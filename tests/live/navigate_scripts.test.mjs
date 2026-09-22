/**
 * What navigating decides about scripts and assets, before any DOM is touched.
 *
 * Running the scripts is DOM work and is checked in a browser.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

globalThis.window = { location: { href: 'https://example.test/posts/' } };

const { trackedChanged, headIdentity } = await import('../../pyblade/live/static/src/navigate.js');

function element(attributes = {}, outerHTML = '') {
    return { getAttribute: (name) => attributes[name] ?? null, outerHTML };
}

test('a tracked asset asked for with another query string is a new build', () => {
    assert.equal(trackedChanged(['/app.js?id=123'], ['/app.js?id=456']), true);
});

test('the same asset with the same query string is not', () => {
    assert.equal(trackedChanged(['/app.js?id=123'], ['/app.js?id=123']), false);
});

test('another file altogether is not a new build of this one', () => {
    assert.equal(trackedChanged(['/app.js?id=123'], ['/other.js?id=456']), false);
});

test('a tracked asset the page did not have is not one either', () => {
    assert.equal(trackedChanged([], ['/app.js?id=456']), false);
});

test('an element of the head that loads a file is told apart by the file', () => {
    assert.equal(headIdentity(element({ src: '/chart.js', defer: '' }, '<script src="/chart.js" defer></script>')), '/chart.js');
    assert.equal(headIdentity(element({ href: '/app.css' })), '/app.css');
});

test('one written inline is told apart by the whole of it', () => {
    assert.equal(headIdentity(element({}, '<style>p{}</style>')), '<style>p{}</style>');
});
