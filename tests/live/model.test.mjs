/**
 * Binding a form field to a property of the component.
 *
 * A field written pb:model reads its value from the property it names and puts
 * back whatever is typed into it. What it reads and writes depends on the kind
 * of field it is -- a checkbox says yes or no, or names one of several, a
 * multiple select gives a list -- and when it is sent depends on the modifiers.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { Directives } from '../../pyblade/live/static/src/directives.js';
import { fieldValue, writeField } from '../../pyblade/live/static/src/fields.js';
import { Component } from '../../pyblade/live/static/src/component.js';
import { Modifiers } from '../../pyblade/live/static/src/modifiers.js';

/** Enough of a form field for what is read off one and written to one. */
class FakeField {
    constructor(attributes = {}, properties = {}) {
        this.attributes = Object.entries(attributes).map(([name, value]) => ({ name, value }));
        this.tagName = (attributes.tag || 'INPUT').toUpperCase();
        this.type = attributes.type || 'text';
        this.value = properties.value ?? '';
        this.checked = properties.checked ?? false;
        this.options = properties.options || [];
        this.multiple = properties.multiple ?? false;
        this.listeners = [];
        this.ownerDocument = { querySelectorAll: () => this.siblings || [] };
    }

    getAttribute(name) {
        return this.attributes.find(a => a.name === name)?.value ?? null;
    }

    hasAttribute(name) {
        return this.getAttribute(name) !== null;
    }

    addEventListener(type, handler) {
        this.listeners.push({ type, handler });
    }

    fire(type) {
        this.listeners.filter(l => l.type === type).forEach(l => l.handler({ target: this }));
    }
}

const text = (value = '') => new FakeField({}, { value });

// Reading a field
// ---------------------------------------------------------------------------

test('a text field is its value', () => {
    assert.equal(fieldValue(text('Hello')), 'Hello');
});

test('a textarea is its value', () => {
    assert.equal(fieldValue(new FakeField({ tag: 'textarea' }, { value: 'Body' })), 'Body');
});

test('a lone checkbox says yes or no', () => {
    const box = new FakeField({ type: 'checkbox' }, { checked: true });

    assert.equal(fieldValue(box), true);
    box.checked = false;
    assert.equal(fieldValue(box), false);
});

test('checkboxes sharing a property give the ones that are ticked', () => {
    const a = new FakeField({ type: 'checkbox', 'pb:model': 'tags' }, { value: 'a', checked: true });
    const b = new FakeField({ type: 'checkbox', 'pb:model': 'tags' }, { value: 'b', checked: false });
    const c = new FakeField({ type: 'checkbox', 'pb:model': 'tags' }, { value: 'c', checked: true });
    [a, b, c].forEach(box => { box.siblings = [a, b, c]; });

    assert.deepEqual(fieldValue(a, 'tags'), ['a', 'c']);
});

test('a radio gives the value of the one that is chosen', () => {
    const one = new FakeField({ type: 'radio', 'pb:model': 'size' }, { value: 'S', checked: false });
    const two = new FakeField({ type: 'radio', 'pb:model': 'size' }, { value: 'M', checked: true });
    [one, two].forEach(radio => { radio.siblings = [one, two]; });

    assert.equal(fieldValue(one, 'size'), 'M');
});

test('a select is the option that is chosen', () => {
    const select = new FakeField({ tag: 'select' }, { value: 'b' });

    assert.equal(fieldValue(select), 'b');
});

test('a select taking several gives the ones that are chosen', () => {
    const select = new FakeField({ tag: 'select' }, {
        multiple: true,
        options: [
            { value: 'a', selected: true },
            { value: 'b', selected: false },
            { value: 'c', selected: true },
        ],
    });

    assert.deepEqual(fieldValue(select), ['a', 'c']);
});

// Writing a field
// ---------------------------------------------------------------------------

test('a text field is written', () => {
    const field = text('old');
    writeField(field, 'new');

    assert.equal(field.value, 'new');
});

test('a lone checkbox is ticked or not', () => {
    const box = new FakeField({ type: 'checkbox' });

    writeField(box, true);
    assert.equal(box.checked, true);

    writeField(box, false);
    assert.equal(box.checked, false);
});

test('a checkbox among several is ticked when the list holds its value', () => {
    const box = new FakeField({ type: 'checkbox', 'pb:model': 'tags' }, { value: 'b' });

    writeField(box, ['a', 'b']);
    assert.equal(box.checked, true);

    writeField(box, ['a']);
    assert.equal(box.checked, false);
});

test('a radio is chosen when the value is its own', () => {
    const radio = new FakeField({ type: 'radio' }, { value: 'M' });

    writeField(radio, 'M');
    assert.equal(radio.checked, true);

    writeField(radio, 'S');
    assert.equal(radio.checked, false);
});

test('a select taking several chooses the options in the list', () => {
    const select = new FakeField({ tag: 'select' }, {
        multiple: true,
        options: [{ value: 'a', selected: false }, { value: 'b', selected: true }],
    });

    writeField(select, ['a']);

    assert.deepEqual(select.options.map(o => o.selected), [true, false]);
});

test('a field is left alone when there is nothing to write', () => {
    const field = text('typed');

    writeField(field, undefined);

    assert.equal(field.value, 'typed');
});

// Casting what was read
// ---------------------------------------------------------------------------

test('a number is read as one', () => {
    assert.equal(Directives.castValue('42', { number: true }), 42);
    assert.equal(Directives.castValue('4.5', { number: true }), 4.5);
});

test('an empty field is not a number at all', () => {
    assert.equal(Directives.castValue('', { number: true }), '');
});

test('something that is not a number is left as it was written', () => {
    assert.equal(Directives.castValue('abc', { number: true }), 'abc');
});

test('a boolean is read from the words a form uses for one', () => {
    assert.equal(Directives.castValue('true', { boolean: true }), true);
    assert.equal(Directives.castValue('1', { boolean: true }), true);
    assert.equal(Directives.castValue('on', { boolean: true }), true);
    assert.equal(Directives.castValue('false', { boolean: true }), false);
    assert.equal(Directives.castValue('0', { boolean: true }), false);
    assert.equal(Directives.castValue('', { boolean: true }), false);
});

test('what a checkbox already answers is left as it is', () => {
    assert.equal(Directives.castValue(true, { boolean: true }), true);
    assert.deepEqual(Directives.castValue(['a'], { number: true }), ['a']);
});

test('a value is left as it is when nothing was asked of it', () => {
    assert.equal(Directives.castValue('42', {}), '42');
});

// What travels with the next request
// ---------------------------------------------------------------------------

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

test('nothing is waiting to be sent in a form nobody has touched', () => {
    assert.deepEqual(live({ title: 'Hello' }).pendingUpdatesToSend(), {});
});

test('what was typed is waiting to be sent', () => {
    const component = live({ title: 'Hello', body: '' });

    component.setLocal('title', 'Goodbye');

    assert.deepEqual(component.pendingUpdatesToSend(), { title: 'Goodbye' });
});

test('several fields wait together', () => {
    const component = live({ title: 'Hello', body: '' });

    component.setLocal('title', 'Goodbye');
    component.setLocal('body', 'Words');

    assert.deepEqual(component.pendingUpdatesToSend(), { title: 'Goodbye', body: 'Words' });
});

test('what the server has answered for is no longer waiting', () => {
    const component = live({ title: 'Hello' });
    component.setLocal('title', 'Goodbye');

    component.update({ html: null, snapshot: { state: { title: 'Goodbye' } } });

    assert.deepEqual(component.pendingUpdatesToSend(), {});
});

test('a field the reader is not in takes what the server says', () => {
    const component = live({ title: 'Hello' });

    component.update({ html: null, snapshot: { state: { title: 'From the server' } } });

    assert.equal(component.formState.values.title, 'From the server');
});

test('a field that was typed into keeps what was typed', () => {
    const component = live({ title: 'Hello' });
    component.setLocal('title', 'Typed');

    component.seedLocal('title', 'From the server');

    assert.equal(component.formState.values.title, 'Typed');
});

test('a property the request is already setting does not also wait', () => {
    const component = live({ query: '' });
    component.setLocal('query', 'abc');

    const updates = component.pendingUpdatesToSend({ action: '$set', params: ['query', 'abc'] });

    assert.deepEqual(updates, {});
});

test('the other fields still travel with it', () => {
    const component = live({ query: '', title: '' });
    component.setLocal('query', 'abc');
    component.setLocal('title', 'A title');

    const updates = component.pendingUpdatesToSend({ action: '$set', params: ['query', 'abc'] });

    assert.deepEqual(updates, { title: 'A title' });
});

test('an ordinary action carries everything that is waiting', () => {
    const component = live({ query: '' });
    component.setLocal('query', 'abc');

    assert.deepEqual(component.pendingUpdatesToSend({ action: 'save', params: [] }), { query: 'abc' });
});

// How long a live field waits before it sends
// ---------------------------------------------------------------------------

/** A component that records how long it was asked to wait. */
function recorder(state = {}) {
    return {
        id: 'c1',
        sent: [],
        formState: { values: { ...state } },
        getState: () => state,
        setLocal() {},
        seedLocal() {},
        onStateChange() {},
        setProperties(pair, delay) { this.sent.push({ pair, delay }); },
    };
}

const bindModel = (el, component, modifiers) =>
    Directives.handlers.model({
        el, expression: 'query', component, modifiers, signal: undefined,
    });

test('a live field waits a quarter of a second before it sends', () => {
    const component = recorder({ query: '' });
    const field = new FakeField({}, { value: '' });

    bindModel(field, component, Modifiers.from('pb:model.live'));
    field.value = 'abc';
    field.fire('input');

    assert.equal(component.sent[0].delay, 250);
});

test('unless it says how long to wait', () => {
    const component = recorder({ query: '' });
    const field = new FakeField({}, { value: '' });

    bindModel(field, component, Modifiers.from('pb:model.live.debounce.500ms'));
    field.value = 'abc';
    field.fire('input');

    assert.equal(component.sent[0].delay, 500);
});
