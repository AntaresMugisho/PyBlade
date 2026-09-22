/**
 * Which clicks navigation answers, and which it leaves to the browser.
 *
 * Only the decision is exercised here: it is the part that has to be right in
 * every case and the part that needs no document to be run against. The
 * fetching and the swapping are DOM work and are checked in a browser.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { Navigation } from '../../pyblade/live/static/src/navigate.js';

function link(attributes = {}) {
    return {
        attributes,
        getAttribute: (name) => attributes[name] ?? null,
        hasAttribute: (name) => name in attributes,
        get target() {
            return attributes.target || '';
        },
    };
}

function click(overrides = {}) {
    return { button: 0, defaultPrevented: false, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false, ...overrides };
}

// The page navigation is currently on
globalThis.window = { location: { href: 'https://example.test/posts/', origin: 'https://example.test',
                                  pathname: '/posts/', search: '' } };

test('a link to another page of the site is answered', () => {
    assert.equal(Navigation.intercepts(click(), link({ href: '/about/' })), true);
});

test('a link to another origin is left to the browser', () => {
    assert.equal(Navigation.intercepts(click(), link({ href: 'https://elsewhere.test/x' })), false);
});

test('a link opening another tab is left to the browser', () => {
    assert.equal(Navigation.intercepts(click(), link({ href: '/about/', target: '_blank' })), false);
});

test('a download is left to the browser', () => {
    assert.equal(Navigation.intercepts(click(), link({ href: '/file.pdf', download: '' })), false);
});

test('a fragment on the page itself is left to the browser', () => {
    assert.equal(Navigation.intercepts(click(), link({ href: '#section' })), false);
});

test('a link to the page we are already on is left to the browser', () => {
    assert.equal(Navigation.intercepts(click(), link({ href: '/posts/' })), false);
});

test('the same path with another query is answered', () => {
    assert.equal(Navigation.intercepts(click(), link({ href: '/posts/?page=2' })), true);
});

test('a click meant to open a tab is left to the browser', () => {
    for (const key of ['metaKey', 'ctrlKey', 'shiftKey', 'altKey']) {
        assert.equal(
            Navigation.intercepts(click({ [key]: true }), link({ href: '/about/' })),
            false,
            `${key} should not be answered`,
        );
    }
});

test('a middle click is left to the browser', () => {
    assert.equal(Navigation.intercepts(click({ button: 1 }), link({ href: '/about/' })), false);
});

test('a click something else already answered is left alone', () => {
    assert.equal(Navigation.intercepts(click({ defaultPrevented: true }), link({ href: '/about/' })), false);
});

test('a click on nothing marked is left to the browser', () => {
    assert.equal(Navigation.intercepts(click(), null), false);
});

test('a link with no href at all is left to the browser', () => {
    assert.equal(Navigation.intercepts(click(), link({})), false);
});
