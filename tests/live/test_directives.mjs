/**
 * Binding of the pb:* directives.
 *
 * Directives are applied again after every update, on a DOM that morphing left
 * mostly in place, so what these check is that applying twice does not bind
 * twice. Just enough of an element is faked here to exercise that: the browser
 * is not involved, and neither is a test framework beyond the one node ships.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { Directives } from '../../pyblade/live/static/src/directives.js';

class FakeElement {
    constructor(attributes = {}, children = []) {
        this.attributes = Object.entries(attributes).map(([name, value]) => ({ name, value }));
        this.children = children;
        this.listeners = [];
        this.style = {};
        this.classList = { add() {}, remove() {} };
    }

    setAttribute(name, value) {
        const attribute = this.attributes.find(a => a.name === name);
        if (attribute) attribute.value = value;
        else this.attributes.push({ name, value });
    }

    getAttribute(name) {
        return this.attributes.find(a => a.name === name)?.value;
    }

    querySelectorAll() {
        return this.children.flatMap(child => [child, ...child.querySelectorAll()]);
    }

    addEventListener(type, handler, options = {}) {
        const listener = { type, handler };
        this.listeners.push(listener);
        options.signal?.addEventListener('abort', () => {
            this.listeners.splice(this.listeners.indexOf(listener), 1);
        }, { once: true });
    }

    dispatch(type) {
        // A copy: a listener may drop itself while the event is being handled
        [...this.listeners].filter(l => l.type === type).forEach(l => l.handler({
            preventDefault() {},
            stopPropagation() {},
            target: this,
        }));
    }

    countListeners(type) {
        return this.listeners.filter(l => l.type === type).length;
    }
}

function fakeComponent(root) {
    return {
        element: root,
        calls: [],
        formState: { values: {}, dirtyFields: new Set(), touchedFields: new Set() },
        getState: () => ({}),
        callServerMethod(name, args) {
            this.calls.push([name, args]);
            return Promise.resolve();
        },
        refresh() {
            this.calls.push(['$refresh', []]);
        },
        stateChangeCallbacks: new Set(),
        destroyCallbacks: new Set(),
        _register(registry, callback, signal) {
            if (signal?.aborted) return () => {};
            registry.add(callback);
            const forget = () => registry.delete(callback);
            signal?.addEventListener('abort', forget, { once: true });
            return forget;
        },
        onStateChange(callback, signal) {
            return this._register(this.stateChangeCallbacks, callback, signal);
        },
        onDestroy(callback, signal) {
            return this._register(this.destroyCallbacks, callback, signal);
        },
    };
}

test('a directive is bound once, however many times it is applied', () => {
    const button = new FakeElement({ 'pb:click': 'increment' });
    const root = new FakeElement({ 'pb:id': 'c1' }, [button]);
    const component = fakeComponent(root);

    Directives.apply(root, component);
    Directives.apply(root, component);
    Directives.apply(root, component);

    assert.equal(button.countListeners('click'), 1);
});

test('one click calls the server once after an update', () => {
    const button = new FakeElement({ 'pb:click': 'increment' });
    const root = new FakeElement({ 'pb:id': 'c1' }, [button]);
    const component = fakeComponent(root);

    Directives.apply(root, component);
    Directives.apply(root, component);
    button.dispatch('click');

    assert.deepEqual(component.calls, [['increment', []]]);
});

test('a directive whose expression changed is bound again', () => {
    const button = new FakeElement({ 'pb:click': 'increment' });
    const root = new FakeElement({ 'pb:id': 'c1' }, [button]);
    const component = fakeComponent(root);

    Directives.apply(root, component);
    button.setAttribute('pb:click', 'decrement');
    Directives.apply(root, component);
    button.dispatch('click');

    assert.equal(button.countListeners('click'), 1);
    assert.deepEqual(component.calls, [['decrement', []]]);
});

test('an element an update took away gives up its bindings', () => {
    const button = new FakeElement({ 'pb:click': 'increment' });
    const root = new FakeElement({ 'pb:id': 'c1' }, [button]);
    const component = fakeComponent(root);

    Directives.apply(root, component);
    root.children = [];
    Directives.apply(root, component);

    assert.equal(button.countListeners('click'), 0);
    assert.equal(component._bindings.size, 0); // pb:id is not a directive, the root binds nothing
});

test('an element an update brought in is bound', () => {
    const root = new FakeElement({ 'pb:id': 'c1' }, []);
    const component = fakeComponent(root);

    Directives.apply(root, component);

    const button = new FakeElement({ 'pb:click': 'increment' });
    root.children = [button];
    Directives.apply(root, component);
    button.dispatch('click');

    assert.deepEqual(component.calls, [['increment', []]]);
});

test('polling runs one timer, however many times it is applied', () => {
    // Counted rather than timed: what matters is how many timers are left running
    const started = [];
    const realSetInterval = globalThis.setInterval;
    const realClearInterval = globalThis.clearInterval;
    globalThis.setInterval = (...args) => {
        const id = realSetInterval(...args);
        started.push(id);
        return id;
    };
    globalThis.clearInterval = (id) => {
        const index = started.indexOf(id);
        if (index !== -1) started.splice(index, 1);
        return realClearInterval(id);
    };

    try {
        const root = new FakeElement({ 'pb:id': 'c1', 'pb:poll': '5' }, []);
        const component = fakeComponent(root);

        Directives.apply(root, component);
        Directives.apply(root, component);
        Directives.apply(root, component);

        assert.equal(started.length, 1, `${started.length} timers left running`);

        Directives.release(component);

        assert.equal(started.length, 0, 'a timer outlived the component');
    } finally {
        globalThis.setInterval = realSetInterval;
        globalThis.clearInterval = realClearInterval;
    }
});

test('releasing a component stops its polling', async () => {
    const root = new FakeElement({ 'pb:id': 'c1', 'pb:poll': '5' }, []);
    const component = fakeComponent(root);

    Directives.apply(root, component);
    Directives.release(component);
    await new Promise(resolve => setTimeout(resolve, 15));

    assert.deepEqual(component.calls, []);
});

test('an update carrying no html leaves the element alone', async () => {
    const { Component } = await import('../../pyblade/live/static/src/component.js');

    const button = new FakeElement({ 'pb:click': 'increment' });
    const root = new FakeElement({ 'pb:id': 'c1' }, [button]);
    const component = new Component('c1', root, { state: { count: 0 } }, new Map());

    let morphed = false;
    const original = root.querySelectorAll;
    root.querySelectorAll = () => { morphed = true; return original.call(root); };

    component.update({ html: null, snapshot: { state: { count: 5 } } });

    assert.equal(morphed, false, 'the element was re-bound although nothing was rendered');
    assert.equal(component.getState().count, 5, 'the new state was not taken in');
});

test('a callback registered by a directive is forgotten with its binding', () => {
    const input = new FakeElement({ 'pb:show': 'visible' });
    const root = new FakeElement({ 'pb:id': 'c1' }, [input]);
    const component = fakeComponent(root);

    Directives.apply(root, component);
    Directives.apply(root, component);

    assert.equal(component.stateChangeCallbacks.size, 1);

    root.children = [];
    Directives.apply(root, component);

    assert.equal(component.stateChangeCallbacks.size, 0);
});
