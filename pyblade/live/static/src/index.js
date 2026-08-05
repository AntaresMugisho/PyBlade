import { Component } from './component.js';
import { Directives } from './directives.js';
import { Navigation } from './navigate.js';
import { Progress } from './progress.js';

class PyBladeCore {
    constructor() {
        // Central JS Memory Store (Map)
        this.store = new Map();
        this.components = new Map();
    }

    start() {
        const boot = () => {
            this.scan();
            Navigation.start(this);
        };

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', boot, { once: true });
        } else {
            boot();
        }
    }

    /**
     * Build a component for every element that carries one and has none yet.
     *
     * Run on the first load and again after each navigation, so a component
     * that was already there is left running rather than started over.
     */
    scan(root = document) {
        root.querySelectorAll('[pb\\:id]').forEach((el) => {
            const id = el.getAttribute('pb:id');
            if (this.components.has(id)) return;

            const script = document.querySelector(`script[pb\\:snapshot="${CSS.escape(id)}"]`);
            const snapshot = script ? JSON.parse(script.textContent) : {};
            script?.remove();

            this.components.set(id, new Component(id, el, snapshot, this.store));
        });
    }

    /**
     * Let go of the components inside an element that is about to be replaced.
     *
     * Their timers and listeners go with them; leaving them behind would keep a
     * poll running against a component the reader has navigated away from.
     */
    release(root = document) {
        root.querySelectorAll('[pb\\:id]').forEach((el) => {
            const id = el.getAttribute('pb:id');
            const component = this.components.get(id);
            if (!component) return;

            component.destroy();
            this.components.delete(id);
            this.store.delete(id);
        });
    }

    // Move to another page without loading one
    navigate(href) {
        return Navigation.visit(href);
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
window.PyBlade.Progress = Progress;
window.PyBlade.start();
