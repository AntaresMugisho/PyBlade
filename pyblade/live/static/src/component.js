import { Directives } from './directives.js';
import { Idiomorph } from "../vendor/idiomorph.esm.js"

export class Component {
    constructor(id, element, snapshot, store) {
        this.id = id;
        this.element = element;
        this.store = store;

        // Store snapshot directly in JS Memory
        this.store.set(this.id, snapshot);

        // Callback registries for directives. Sets, because a directive gives up
        // its callbacks when its binding is dropped, and an update drops as many
        // bindings as it renews.
        this.loadingStartCallbacks = new Set();
        this.loadingEndCallbacks = new Set();
        this.dirtyCallbacks = new Set();
        this.cleanCallbacks = new Set();
        this.stateChangeCallbacks = new Set();
        this.streamUpdateCallbacks = new Set();
        this.destroyCallbacks = new Set();

        // Directive bindings, kept per element so that an update only binds
        // what morphing has actually added or changed
        this._bindings = new Map();

        // Form state registry (react-hook-form inspired)
        this.formState = {
            values: { ...snapshot.state },
            dirtyFields: new Set(),
            touchedFields: new Set(),
        };
        this.pendingUpdates = null;
        this.pendingUpdateTimer = null;

        // Bind directives to DOM
        Directives.apply(this.element, this);
    }

    async callServerMethod(methodName, params = []) {
        await this.sendRequest({ action: methodName, params });
    }

    async setProperties(updatedProperties) {
        const [propName, value] = updatedProperties;
        
        // Update local form state immediately (react-hook-form pattern)
        this.formState.values[propName] = value;
        this.formState.dirtyFields.add(propName);
        this.formState.touchedFields.add(propName);
        
        // Batch updates - don't send immediately
        this.pendingUpdates = this.pendingUpdates || {};
        this.pendingUpdates[propName] = value;
        
        // Clear existing timer and set new one for batched update
        if (this.pendingUpdateTimer) {
            clearTimeout(this.pendingUpdateTimer);
        }
        
        this.pendingUpdateTimer = setTimeout(async () => {
            if (this.pendingUpdates) {
                const updates = Object.entries(this.pendingUpdates).flat();
                this.pendingUpdates = null;
                await this.sendRequest({ action: "$set", params: updates });
            }
        }, 300); // Default batch delay
    }

    async sendRequest(payload) {
        const csrfToken = document.querySelector('script[data-csrf]')?.getAttribute('data-csrf');

        // Trigger loading start callbacks
        this.loadingStartCallbacks.forEach(cb => cb());

        try {
            const response = await fetch('/pyblade/live/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    id: this.id,
                    snapshot: this.store.get(this.id),
                    // What the page already holds, so that a component written
                    // inside this one is left where it is rather than started over
                    known: [...window.PyBlade.components.keys()],
                    ...payload
                })
            });

            const data = await response.json();
            if (data) this.update(data);
        } finally {
            // Trigger loading end callbacks
            this.loadingEndCallbacks.forEach(cb => cb());
        }
    }

    update({ html, snapshot, events = [], redirect = null }) {
        this.store.set(this.id, snapshot);

        // A renderless action answers with its new state and no HTML at all,
        // and the page is left as it is
        if (html) {
            Idiomorph.morph(this.element, this.withNestedComponents(html), {
                callbacks: {
                    // A component written inside this one answers for itself.
                    // Its element is left exactly as it is, with the state, the
                    // listeners and the timers it has been keeping.
                    beforeNodeMorphed: (node) => !this.isNested(node),
                },
            });

            Directives.apply(this.element, this);

            // Whatever the new markup brought with it, and whatever it took away
            window.PyBlade.scan(this.element);
            window.PyBlade.prune();
        }

        // Handed to the core rather than raised here: an event is for the other
        // components on the page as much as for whatever JavaScript listens.
        events.forEach(event => window.PyBlade.deliver(event, this.id));

        // Trigger state change callbacks
        this.stateChangeCallbacks.forEach(cb => cb());

        if (redirect) {
            redirect.navigate ? this.navigate(redirect.href) : (window.location.href = redirect.href);
        }
    }

    // Callback registration methods for directives.
    //
    // A directive passes the signal of its binding along: the callback is then
    // forgotten as soon as that binding is renewed or dropped, instead of
    // piling up on every update and running against elements long gone.
    _register(registry, callback, signal) {
        if (signal?.aborted) return () => {};

        registry.add(callback);

        const forget = () => registry.delete(callback);
        signal?.addEventListener('abort', forget, { once: true });

        return forget;
    }

    onLoadingStart(callback, signal) {
        return this._register(this.loadingStartCallbacks, callback, signal);
    }

    onLoadingEnd(callback, signal) {
        return this._register(this.loadingEndCallbacks, callback, signal);
    }

    onDirty(callback, signal) {
        return this._register(this.dirtyCallbacks, callback, signal);
    }

    onClean(callback, signal) {
        return this._register(this.cleanCallbacks, callback, signal);
    }

    onStateChange(callback, signal) {
        return this._register(this.stateChangeCallbacks, callback, signal);
    }

    onStreamUpdate(callback, signal) {
        return this._register(this.streamUpdateCallbacks, callback, signal);
    }

    onDestroy(callback, signal) {
        return this._register(this.destroyCallbacks, callback, signal);
    }

    /**
     * Whether a node belongs to a component written inside this one.
     *
     * The root of this component carries an id too, and that one is ours.
     */
    isNested(node) {
        return node !== this.element && node.nodeType === 1 && node.hasAttribute('pb:id');
    }

    /**
     * Put back the markup of the components this one only said the place of.
     *
     * A component already on the page is not rendered again: its parent answers
     * with an empty element carrying its id. Morphing pairs the old markup with
     * the new by what the two look like, so the placeholder is filled with what
     * the page holds before it is handed over -- an empty element of another
     * name would be taken for a different one and the component swept away with it.
     */
    withNestedComponents(html) {
        if (!html.includes('pb:placeholder')) return html;

        const incoming = document.createElement('div');
        incoming.innerHTML = html;

        incoming.querySelectorAll('[pb\\:placeholder]').forEach((placeholder) => {
            const id = placeholder.getAttribute('pb:id');
            const live = document.querySelector(`[pb\\:id="${CSS.escape(id)}"]`);

            if (live) placeholder.replaceWith(live.cloneNode(true));
        });

        return incoming.innerHTML;
    }

    /**
     * Emit an event from this component, as pb:click="emit('saved')" does.
     */
    emit(event) {
        return window.PyBlade.deliver(event, this.id);
    }

    /**
     * Answer an event this component listens for.
     *
     * What it listens for is read from the snapshot on every event rather than
     * subscribed to once: an event name may be built from what the component
     * holds, and what it holds changes with every answer it gets.
     */
    handleEvent(name, data = {}) {
        const listeners = this.store.get(this.id)?.listeners || {};

        if (!Object.prototype.hasOwnProperty.call(listeners, name)) return;

        return this.sendRequest({ action: '$event', params: [name, data] });
    }

    /**
     * Whether this component is the one named, as emit().to('Dashboard') names it.
     *
     * Either the class on its own or the whole path it is reached by, so that
     * two components of the same name in different modules can be told apart.
     */
    isNamed(name) {
        const path = this.store.get(this.id)?.class || '';

        return path === name || path.split('.').pop() === name;
    }

    // Utility methods for directives
    getState() {
        return this.store.get(this.id)?.state || {};
    }

    navigate(url) {
        return window.PyBlade.navigate(url);
    }

    async refresh() {
        await this.sendRequest({ action: '$refresh' });
    }

    destroy() {
        this.destroyCallbacks.forEach(cb => cb());
        Directives.release(this);
    }
}