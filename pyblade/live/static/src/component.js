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
            Idiomorph.morph(this.element, html);
            Directives.apply(this.element, this);
        }

        events.forEach(evt => window.dispatchEvent(new CustomEvent(`pb:${evt.name}`, { detail: evt.data })));

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