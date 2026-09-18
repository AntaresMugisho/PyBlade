/**
 * Which of the pushes an update came back with the page still has to add.
 *
 * The adding itself is DOM work and is checked in a browser.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { missing } from '../../pyblade/live/static/src/stacks.js';

const push = (stack, key) => ({ stack, key, html: `<i>${key}</i>` });

test('a push the page does not hold is added', () => {
    assert.deepEqual(missing([push('scripts', 'a')], new Set(), new Set(['scripts'])), [push('scripts', 'a')]);
});

test('a push the page holds already is not', () => {
    assert.deepEqual(missing([push('scripts', 'a')], new Set(['scripts\0a']), new Set(['scripts'])), []);
});

test('the same push held in another stack is still added to this one', () => {
    const added = missing([push('scripts', 'a')], new Set(['styles\0a']), new Set(['scripts', 'styles']));

    assert.deepEqual(added, [push('scripts', 'a')]);
});

test('a push to a stack the page does not have goes nowhere', () => {
    assert.deepEqual(missing([push('nowhere', 'a')], new Set(), new Set(['scripts'])), []);
});

test('the same push twice is added once, in the order they came', () => {
    const added = missing(
        [push('s', 'a'), push('s', 'b'), push('s', 'a')], new Set(), new Set(['s']),
    );

    assert.deepEqual(added, [push('s', 'a'), push('s', 'b')]);
});
