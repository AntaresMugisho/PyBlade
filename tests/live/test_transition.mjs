/**
 * How an element comes and goes.
 *
 * pb:transition says that an element appearing or leaving is to be animated
 * rather than to blink in and out. What is checked here is what the modifiers
 * add up to -- how long, after how long, what moves, and in which direction the
 * element is animated at all. The animating itself is the browser's.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { transitionOf, pollRate } from '../../pyblade/live/static/src/transition.js';
import { Modifiers } from '../../pyblade/live/static/src/modifiers.js';
import { Directives } from '../../pyblade/live/static/src/directives.js';

/** Enough of an element for the attributes to be read off it. */
function element(attributes = {}) {
    return {
        nodeType: 1,
        attributes: Object.entries(attributes).map(([name, value]) => ({ name, value })),
    };
}

// Whether there is one at all
// ---------------------------------------------------------------------------

test('an element that says nothing is not animated', () => {
    assert.equal(transitionOf(element({ class: 'card' })), null);
});

test('an element written pb:transition is', () => {
    assert.notEqual(transitionOf(element({ 'pb:transition': '' })), null);
});

// How long
// ---------------------------------------------------------------------------

test('a transition takes 150ms unless it says otherwise', () => {
    assert.equal(transitionOf(element({ 'pb:transition': '' })).duration, 150);
});

test('it may say how long in milliseconds', () => {
    assert.equal(transitionOf(element({ 'pb:transition.duration.400ms': '' })).duration, 400);
});

test('or in seconds', () => {
    assert.equal(transitionOf(element({ 'pb:transition.duration.2s': '' })).duration, 2000);
});

test('it may wait before it starts', () => {
    assert.equal(transitionOf(element({ 'pb:transition.delay.300ms': '' })).delay, 300);
});

test('and waits for nothing unless it says so', () => {
    assert.equal(transitionOf(element({ 'pb:transition': '' })).delay, 0);
});

// What moves
// ---------------------------------------------------------------------------

test('an element fades and grows unless it asks for one of the two', () => {
    const spec = transitionOf(element({ 'pb:transition': '' }));

    assert.deepEqual([spec.opacity, spec.scale], [true, true]);
});

test('asking only to fade leaves the size alone', () => {
    const spec = transitionOf(element({ 'pb:transition.opacity': '' }));

    assert.deepEqual([spec.opacity, spec.scale], [true, false]);
});

test('asking only to grow leaves it solid', () => {
    const spec = transitionOf(element({ 'pb:transition.scale': '' }));

    assert.deepEqual([spec.opacity, spec.scale], [false, true]);
});

test('where it grows from may be said', () => {
    assert.equal(transitionOf(element({ 'pb:transition.origin.top': '' })).origin, 'top');
});

test('and is the middle unless it is', () => {
    assert.equal(transitionOf(element({ 'pb:transition': '' })).origin, 'center');
});

// Which way
// ---------------------------------------------------------------------------

test('an element is animated both coming and going', () => {
    const spec = transitionOf(element({ 'pb:transition': '' }));

    assert.deepEqual([spec.entering, spec.leaving], [true, true]);
});

test('written .in it is only animated coming', () => {
    const spec = transitionOf(element({ 'pb:transition.in': '' }));

    assert.deepEqual([spec.entering, spec.leaving], [true, false]);
});

test('written .out it is only animated going', () => {
    const spec = transitionOf(element({ 'pb:transition.out': '' }));

    assert.deepEqual([spec.entering, spec.leaving], [false, true]);
});

test('the modifiers may be written together', () => {
    const spec = transitionOf(element({ 'pb:transition.out.opacity.duration.1s.origin.bottom': '' }));

    assert.deepEqual(
        [spec.entering, spec.leaving, spec.opacity, spec.scale, spec.duration, spec.origin],
        [false, true, true, false, 1000, 'bottom'],
    );
});

// How often a component polls
// ---------------------------------------------------------------------------

test('a tab being read polls at the rate it was given', () => {
    assert.equal(pollRate(2000, { hidden: false, keepAlive: false }), 2000);
});

test('a tab in the background polls at a twentieth of it', () => {
    // The page nobody is looking at is not worth the traffic: 95% less of it
    assert.equal(pollRate(2000, { hidden: true, keepAlive: false }), 40000);
});

test('unless it was told to keep going', () => {
    assert.equal(pollRate(2000, { hidden: true, keepAlive: true }), 2000);
});

test('a rate of its own is kept in the background too', () => {
    assert.equal(pollRate(15000, { hidden: true, keepAlive: false }), 300000);
});

// What a poll actually does per tick
// ---------------------------------------------------------------------------

/** A component that remembers what it was asked, and how slowly it answers. */
function pollable({ answerAfter = 0 } = {}) {
    return {
        refreshes: 0,
        calls: [],
        answerAfter,
        refresh() {
            this.refreshes += 1;
            return new Promise(r => setTimeout(r, this.answerAfter));
        },
        callServerMethod(name) {
            this.calls.push(name);
            return Promise.resolve();
        },
        onDestroy() {},
    };
}

function pollElement(attribute) {
    const el = {
        nodeType: 1,
        attributes: [{ name: attribute, value: attribute.includes('=') ? '' : '' }],
        getAttribute: () => null,
        querySelectorAll: () => [],
    };
    return el;
}

test('a poll asks for a refresh when it names no action', async () => {
    const component = pollable();
    const controller = new AbortController();

    Directives.handlers.poll({
        el: pollElement('pb:poll'),
        expression: '',
        component,
        modifiers: Modifiers.from('pb:poll.60ms'),
        signal: controller.signal,
    });

    await new Promise(r => setTimeout(r, 200));
    controller.abort();

    assert.ok(component.refreshes >= 2, `expected at least two refreshes, got ${component.refreshes}`);
});

test('a poll calls the action it names instead', async () => {
    const component = pollable();
    const controller = new AbortController();

    Directives.handlers.poll({
        el: pollElement('pb:poll'),
        expression: 'refresh_posts',
        component,
        modifiers: Modifiers.from('pb:poll.60ms'),
        signal: controller.signal,
    });

    await new Promise(r => setTimeout(r, 200));
    controller.abort();

    assert.ok(component.calls.every(name => name === 'refresh_posts'));
    assert.ok(component.calls.length >= 2);
});

test('a server slower than the interval is not asked again while it answers', async () => {
    const component = pollable({ answerAfter: 500 });
    const controller = new AbortController();

    Directives.handlers.poll({
        el: pollElement('pb:poll'),
        expression: '',
        component,
        modifiers: Modifiers.from('pb:poll.50ms'),
        signal: controller.signal,
    });

    await new Promise(r => setTimeout(r, 300));
    controller.abort();

    assert.equal(component.refreshes, 1);
});

test('a poll stops when its binding is dropped', async () => {
    const component = pollable();
    const controller = new AbortController();

    Directives.handlers.poll({
        el: pollElement('pb:poll'),
        expression: '',
        component,
        modifiers: Modifiers.from('pb:poll.50ms'),
        signal: controller.signal,
    });

    await new Promise(r => setTimeout(r, 120));
    controller.abort();
    const stoppedAt = component.refreshes;

    await new Promise(r => setTimeout(r, 200));

    assert.equal(component.refreshes, stoppedAt);
});
