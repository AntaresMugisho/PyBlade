/**
 * What @persist keeps while a component is updated.
 *
 * Moving an element into a new page is DOM work and is checked in a browser.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { morphCallbacks, persistedName } from '../../pyblade/live/static/src/morph.js';

function element(attributes = {}) {
    return {
        nodeType: 1,
        attributes: Object.entries(attributes).map(([name, value]) => ({ name, value })),
        getAttribute: (name) => attributes[name] ?? null,
    };
}

const morphs = (oldNode, newNode) => morphCallbacks().beforeNodeMorphed(oldNode, newNode);

test('an element written @persist has the name it was written with', () => {
    assert.equal(persistedName(element({ 'data-pb-persist': 'player' })), 'player');
});

test('any other element has none', () => {
    assert.equal(persistedName(element({ class: 'player' })), null);
});

test('an update leaves a persisted element exactly as it is', () => {
    const player = () => element({ 'data-pb-persist': 'player' });

    assert.equal(morphs(player(), player()), false);
});

test('one the new markup has another @persist for is brought up to date', () => {
    assert.equal(morphs(element({ 'data-pb-persist': 'player' }), element({ 'data-pb-persist': 'chat' })), true);
});

test('an ordinary element is morphed as ever', () => {
    assert.equal(morphs(element({ class: 'comments' }), element({ class: 'comments' })), true);
});
