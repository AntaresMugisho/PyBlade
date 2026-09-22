/**
 * The little that a directive asks about the state of a component.
 *
 * pb:show says when an element is on the page, and says it in terms of what the
 * component holds: a property, its opposite, or a comparison against something
 * written in the template. That is the whole of it -- the work is done in
 * Python, and a template is not the place to start writing another language.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { readCondition } from '../../pyblade/live/static/src/expressions.js';

const of = (expression, state) => readCondition(expression, state);

// A property on its own
// ---------------------------------------------------------------------------

test('a property is read for whether it holds anything', () => {
    assert.equal(of('visible', { visible: true }), true);
    assert.equal(of('visible', { visible: false }), false);
});

test('what a property holds is read the way a condition is anywhere', () => {
    assert.equal(of('count', { count: 3 }), true);
    assert.equal(of('count', { count: 0 }), false);
    assert.equal(of('name', { name: '' }), false);
    assert.equal(of('name', { name: 'Antares' }), true);
    assert.equal(of('rows', { rows: [] }), false);
    assert.equal(of('rows', { rows: [1] }), true);
});

test('a property the component does not hold holds nothing', () => {
    assert.equal(of('nowhere', {}), false);
});

test('a path walks into what a property holds', () => {
    assert.equal(of('post.published', { post: { published: true } }), true);
    assert.equal(of('post.published', { post: { published: false } }), false);
    assert.equal(of('post.nowhere', { post: {} }), false);
});

// The opposite of one
// ---------------------------------------------------------------------------

test('an exclamation mark turns it around', () => {
    assert.equal(of('!visible', { visible: true }), false);
    assert.equal(of('!visible', { visible: false }), true);
});

test('it may be written with a space after it', () => {
    assert.equal(of('! visible', { visible: false }), true);
});

// Comparisons
// ---------------------------------------------------------------------------

test('a number is compared with a number', () => {
    assert.equal(of('count > 3', { count: 4 }), true);
    assert.equal(of('count > 3', { count: 3 }), false);
    assert.equal(of('count >= 3', { count: 3 }), true);
    assert.equal(of('count < 3', { count: 2 }), true);
    assert.equal(of('count <= 3', { count: 3 }), true);
});

test('a value is compared for being the same or not', () => {
    assert.equal(of('status == "done"', { status: 'done' }), true);
    assert.equal(of("status == 'done'", { status: 'done' }), true);
    assert.equal(of('status != "done"', { status: 'open' }), true);
    assert.equal(of('status != "done"', { status: 'done' }), false);
});

test('one equals sign says the same thing as two', () => {
    assert.equal(of('status = "done"', { status: 'done' }), true);
});

test('the words a template writes for yes, no and nothing are read as such', () => {
    assert.equal(of('done == true', { done: true }), true);
    assert.equal(of('done == false', { done: false }), true);
    assert.equal(of('post == null', { post: null }), true);
    assert.equal(of('post != null', { post: {} }), true);
});

test('a comparison against a property compares the two', () => {
    assert.equal(of('count > limit', { count: 5, limit: 3 }), true);
    assert.equal(of('count > limit', { count: 2, limit: 3 }), false);
});

// What it refuses to guess at
// ---------------------------------------------------------------------------

test('nothing written is nothing shown', () => {
    assert.equal(of('', {}), false);
    assert.equal(of(null, {}), false);
});

test('something it cannot read is not a reason to hide an element', () => {
    // A template asking something this does not understand keeps its element:
    // a page missing what it should show is worse than one showing too much
    assert.equal(of('count > 3 and count < 10', { count: 5 }), true);
});
