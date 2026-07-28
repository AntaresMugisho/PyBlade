import { Directives } from './directives.js';
import { Idiomorph } from "../vendor/idiomorph.esm.js"

export class Component {
    constructor(id, element, snapshot, store) {
        this.id = id;
        this.element = element;
        this.store = store;

        // Store snapshot directly in JS Memory
        this.store.set(this.id, snapshot);

        // Bind directives to DOM
        Directives.apply(this.element, this);
    }

    async callServerMethod(methodName, params = []) {
        await this.sendRequest({ action: methodName, params });
    }

    async setProperties(updatedProperties) {
        await this.sendRequest({ properties: updatedProperties });
    }

    async sendRequest(payload) {
        const csrfToken = document.querySelector('script[data-csrf]')?.getAttribute('data-csrf');

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
    }

    update({ html, snapshot, events = [] }) {
        this.store.set(this.id, snapshot);

        Idiomorph.morph(this.element, html);

        Directives.apply(this.element, this);

        events.forEach(evt => window.dispatchEvent(new CustomEvent(`pb:${evt.name}`, { detail: evt.data })));
    }
}