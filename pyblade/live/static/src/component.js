import { Directives } from './directives.js';
import { Idiomorph } from "../vendor/idiomorph.esm.js"
import { applyKeys, morphCallbacks } from './morph.js';
import { readLines } from './streaming.js';

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
        this.dirtyChangeCallbacks = new Set();
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

        // The dirty properties as they were last told, so that they are only
        // told again when they have actually changed
        this._dirtySignature = '';

        // Bind directives to DOM
        Directives.apply(this.element, this);
    }

    async callServerMethod(methodName, params = [], options = undefined) {
        await this.sendRequest({ action: methodName, params, ...(options || {}) });
    }

    async setProperties(updatedProperties, delay = 300) {
        const [propName, value] = updatedProperties;
        
        // Update local form state immediately (react-hook-form pattern)
        this.formState.values[propName] = value;
        this.formState.touchedFields.add(propName);
        this.refreshDirty();
        
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
        }, delay);
    }

    async sendRequest(payload) {
        const csrfToken = document.querySelector('script[data-csrf]')?.getAttribute('data-csrf');

        // What is being asked of the server, so that an element watching one
        // action or one property can tell whether this is the one
        this.loadingStartCallbacks.forEach(cb => cb(payload));

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
                    // What was typed into the form and not sent yet, so that
                    // the action runs against the form as the reader left it
                    updates: this.pendingUpdatesToSend(payload),
                    ...payload
                })
            });

            // An action that answers as it goes says so with its content type:
            // its answer is a line of JSON at a time, the last of which is the
            // answer proper and the rest what it streamed on the way there.
            if (response.headers.get('Content-Type')?.includes('x-ndjson')) {
                await readLines(response.body, (line) => {
                    if (line.stream) this.streamTo(line.stream);
                    else this.update(line);
                });
                return;
            }

            const data = await response.json();
            if (data) this.update(data);
        } finally {
            this.loadingEndCallbacks.forEach(cb => cb(payload));
        }
    }

    update({ html, snapshot, events = [], streams = [], redirect = null }) {
        this.store.set(this.id, snapshot);

        // What has not been typed into is the server's to say, so that the
        // page keeps up with a property an action changed
        Object.entries(snapshot?.state || {}).forEach(([name, value]) => {
            if (!this.formState.touchedFields.has(name)) this.formState.values[name] = value;
        });

        // A renderless action answers with its new state and no HTML at all,
        // and the page is left as it is
        if (html) {
            // A component written inside this one answers for itself: its
            // element is left as it is, with the state, the listeners and the
            // timers it has been keeping. pb:ignore, pb:replace and pb:key are
            // read by the same callbacks.
            applyKeys(this.element);

            Idiomorph.morph(this.element, applyKeys(this.incoming(html)), {
                callbacks: morphCallbacks({ isOwn: (node) => !this.isNested(node) }),
            });

            Directives.apply(this.element, this);

            // Whatever the new markup brought with it, and whatever it took away
            window.PyBlade.scan(this.element);
            window.PyBlade.prune();
        }

        // Handed to the core rather than raised here: an event is for the other
        // components on the page as much as for whatever JavaScript listens.
        events.forEach(event => window.PyBlade.deliver(event, this.id));

        // What the action streamed while there was nowhere to stream it to:
        // written now, all at once, rather than as it was written
        streams.forEach(chunk => this.streamTo(chunk));

        // What the server has answered for is no longer dirty
        this.refreshDirty();

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

    /**
     * Watch which properties have been changed here and not yet sent.
     *
     * The callback is handed the names of them, every time that set changes:
     * an element watching one of its own decides for itself what to do about it.
     */
    onDirtyChange(callback, signal) {
        return this._register(this.dirtyChangeCallbacks, callback, signal);
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
     * The answer of the server, as an element, ready to be morphed in.
     *
     * Put back into it are the components this one only said the place of.
     *
     * A component already on the page is not rendered again: its parent answers
     * with an empty element carrying its id. Morphing pairs the old markup with
     * the new by what the two look like, so the placeholder is filled with what
     * the page holds before it is handed over -- an empty element of another
     * name would be taken for a different one and the component swept away with it.
     */
    incoming(html) {
        const incoming = document.createElement('div');
        incoming.innerHTML = html;

        incoming.querySelectorAll('[pb\\:placeholder]').forEach((placeholder) => {
            const id = placeholder.getAttribute('pb:id');
            const live = document.querySelector(`[pb\\:id="${CSS.escape(id)}"]`);

            if (live) placeholder.replaceWith(live.cloneNode(true));
        });

        // The root of the answer is the component itself, which is what the
        // element being morphed is to be brought up to
        return incoming.firstElementChild || incoming;
    }

    /**
     * What the reader has put into a field, kept on the page.
     *
     * Whether it is sent now or with whatever the component asks next, this is
     * where it is held meanwhile, and what makes the property dirty.
     */
    setLocal(name, value) {
        this.formState.values[name] = value;
        this.formState.touchedFields.add(name);
        this.refreshDirty();
    }

    /**
     * What the server says a property holds, for a field that has not been
     * typed into. A field the reader is working in is left with what they typed.
     */
    seedLocal(name, value) {
        if (this.formState.touchedFields.has(name)) return;

        this.formState.values[name] = value;
    }

    /**
     * What the page holds and the server has not seen, to travel with a request.
     *
     * A field written pb:model says nothing on its own: this is how what was
     * typed into it reaches the server, with whatever the component asks next.
     */
    pendingUpdatesToSend(payload = {}) {
        const updates = {};

        this.dirtyFields().forEach((name) => { updates[name] = this.formState.values[name]; });

        // A property this very request is setting is not also one waiting to be
        // sent: setting it twice would run the hooks watching it twice over
        if (payload.action === '$set') {
            for (let i = 0; i < (payload.params || []).length; i += 2) delete updates[payload.params[i]];
        }

        return updates;
    }

    /**
     * The properties changed here and not yet answered for by the server.
     *
     * A property is dirty while what the page holds differs from the state the
     * last answer came back with: what the reader has typed and the server has
     * not seen yet. Worked out rather than remembered, so that an answer
     * carrying the very value that was typed leaves nothing dirty behind.
     */
    dirtyFields() {
        const state = this.getState();
        const dirty = new Set();

        // Only what has actually been typed into: a property the server changed
        // on its own was never the reader's to save, and saying it is unsaved
        // would leave the word on the page for as long as the page is open.
        this.formState.touchedFields.forEach((name) => {
            if (JSON.stringify(this.formState.values[name]) !== JSON.stringify(state[name])) dirty.add(name);
        });

        return dirty;
    }

    /** Tell whoever watches which properties are dirty, if that has changed. */
    refreshDirty() {
        const dirty = this.dirtyFields();
        const signature = [...dirty].sort().join(',');

        if (signature === this._dirtySignature) return;

        this._dirtySignature = signature;
        this.formState.dirtyFields = dirty;
        this.dirtyChangeCallbacks.forEach(cb => cb(dirty));
    }

    /**
     * Hand a piece of streamed content to the element it was sent to.
     */
    streamTo(chunk) {
        this.streamUpdateCallbacks.forEach(cb => cb(chunk));
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