/**
 * What an element says it is about, and what morphing is told to leave alone.
 *
 * pb:target narrows pb:loading and pb:dirty to one action or one property, so
 * that a spinner beside a save button is not shown by every keystroke elsewhere
 * on the form. pb:ignore, pb:replace and pb:key say how the new markup is to be
 * put over the old.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { Directives } from '../../pyblade/live/static/src/directives.js';
import { ignoresAttributes, ignoresContent, replacement } from '../../pyblade/live/static/src/morph.js';
import { Component } from '../../pyblade/live/static/src/component.js';

/** Enough of an element for what is read off one here. */
function element(attributes = {}) {
    return {
        nodeType: 1,
        attributes: Object.entries(attributes).map(([name, value]) => ({ name, value })),
        getAttribute(name) {
            return this.attributes.find(a => a.name === name)?.value ?? null;
        },
    };
}

/** A component holding the given state, as one arrives from the server. */
function live(state) {
    const root = {
        nodeType: 1,
        attributes: [{ name: 'pb:id', value: 'c1' }],
        getAttribute: () => null,
        querySelectorAll: () => [],
    };

    return new Component('c1', root, { state }, new Map());
}

/** Type into a field, as pb:model does when the reader does. */
function type(component, name, value) {
    component.formState.values[name] = value;
    component.formState.touchedFields.add(name);
}

// pb:target
// ---------------------------------------------------------------------------

test('an element that names nothing is about anything the component does', () => {
    assert.equal(Directives.matchesTarget(element(), { action: 'save' }), true);
});

test('an element is about the action it names', () => {
    const el = element({ 'pb:target': 'save' });

    assert.equal(Directives.matchesTarget(el, { action: 'save' }), true);
    assert.equal(Directives.matchesTarget(el, { action: 'delete' }), false);
});

test('an element may name several', () => {
    const el = element({ 'pb:target': 'save, publish' });

    assert.equal(Directives.matchesTarget(el, { action: 'publish' }), true);
    assert.equal(Directives.matchesTarget(el, { action: 'delete' }), false);
});

test('a property being set is named by the property, not by the action', () => {
    const el = element({ 'pb:target': 'title' });
    const setting = { action: '$set', params: ['title', 'Hello'] };

    assert.equal(Directives.matchesTarget(el, setting), true);
    assert.equal(Directives.matchesTarget(el, { action: '$set', params: ['body', 'x'] }), false);
});

test('an event being handled is named by the event', () => {
    const el = element({ 'pb:target': 'post-created' });
    const handling = { action: '$event', params: ['post-created', {}] };

    assert.equal(Directives.matchesTarget(el, handling), true);
});

test('a name is read as an action or as a property, whichever the request is', () => {
    const el = element({ 'pb:target': 'save' });

    assert.equal(Directives.matchesTarget(el, { action: 'save' }), true);
    assert.equal(Directives.matchesTarget(el, { action: '$set', params: ['save', 1] }), true);
});

test('an empty target is as good as none', () => {
    assert.equal(Directives.matchesTarget(element({ 'pb:target': '  ' }), { action: 'save' }), true);
});

// pb:ignore
// ---------------------------------------------------------------------------

test('an element that is not marked is morphed as any other', () => {
    const el = element({ class: 'x' });

    assert.equal(ignoresContent(el), false);
    assert.equal(ignoresAttributes(el), false);
});

test('pb:ignore leaves the element as it is', () => {
    assert.equal(ignoresContent(element({ 'pb:ignore': '' })), true);
});

test('pb:ignore.attrs leaves the attributes alone and the content morphed', () => {
    const el = element({ 'pb:ignore.attrs': '' });

    assert.equal(ignoresContent(el), false);
    assert.equal(ignoresAttributes(el), true);
});

// pb:replace
// ---------------------------------------------------------------------------

test('an element that is not marked asks for no replacement', () => {
    assert.equal(replacement(element()), null);
});

test('pb:replace puts the new content in place of the old', () => {
    assert.equal(replacement(element({ 'pb:replace': '' })), 'children');
});

test('pb:replace.self puts the new element in place of the old one', () => {
    assert.equal(replacement(element({ 'pb:replace.self': '' })), 'self');
});

// What is dirty: changed here and not yet answered for by the server
// ---------------------------------------------------------------------------

test('nothing is dirty in a component as it arrives', () => {
    const component = live({ title: 'Hello' });

    assert.deepEqual([...component.dirtyFields()], []);
});

test('a property changed here is dirty', () => {
    const component = live({ title: 'Hello' });

    type(component, 'title', 'Goodbye');

    assert.deepEqual([...component.dirtyFields()], ['title']);
});

test('a property changed back is not dirty', () => {
    const component = live({ title: 'Hello' });

    type(component, 'title', 'Goodbye');
    type(component, 'title', 'Hello');

    assert.deepEqual([...component.dirtyFields()], []);
});

test('a value the server answers with leaves nothing dirty', () => {
    const component = live({ title: 'Hello' });

    type(component, 'title', 'Goodbye');
    component.store.set('c1', { state: { title: 'Goodbye' } });

    assert.deepEqual([...component.dirtyFields()], []);
});

test('a list is compared by what it holds, not by being the same list', () => {
    const component = live({ tags: ['a'] });

    type(component, 'tags', ['a']);
    assert.deepEqual([...component.dirtyFields()], []);

    type(component, 'tags', ['a', 'b']);
    assert.deepEqual([...component.dirtyFields()], ['tags']);
});

test('whoever watches is told what is dirty', () => {
    const component = live({ title: 'Hello' });
    const told = [];
    component.onDirtyChange(dirty => told.push([...dirty]));

    type(component, 'title', 'Goodbye');
    component.refreshDirty();

    assert.deepEqual(told, [['title']]);
});

test('they are told again only when it has changed', () => {
    const component = live({ title: 'Hello', body: '' });
    const told = [];
    component.onDirtyChange(dirty => told.push([...dirty]));

    type(component, 'title', 'Goodbye');
    component.refreshDirty();
    component.refreshDirty();

    type(component, 'body', 'x');
    component.refreshDirty();

    assert.deepEqual(told, [['title'], ['title', 'body']]);
});

test('a property the server changed on its own is not unsaved work', () => {
    const component = live({ saved: 0 });

    // An action ran and the count went up: nothing was typed, so nothing is dirty
    component.store.set('c1', { state: { saved: 1 } });

    assert.deepEqual([...component.dirtyFields()], []);
});

test('an answer brings what was not typed into up to date', () => {
    const component = live({ saved: 0, title: 'Hello' });
    type(component, 'title', 'Goodbye');

    component.update({ html: null, snapshot: { state: { saved: 1, title: 'Hello' } } });

    assert.equal(component.formState.values.saved, 1);
    assert.equal(component.formState.values.title, 'Goodbye');
    assert.deepEqual([...component.dirtyFields()], ['title']);
});

test('an element streamed to is not morphed over', () => {
    // What an action streamed into it is what it is for: the server renders it
    // empty, so morphing would wipe out what has just been read
    assert.equal(ignoresContent(element({ 'pb:stream': 'answer' })), true);
    assert.equal(ignoresContent(element({ 'pb:stream.replace': 'status' })), true);
});
