/**
 * What the page does when another page of a list is drawn.
 *
 * Two small things, both easy to get wrong: the address bar should say which
 * page is being looked at without filling the Back button with one entry per
 * click, and the reader should be looking at the top of what has just arrived
 * rather than at the bottom of it.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { Component } from '../../pyblade/live/static/src/component.js';

/** Enough of a page for the address bar and a scroll to be watched. */
function setUp(href = 'http://localhost/posts') {
    const calls = { replaced: [], pushed: [], scrolled: [] };
    let current = href;

    global.window = { location: { get href() { return current; } } };
    global.history = {
        state: { pyblade: true },
        replaceState(state, title, url) { calls.replaced.push(url); current = url; },
        pushState(state, title, url) { calls.pushed.push(url); current = url; },
    };
    global.document = { querySelector: (selector) => ({ selector, scrollIntoView: (o) => calls.scrolled.push(selector) }) };

    const root = {
        nodeType: 1,
        attributes: [{ name: 'pb:id', value: 'c1' }],
        getAttribute: () => null,
        querySelectorAll: () => [],
        closest: () => null,
        scrollIntoView: () => calls.scrolled.push('self'),
    };

    return { component: new Component('c1', root, { state: {} }, new Map()), calls };
}

const answer = (extra) => ({ html: null, snapshot: { state: {} }, ...extra });

// The address bar
// ---------------------------------------------------------------------------

test('the page being looked at is written into the address bar', () => {
    const { component, calls } = setUp();

    component.update(answer({ query: { page: 2 } }));

    assert.equal(calls.replaced.length, 1);
    assert.ok(calls.replaced[0].endsWith('/posts?page=2'));
});

test('it is written over rather than piled up in the history', () => {
    const { component, calls } = setUp();

    component.update(answer({ query: { page: 2 } }));
    component.update(answer({ query: { page: 3 } }));
    component.update(answer({ query: { page: 4 } }));

    assert.equal(calls.pushed.length, 0);
    assert.equal(calls.replaced.length, 3);
    assert.ok(calls.replaced.at(-1).endsWith('?page=4'));
});

test('what was already in the address bar is left there', () => {
    const { component, calls } = setUp('http://localhost/posts?sort=votes');

    component.update(answer({ query: { page: 2 } }));

    assert.ok(calls.replaced[0].includes('sort=votes'));
    assert.ok(calls.replaced[0].includes('page=2'));
});

test('a second paginator is written beside the first', () => {
    const { component, calls } = setUp();

    component.update(answer({ query: { page: 2, invoice_page: 5 } }));

    assert.ok(calls.replaced[0].includes('page=2'));
    assert.ok(calls.replaced[0].includes('invoice_page=5'));
});

test('an answer that says nothing about it leaves the address bar alone', () => {
    const { component, calls } = setUp();

    component.update(answer({}));

    assert.deepEqual(calls.replaced, []);
});

test('the address bar is not written over when nothing about it changed', () => {
    const { component, calls } = setUp('http://localhost/posts?page=2');

    component.update(answer({ query: { page: 2 } }));

    assert.deepEqual(calls.replaced, []);
});

// Scrolling
// ---------------------------------------------------------------------------

// Asked of the component directly: putting markup through update() would take
// the whole morph with it, and what is being checked is only where it scrolls
test('the reader is taken to the top of what has been drawn', () => {
    const { component, calls } = setUp();

    component.scrollAfterUpdate(true);

    assert.deepEqual(calls.scrolled, ['self']);
});

test('somewhere else may be named to scroll to', () => {
    const { component, calls } = setUp();

    component.scrollAfterUpdate('#posts');

    assert.deepEqual(calls.scrolled, ['#posts']);
});

test('scrolling may be turned off', () => {
    const { component, calls } = setUp();

    component.scrollAfterUpdate(false);

    assert.deepEqual(calls.scrolled, []);
});

test('nothing is scrolled when nothing was drawn', () => {
    const { component, calls } = setUp();

    component.update(answer({ html: null, scroll: true }));

    assert.deepEqual(calls.scrolled, []);
});
