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

            // So that a script on the page can register its listeners knowing
            // PyBlade is there to hand events to
            document.dispatchEvent(new CustomEvent('live:init', { detail: this }));
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
        const emitted = [];

        root.querySelectorAll('[pb\\:id]').forEach((el) => {
            const id = el.getAttribute('pb:id');
            if (this.components.has(id)) return;

            // What the component boots from is written on the element itself,
            // and read off it once: morphing may bring newer markup in, but the
            // state of a running component is the one it has been keeping.
            const snapshot = this.read(el, 'pb:snapshot') || {};
            const events = this.read(el, 'pb:events') || [];

            el.removeAttribute('pb:snapshot');
            el.removeAttribute('pb:events');

            this.components.set(id, new Component(id, el, snapshot, this.store));
            events.forEach(event => emitted.push([event, id]));
        });

        // Held back until every component of the page is built, so that one
        // emitting while it mounts reaches the others rather than an empty page
        emitted.forEach(([event, id]) => this.deliver(event, id));
    }

    /** Read what a component wrote on its element as JSON, if it wrote any. */
    read(el, attribute) {
        const value = el.getAttribute(attribute);
        if (!value) return null;

        try {
            return JSON.parse(value);
        } catch {
            return null;
        }
    }

    /**
     * Let go of the components whose element has left the page.
     *
     * A component written in the template of another is gone as soon as the
     * parent stops writing it, and nothing else would tell us so.
     */
    prune() {
        this.components.forEach((component, id) => {
            if (component.element.isConnected) return;

            component.destroy();
            this.components.delete(id);
            this.store.delete(id);
        });
    }

    /**
     * Hand an event to whoever it is meant for.
     *
     * Every component listening for it, unless the one that emitted it said
     * otherwise: .self() keeps it for itself, .to() names the component it is
     * for. It is then raised on the window as 'pb:<name>' for whatever plain
     * JavaScript is listening, the data it carries as the detail of the event.
     */
    deliver(event, originId = null) {
        const { name, data = {}, to = null, self: toSelf = false } = event || {};
        if (!name) return;

        this.components.forEach((component, id) => {
            if (toSelf && id !== originId) return;
            if (to && !component.isNamed(to)) return;

            component.handleEvent(name, data);
        });

        window.dispatchEvent(new CustomEvent(`pb:${name}`, { detail: data }));
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

    /**
     * Listen for an event from anywhere on the page.
     *
     * The callback is handed the event, the data it carries being its detail.
     * What comes back un-registers the listener:
     *
     *     const cleanup = PyBlade.on('post-created', (event) => ...);
     *     cleanup();
     */
    on(eventName, callback) {
        const type = `pb:${eventName}`;

        window.addEventListener(type, callback);

        return () => window.removeEventListener(type, callback);
    }

    /**
     * Emit an event from plain JavaScript, reaching every component that
     * listens for it as one emitted by a component would.
     */
    emit(eventName, data = {}) {
        this.deliver({ name: eventName, data });
    }

    dispatch(eventName, data = {}) {
        this.emit(eventName, data);
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
