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

/** What each request carried, in the order they went out. */
let asked = [];

function setUp({ store = new Map() } = {}) {
    answering = [];
    asked = [];

    const heard = [];

    global.CustomEvent = class {
        constructor(type, init) {
            this.type = type;
            this.detail = init?.detail;
            this.cancelable = init?.cancelable;
        }
    };

    // Enough of a document for the csrf token, the events, and the dialogue the
    // error page is shown in
    const element = (tag) => ({
        tagName: tag.toUpperCase(),
        children: [],
        attributes: {},
        open: false,
        className: '',
        setAttribute(name, value) { this.attributes[name] = value; },
        getAttribute(name) { return this.attributes[name] ?? null; },
        append(...kids) { this.children.push(...kids); },
        appendChild(kid) { this.children.push(kid); return kid; },
        addEventListener() {},
        querySelector(selector) {
            return this.children.find(kid => kid.tagName === selector.toUpperCase()) || null;
        },
        showModal() { this.open = true; },
        close() { this.open = false; },
        get isConnected() { return global.document?.body?.children.includes(this) ?? false; },
    });

    global.document = {
        querySelector: () => ({ getAttribute: () => 'a-csrf-token' }),
        dispatchEvent: (event) => heard.push(event),
        createElement: element,
        body: element('body'),
    };

    global.window = { PyBlade: { components: new Map() } };

    // Every request is left hanging until the test answers it, and what it
    // carried is kept so a test can see what it was built on
    global.fetch = (url, options) => new Promise((resolve, reject) => {
        asked.push(JSON.parse(options.body));
        answering.push({ resolve, reject });
    });

    const root = {
        nodeType: 1,
        attributes: [{ name: 'pb:id', value: 'c1' }],
        getAttribute: () => null,
        querySelectorAll: () => [],
    };

    const component = new Component('c1', root, { state: { title: '' } }, store);

    return { component, heard, store, asked: () => asked };
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

/** A body that hands over the given lines, as an ndjson answer does. */
function streamOf(lines) {
    const encoder = new TextEncoder();
    const chunks = lines.map(line => encoder.encode(JSON.stringify(line) + '\n'));
    let sent = 0;

    return {
        getReader: () => ({
            read: async () => (sent < chunks.length
                ? { done: false, value: chunks[sent++] }
                : { done: true, value: undefined }),
        }),
    };
}

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

// One request at a time
// ---------------------------------------------------------------------------

test('a second request waits for the first to be answered', async () => {
    const { component } = setUp();

    component.sendRequest({ action: 'increment', params: [] });
    component.sendRequest({ action: 'increment', params: [] });
    await settle();

    // Only the first has gone: the second is waiting to be built on its answer
    assert.equal(answering.length, 1);
});

test('and is built on the state that answer brought back', async () => {
    const { component, store, asked } = setUp();

    const first = component.sendRequest({ action: 'increment', params: [] });
    const second = component.sendRequest({ action: 'increment', params: [] });

    answering[0].resolve(answer({ count: 1 }));
    await first;
    await settle();

    // Without this the second would carry the count the first started from,
    // the server would work out the same answer twice, and a click would be lost
    assert.equal(asked()[1].snapshot.state.count, 1);

    answering[1].resolve(answer({ count: 2 }));
    await second;

    assert.deepEqual(store.get('c1').state, { count: 2 });
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

test('an answer older than one already applied is dropped', async () => {
    // Requests to one component no longer overlap, so this cannot arise from
    // clicking. It is kept as the guard it is: whatever else may one day put
    // two answers in flight, the older one must not land on the newer.
    const { component, store } = setUp();

    const first = component.sendRequest({ action: '$set', params: ['title', 'a'] });
    answering[0].resolve(answer({ title: 'a' }));
    await first;

    const second = component.sendRequest({ action: '$set', params: ['title', 'ab'] });
    answering[1].resolve(answer({ title: 'ab' }));
    await second;

    // The answer to the first request, arriving now
    component.apply(1, { html: null, snapshot: { state: { title: 'a' } } });

    assert.deepEqual(store.get('c1').state, { title: 'ab' });
});

// The error page, while developing
// ---------------------------------------------------------------------------

function refusalWithPage(status, page) {
    return {
        ok: false,
        status,
        headers: { get: () => 'application/json' },
        json: async () => ({ error: 'Something was wrong.', page }),
    };
}

test('a failure that comes back with the error page says so', async () => {
    const { component, heard } = setUp();

    const asking = component.sendRequest({ action: 'save', params: [] });
    answering[0].resolve(refusalWithPage(500, '<!DOCTYPE html><html>Boom</html>'));
    await asking;

    assert.match(heard[0].detail.page, /Boom/);
});

test('a failure with no page to show carries none', async () => {
    const { component, heard } = setUp();

    const asking = component.sendRequest({ action: 'save', params: [] });
    answering[0].resolve(refusal(500));
    await asking;

    assert.equal(heard[0].detail.page, null);
});

test('an answer that streamed and then went wrong is a failure, not an answer', async () => {
    const { component, store } = setUp();
    const before = store.get('c1');

    const asking = component.sendRequest({ action: 'tell', params: [] });
    answering[0].resolve({
        ok: true,
        headers: { get: () => 'application/x-ndjson' },
        body: streamOf([
            { stream: { to: 'out', content: 'half a ' } },
            { error: 'and then nothing', page: '<!DOCTYPE html><html>Boom</html>' },
        ]),
    });
    await asking;

    assert.deepEqual(store.get('c1'), before);
});

test('and what went wrong is said out loud', async () => {
    const { component, heard } = setUp();

    const asking = component.sendRequest({ action: 'tell', params: [] });
    answering[0].resolve({
        ok: true,
        headers: { get: () => 'application/x-ndjson' },
        body: streamOf([{ error: 'and then nothing', page: '<!DOCTYPE html><html>Boom</html>' }]),
    });
    await asking;

    assert.deepEqual(heard.map(event => event.type), ['live:error']);
    assert.match(heard[0].detail.page, /Boom/);
});

// Told to slow down
// ---------------------------------------------------------------------------

function tooMany(retryAfter) {
    return {
        ok: false,
        status: 429,
        headers: { get: (name) => (name === 'Retry-After' ? String(retryAfter) : 'application/json') },
        json: async () => ({ error: 'Too many requests.' }),
    };
}

/** Answer every request as it arrives, the way the given function says. */
async function answerAsTheyCome(how, until) {
    let answered = 0;
    while (!until()) {
        await new Promise(resolve => setTimeout(resolve, 20));
        while (answered < answering.length) answering[answered].resolve(how(answered++));
    }
}

test('a request refused for asking too often is sent again once it may be', async () => {
    const { component, store, heard } = setUp();
    let done = false;

    const asking = component.sendRequest({ action: 'save', params: [] }).then(() => { done = true; });
    await answerAsTheyCome(n => (n === 0 ? tooMany(1) : answer({ title: 'Saved' })), () => done);
    await asking;

    // Refused once, waited, sent again, and answered: nothing was lost
    assert.equal(answering.length, 2);
    assert.deepEqual(store.get('c1').state, { title: 'Saved' });
    assert.deepEqual(heard, []);
});

test('it waits as long as it was told before asking again', async () => {
    const { component } = setUp();
    let done = false;

    const started = Date.now();
    const asking = component.sendRequest({ action: 'save', params: [] }).then(() => { done = true; });
    await answerAsTheyCome(n => (n === 0 ? tooMany(1) : answer({ title: 'x' })), () => done);
    await asking;

    assert.ok(Date.now() - started >= 950);
});

test('a server that never lets up is given up on, and the page is told why', async () => {
    const { component, heard } = setUp();
    let done = false;

    const asking = component.sendRequest({ action: 'save', params: [] }).then(() => { done = true; });
    await answerAsTheyCome(() => tooMany(1), () => done);
    await asking;

    // The first, and three more after waiting: then it stops
    assert.equal(answering.length, 4);
    assert.equal(heard.length, 1);
    assert.equal(heard[0].detail.throttled, true);
});

test('an ordinary refusal asks nothing of the kind', async () => {
    const { component, heard } = setUp();

    const asking = component.sendRequest({ action: 'save', params: [] });
    answering[0].resolve(refusal(500));
    await asking;

    assert.equal(heard[0].detail.throttled, false);
    assert.equal(component.quietFor(), 0);
});
