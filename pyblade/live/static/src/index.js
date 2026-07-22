import { Component } from './component.js';
import { Directives } from './directives.js';

class PyBladeCore {
    constructor() {
        // Central JS Memory Store (Map)
        this.store = new Map();
        this.components = new Map();
    }

    start() {
        document.addEventListener('DOMContentLoaded', () => {
            // Scan page for components initialized
            console.log("Hello from PyBlade Live")

            document.querySelectorAll('[pb\\:id]').forEach(el => {
                const id = el.getAttribute('pb:id');
                const initialState = window.__PB_SNAPSHOTS__?.[id] || {};

                const component = new Component(id, el, initialState, this.store);
                this.components.set(id, component);
            });

            // Cleanup initial HTML script tag memory
            delete window.__PB_SNAPSHOTS__;
        });
    }

    // Server-to-Client / Client-to-Client Event Bus
    on(eventName, callback) {
        window.addEventListener(`pb:${eventName}`, (e) => callback(e.detail));
    }

    emit(eventName, detail = {}) {
        window.dispatchEvent(new CustomEvent(`pb:${eventName}`, { detail }));
    }

    // Register custom directives via JS API
    directive(name, callback) {
        Directives.add(name, callback);
    }
}

// Global initialization
window.PyBlade = new PyBladeCore();
window.PyBlade.start();