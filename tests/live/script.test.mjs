/**
 * $pb, a component as JavaScript sees it, and which @script blocks are run.
 *
 * Running a block is DOM work and is checked in a browser; what is checked here
 * is what $pb reads, sets and asks for, and the choosing of the blocks.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { pbFor, scriptsToRun } from '../../pyblade/live/static/src/script.js';

/** Enough of a component for $pb to be read off it, recording what it is asked. */
function component(state = {}) {
    const asked = [];
    const stateCallbacks = new Set();

    const fake = {
        id: 'c1',
        element: { tagName: 'DIV' },
        formState: { values: { ...state }, touchedFields: new Set() },
        snapshot: { state },
        asked,
        getState: () => fake.snapshot.state,
        setLocal(name, value) { this.formState.values[name] = value; asked.push(['local', name, value]); },
        sendRequest: (payload) => { asked.push(['request', payload]); return Promise.resolve(); },
        callServerMethod: (name, params) => { asked.push(['call', name, params]); return Promise.resolve(); },
        refresh: () => { asked.push(['refresh']); return Promise.resolve(); },
        emit: (event) => asked.push(['emit', event]),
        onStateChange: (callback) => { stateCallbacks.add(callback); return () => stateCallbacks.delete(callback); },
        onDestroy: () => () => {},
        isNested: (node) => node.nested === true,
        answer(newState) {
            this.snapshot.state = newState;
            this.formState.values = { ...newState };
            stateCallbacks.forEach(cb => cb());
        },
    };

    return fake;
}

// Properties
// ---------------------------------------------------------------------------

test('a property reads what the component holds', () => {
    assert.equal(pbFor(component({ count: 3 })).count, 3);
});

test('setting one keeps it here, to go with the next request', () => {
    const c = component({ count: 3 });
    pbFor(c).count = 5;

    assert.equal(pbFor(c).count, 5);
    assert.deepEqual(c.asked, [['local', 'count', 5]]);
});

test('$set sends it now', () => {
    const c = component({ count: 3 });
    pbFor(c).$set('count', 5);

    assert.deepEqual(c.asked.at(-1), ['request', { action: '$set', params: ['count', 5] }]);
});

test('$get reads it', () => {
    assert.equal(pbFor(component({ name: 'Ada' })).$get('name'), 'Ada');
});

// Actions
// ---------------------------------------------------------------------------

test('any other name is an action, called with what it is given', () => {
    const c = component({ count: 3 });
    pbFor(c).save(1, 'two');

    assert.deepEqual(c.asked, [['call', 'save', [1, 'two']]]);
});

test('$call is the same thing', () => {
    const c = component();
    pbFor(c).$call('save', 1);

    assert.deepEqual(c.asked, [['call', 'save', [1]]]);
});

test('$refresh renders the component again', () => {
    const c = component();
    pbFor(c).$refresh();

    assert.deepEqual(c.asked, [['refresh']]);
});

test('$emit and $dispatch emit an event from the component', () => {
    const c = component();
    pbFor(c).$emit('saved', { id: 1 });
    pbFor(c).$dispatch('saved');

    assert.deepEqual(c.asked, [['emit', { name: 'saved', data: { id: 1 } }], ['emit', { name: 'saved', data: {} }]]);
});

// What it is
// ---------------------------------------------------------------------------

test('$el and $id are its element and its id', () => {
    const c = component();

    assert.equal(pbFor(c).$el, c.element);
    assert.equal(pbFor(c).$id, 'c1');
});

test('$pb is not something to be awaited', () => {
    assert.equal(pbFor(component()).then, undefined);
});

// Watching
// ---------------------------------------------------------------------------

test('$watch is told the new value and the old one when a property changes', () => {
    const c = component({ count: 1 });
    const seen = [];
    pbFor(c).$watch('count', (now, before) => seen.push([now, before]));

    c.answer({ count: 2 });

    assert.deepEqual(seen, [[2, 1]]);
});

test('and not when an answer leaves it as it was', () => {
    const c = component({ count: 1, other: 1 });
    const seen = [];
    pbFor(c).$watch('count', (now) => seen.push(now));

    c.answer({ count: 1, other: 2 });

    assert.deepEqual(seen, []);
});

// Which @script blocks are run
// ---------------------------------------------------------------------------

const block = (key, nested = false) => ({ nested, getAttribute: () => key });

test('each block is run once', () => {
    const c = component();
    const blocks = [block('a'), block('b')];

    assert.equal(scriptsToRun(c, blocks).length, 2);
    assert.equal(scriptsToRun(c, blocks).length, 0);
});

test('a block that appears later is run when it does', () => {
    const c = component();
    scriptsToRun(c, [block('a')]);

    assert.deepEqual(scriptsToRun(c, [block('a'), block('b')]).map(b => b.getAttribute()), ['b']);
});

test('a block of a component written inside this one is that one\'s', () => {
    assert.deepEqual(scriptsToRun(component(), [block('a', true)]), []);
});
