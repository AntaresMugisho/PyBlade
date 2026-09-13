/**
 * What a directive reads from the modifiers written after its name.
 *
 * A directive is written pb:name.one.two, and everything after the name says
 * how it is to behave. Several of them take an argument -- a delay, a duration,
 * a transform origin -- which is the segment that follows them, so the reading
 * of it belongs in one place rather than in every handler that needs one.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { Modifiers } from '../../pyblade/live/static/src/modifiers.js';

const of = (name) => Modifiers.from(name);

// Reading the name and the modifiers apart
// ---------------------------------------------------------------------------

test('a directive written with no modifier has none', () => {
    assert.deepEqual(of('pb:click').list, []);
});

test('the modifiers are what follows the name', () => {
    assert.deepEqual(of('pb:model.live').list, ['live']);
});

test('every modifier is kept, however many there are', () => {
    assert.deepEqual(of('pb:model.live.debounce.500ms').list, ['live', 'debounce', '500ms']);
});

// Flags
// ---------------------------------------------------------------------------

test('a flag that is written is there', () => {
    assert.equal(of('pb:model.live').has('live'), true);
});

test('a flag that is not written is not', () => {
    assert.equal(of('pb:model.live').has('blur'), false);
});

test('a flag is found wherever it is written', () => {
    assert.equal(of('pb:model.debounce.500ms.live').has('live'), true);
});

// Arguments
// ---------------------------------------------------------------------------

test('the argument of a modifier is what follows it', () => {
    assert.equal(of('pb:transition.origin.top').get('origin'), 'top');
});

test('a modifier that was not written falls back', () => {
    assert.equal(of('pb:transition.opacity').get('origin', 'center'), 'center');
});

test('a modifier written last has no argument and falls back', () => {
    assert.equal(of('pb:transition.opacity.origin').get('origin', 'center'), 'center');
});

test('one modifier does not read the argument of another', () => {
    const modifiers = of('pb:transition.duration.150ms.origin.top');

    assert.equal(modifiers.get('duration'), '150ms');
    assert.equal(modifiers.get('origin'), 'top');
});

// Durations
// ---------------------------------------------------------------------------

test('a duration in milliseconds is read as it is written', () => {
    assert.equal(of('pb:model.debounce.500ms').duration('debounce', 300), 500);
});

test('a duration in seconds is read in milliseconds', () => {
    assert.equal(of('pb:transition.duration.2s').duration('duration', 150), 2000);
});

test('a fraction cannot be written, the modifiers being told apart by the dot', () => {
    // '.duration.1.5s' reads as the modifiers 'duration', '1' and '5s': a
    // duration shorter than a second is written in milliseconds instead.
    assert.equal(of('pb:transition.duration.1.5s').duration('duration', 150), 1);
    assert.equal(of('pb:transition.duration.1500ms').duration('duration', 150), 1500);
});

test('a bare number is read as milliseconds', () => {
    assert.equal(of('pb:loading.delay.250').duration('delay', 200), 250);
});

test('a duration that was not written falls back', () => {
    assert.equal(of('pb:model.live').duration('debounce', 300), 300);
});

test('something that is not a duration falls back', () => {
    assert.equal(of('pb:model.debounce.soon').duration('debounce', 300), 300);
});

// A duration written on its own, as pb:poll.15s is
// ---------------------------------------------------------------------------

test('a duration written with no name is found', () => {
    assert.equal(of('pb:poll.15s').timing(2000), 15000);
});

test('it is found among the other modifiers', () => {
    assert.equal(of('pb:poll.keep-alive.15s').timing(2000), 15000);
});

test('milliseconds may be written instead', () => {
    assert.equal(of('pb:poll.15000ms').timing(2000), 15000);
});

test('a poll with no timing of its own falls back', () => {
    assert.equal(of('pb:poll.visible').timing(2000), 2000);
});

// What the handlers that only ever took one modifier still read
// ---------------------------------------------------------------------------

test('the first modifier is the one a handler of old reads', () => {
    assert.equal(of('pb:click.prevent').first, 'prevent');
});

test('and it is nothing when none is written', () => {
    assert.equal(of('pb:click').first, null);
});
