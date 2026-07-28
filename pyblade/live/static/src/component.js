import { Directives } from './directives.js';
import { Idiomorph } from "../vendor/idiomorph.esm.js"

export class Component {
    constructor(id, element, snapshot, store) {
        this.id = id;
        this.element = element;
        this.store = store;

        // Store snapshot directly in JS Memory
        this.store.set(this.id, snapshot);

        // Callback registries for directives
        this.loadingStartCallbacks = [];
        this.loadingEndCallbacks = [];
        this.dirtyCallbacks = [];
        this.cleanCallbacks = [];
        this.stateChangeCallbacks = [];
        this.streamUpdateCallbacks = [];
        this.destroyCallbacks = [];

        // Bind directives to DOM
        Directives.apply(this.element, this);
    }

    async callServerMethod(methodName, params = []) {
        await this.sendRequest({ action: methodName, params });
    }

    async setProperties(updatedProperties) {
        await this.sendRequest({ action: "$set", params: updatedProperties });
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

    update({ html, snapshot, events = [] }) {
        this.store.set(this.id, snapshot);

        Idiomorph.morph(this.element, html);

        Directives.apply(this.element, this);

        events.forEach(evt => window.dispatchEvent(new CustomEvent(`pb:${evt.name}`, { detail: evt.data })));

        // Trigger state change callbacks
        this.stateChangeCallbacks.forEach(cb => cb());
    }

    // Callback registration methods for directives
    onLoadingStart(callback) {
        this.loadingStartCallbacks.push(callback);
    }

    onLoadingEnd(callback) {
        this.loadingEndCallbacks.push(callback);
    }

    onDirty(callback) {
        this.dirtyCallbacks.push(callback);
    }

    onClean(callback) {
        this.cleanCallbacks.push(callback);
    }

    onStateChange(callback) {
        this.stateChangeCallbacks.push(callback);
    }

    onStreamUpdate(callback) {
        this.streamUpdateCallbacks.push(callback);
    }

    onDestroy(callback) {
        this.destroyCallbacks.push(callback);
    }

    // Utility methods for directives
    getState() {
        return this.store.get(this.id)?.state || {};
    }

    navigate(url) {
        // SPA-like navigation
        window.history.pushState({}, '', url);
        window.dispatchEvent(new PopStateEvent('popstate'));
    }

    async refresh() {
        await this.sendRequest({ action: '$refresh' });
    }

    destroy() {
        this.destroyCallbacks.forEach(cb => cb());
    }
}