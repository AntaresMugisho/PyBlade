/**
 * What happens to a request between asking and answering.
 *
 * Two things a page cannot see for itself: a request that came back wrong, and
 * an answer that came back late. The first has to be said out loud rather than
 * left as a page that has quietly stopped working; the second has to be thrown
 * away, because an old answer carries an old state, and applying it would take
 * the page backwards and then send that backwards state on.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { Component } from '../../pyblade/live/static/src/component.js';

/** The answers a fake server is holding, so a test can settle them in any order. */
let answering = [];

function setUp({ store = new Map() } = {}) {
    answering = [];

    const heard = [];

    global.CustomEvent = class {
        constructor(type, init) {
            this.type = type;
            this.detail = init?.detail;
            this.cancelable = init?.cancelable;
        }
    };

    global.document = {
        querySelector: () => ({ getAttribute: () => 'a-csrf-token' }),
        dispatchEvent: (event) => heard.push(event),
    };

    global.window = { PyBlade: { components: new Map() } };

    // Every request is left hanging until the test answers it
    global.fetch = () => new Promise((resolve, reject) => {
        answering.push({ resolve, reject });
    });

    const root = {
        nodeType: 1,
        attributes: [{ name: 'pb:id', value: 'c1' }],
        getAttribute: () => null,
        querySelectorAll: () => [],
    };

    const component = new Component('c1', root, { state: { title: '' } }, store);

    return { component, heard, store };
}

/** An answer as the server sends one, with nothing to morph. */
function answer(state) {
    return {
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ html: null, snapshot: { state } }),
    };
}

function refusal(status) {
    return {
        ok: false,
        status,
        headers: { get: () => 'application/json' },
        json: async () => ({ error: 'Something was wrong.' }),
    };
}

const settle = () => new Promise(resolve => setTimeout(resolve, 0));

// A request that came back wrong
// ---------------------------------------------------------------------------

test('an answer that is not an answer is said out loud', async () => {
    const { component, heard } = setUp();

    const asking = component.sendRequest({ action: 'save', params: [] });
    answering[0].resolve(refusal(500));
    await asking;

    assert.deepEqual(heard.map(event => event.type), ['live:error']);
    assert.equal(heard[0].detail.status, 500);
});

test('what was being asked is said with it', async () => {
    const { component, heard } = setUp();

    const asking = component.sendRequest({ action: 'save', params: [] });
    answering[0].resolve(refusal(500));
    await asking;

    assert.equal(heard[0].detail.action, 'save');
    assert.equal(heard[0].detail.id, 'c1');
});

test('a session that has gone stale is told apart from a server that is unwell', async () => {
    const { component, heard } = setUp();

    const asking = component.sendRequest({ action: 'save', params: [] });
    answering[0].resolve(refusal(403));
    await asking;

    assert.equal(heard[0].detail.status, 403);
    assert.equal(heard[0].detail.expired, true);
});

test('a request that never arrives is said out loud too', async () => {
    const { component, heard } = setUp();

    const asking = component.sendRequest({ action: 'save', params: [] });
    answering[0].reject(new TypeError('Failed to fetch'));
    await asking;

    assert.deepEqual(heard.map(event => event.type), ['live:error']);
    assert.equal(heard[0].detail.status, 0);
});

test('nothing of a refused answer is applied', async () => {
    const { component, store } = setUp();

    const asking = component.sendRequest({ action: 'save', params: [] });
    answering[0].resolve(refusal(500));
    await asking;

    assert.deepEqual(store.get('c1'), { state: { title: '' } });
});

test('the page is not left waiting for ever', async () => {
    const { component } = setUp();
    const ended = [];
    component.onLoadingEnd(() => ended.push(true));

    const asking = component.sendRequest({ action: 'save', params: [] });
    answering[0].resolve(refusal(500));
    await asking;

    assert.equal(ended.length, 1);
});

test('an answer that came back whole says nothing about errors', async () => {
    const { component, heard } = setUp();

    const asking = component.sendRequest({ action: 'save', params: [] });
    answering[0].resolve(answer({ title: 'Saved' }));
    await asking;

    assert.deepEqual(heard, []);
});

// An answer that came back late
// ---------------------------------------------------------------------------

test('the newer answer is the one the page keeps', async () => {
    const { component, store } = setUp();

    const first = component.sendRequest({ action: '$set', params: ['title', 'a'] });
    const second = component.sendRequest({ action: '$set', params: ['title', 'ab'] });

    // The second request is answered first, as a shorter query might be
    answering[1].resolve(answer({ title: 'ab' }));
    await settle();
    answering[0].resolve(answer({ title: 'a' }));
    await Promise.all([first, second]);

    assert.deepEqual(store.get('c1').state, { title: 'ab' });
});

test('and the state the next request is built on is the newer one', async () => {
    const { component } = setUp();

    const first = component.sendRequest({ action: '$set', params: ['title', 'a'] });
    const second = component.sendRequest({ action: '$set', params: ['title', 'ab'] });

    answering[1].resolve(answer({ title: 'ab' }));
    await settle();
    answering[0].resolve(answer({ title: 'a' }));
    await Promise.all([first, second]);

    assert.equal(component.formState.values.title, 'ab');
});

test('answers that come back in the order they were asked for are all applied', async () => {
    const { component, store } = setUp();

    const first = component.sendRequest({ action: '$set', params: ['title', 'a'] });
    answering[0].resolve(answer({ title: 'a' }));
    await first;

    const second = component.sendRequest({ action: '$set', params: ['title', 'ab'] });
    answering[1].resolve(answer({ title: 'ab' }));
    await second;

    assert.deepEqual(store.get('c1').state, { title: 'ab' });
});

test('a late answer is dropped rather than made the newest', async () => {
    const { component, store } = setUp();

    const first = component.sendRequest({ action: '$set', params: ['title', 'a'] });
    const second = component.sendRequest({ action: '$set', params: ['title', 'ab'] });

    answering[1].resolve(answer({ title: 'ab' }));
    await settle();
    answering[0].resolve(answer({ title: 'a' }));
    await Promise.all([first, second]);

    const third = component.sendRequest({ action: '$set', params: ['title', 'abc'] });
    answering[2].resolve(answer({ title: 'abc' }));
    await third;

    assert.deepEqual(store.get('c1').state, { title: 'abc' });
});
