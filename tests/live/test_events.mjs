/**
 * Events travelling between components on the page.
 *
 * What the client does with an event is decide who it is for: every component
 * that listens for it, or the one it names, or only the one that emitted it.
 * Whoever it reaches asks the server to handle it. The browser is not involved
 * here beyond the little of it these fakes stand in for.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { Directives } from '../../pyblade/live/static/src/directives.js';

// Reading an expression that emits rather than calls
// ---------------------------------------------------------------------------

test('an ordinary action is not an event', () => {
    assert.equal(Directives.parseEmit('increment'), null);
    assert.equal(Directives.parseEmit('save(1, 2)'), null);
});

test('emit names the event', () => {
    assert.deepEqual(Directives.parseEmit("emit('post-created')"), {
        name: 'post-created',
        data: {},
    });
});

test('dispatch is read the same way', () => {
    assert.deepEqual(Directives.parseEmit("dispatch('post-created')"), {
        name: 'post-created',
        data: {},
    });
});

test('what is written as key=value is the data of the event', () => {
    assert.deepEqual(Directives.parseEmit("emit('show-post-modal', id=3)"), {
        name: 'show-post-modal',
        data: { id: 3 },
    });
});

test('several values are carried together', () => {
    const event = Directives.parseEmit("emit('saved', id=3, title='Hello')");

    assert.deepEqual(event.data, { id: 3, title: 'Hello' });
});

test('to names the component the event is for', () => {
    const event = Directives.parseEmit("emit('show-post-modal', id=3).to('PostList')");

    assert.deepEqual(event, { name: 'show-post-modal', data: { id: 3 }, to: 'PostList' });
});

test('self keeps the event for the component that emitted it', () => {
    const event = Directives.parseEmit("emit('saved').self()");

    assert.equal(event.self, true);
});

test('a parenthesis inside a value does not end the call', () => {
    const event = Directives.parseEmit("emit('saved', title='a (b)')");

    assert.deepEqual(event.data, { title: 'a (b)' });
});

test('an unfinished call is not an event', () => {
    assert.equal(Directives.parseEmit("emit('saved'"), null);
});

test('a method whose name merely starts with emit is an action', () => {
    assert.equal(Directives.parseEmit('emitter()'), null);
});

// Handing an event to whoever it is for
// ---------------------------------------------------------------------------

class FakeComponent {
    constructor(id, { listeners = {}, className = 'app.Dashboard' } = {}) {
        this.id = id;
        this.className = className;
        this.listeners = listeners;
        this.handled = [];
    }

    handleEvent(name, data) {
        if (!Object.prototype.hasOwnProperty.call(this.listeners, name)) return;
        this.handled.push({ name, data });
    }

    isNamed(name) {
        return this.className === name || this.className.split('.').pop() === name;
    }
}

/** The part of the core that routes an event, with the rest of it left out. */
function core(components) {
    const raised = [];

    return {
        raised,
        components: new Map(components.map(component => [component.id, component])),

        deliver(event, originId = null) {
            const { name, data = {}, to = null, self: toSelf = false } = event || {};
            if (!name) return;

            this.components.forEach((component, id) => {
                if (toSelf && id !== originId) return;
                if (to && !component.isNamed(to)) return;

                component.handleEvent(name, data);
            });

            raised.push({ name, detail: data });
        },
    };
}

test('an event reaches every component that listens for it', () => {
    const a = new FakeComponent('a', { listeners: { saved: 'refresh' } });
    const b = new FakeComponent('b', { listeners: { saved: 'reload' } });
    const bus = core([a, b]);

    bus.deliver({ name: 'saved', data: { id: 1 } }, 'a');

    assert.deepEqual(a.handled, [{ name: 'saved', data: { id: 1 } }]);
    assert.deepEqual(b.handled, [{ name: 'saved', data: { id: 1 } }]);
});

test('a component that listens for nothing is left alone', () => {
    const quiet = new FakeComponent('a');
    const bus = core([quiet]);

    bus.deliver({ name: 'saved' }, 'b');

    assert.deepEqual(quiet.handled, []);
});

test('self keeps the event for the component that emitted it', () => {
    const origin = new FakeComponent('a', { listeners: { saved: 'refresh' } });
    const other = new FakeComponent('b', { listeners: { saved: 'refresh' } });
    const bus = core([origin, other]);

    bus.deliver({ name: 'saved', self: true }, 'a');

    assert.equal(origin.handled.length, 1);
    assert.deepEqual(other.handled, []);
});

test('to reaches the component it names and no other', () => {
    const dashboard = new FakeComponent('a', { listeners: { saved: 'r' }, className: 'app.Dashboard' });
    const sidebar = new FakeComponent('b', { listeners: { saved: 'r' }, className: 'app.Sidebar' });
    const bus = core([dashboard, sidebar]);

    bus.deliver({ name: 'saved', to: 'Dashboard' }, 'c');

    assert.equal(dashboard.handled.length, 1);
    assert.deepEqual(sidebar.handled, []);
});

test('to accepts the whole path a component is reached by', () => {
    const dashboard = new FakeComponent('a', { listeners: { saved: 'r' }, className: 'app.Dashboard' });
    const bus = core([dashboard]);

    bus.deliver({ name: 'saved', to: 'app.Dashboard' }, 'c');

    assert.equal(dashboard.handled.length, 1);
});

test('an event is raised for plain JavaScript too', () => {
    const bus = core([]);

    bus.deliver({ name: 'saved', data: { id: 2 } });

    assert.deepEqual(bus.raised, [{ name: 'saved', detail: { id: 2 } }]);
});

test('an event with no name goes nowhere', () => {
    const listener = new FakeComponent('a', { listeners: { saved: 'r' } });
    const bus = core([listener]);

    bus.deliver({});

    assert.deepEqual(listener.handled, []);
    assert.deepEqual(bus.raised, []);
});

// The parsing an event shares with any other action
// ---------------------------------------------------------------------------

test('an action carries several keyword arguments too', () => {
    const { methodName, args } = Directives.parseExpression("save(id=3, title='Hello')");

    assert.equal(methodName, 'save');
    assert.deepEqual(args, [{ id: 3 }, { title: 'Hello' }]);
});

test('positional and keyword arguments sit side by side', () => {
    const { args } = Directives.parseExpression("save(1, title='Hello')");

    assert.deepEqual(args, [1, { title: 'Hello' }]);
});
