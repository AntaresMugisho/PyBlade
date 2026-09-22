/**
 * Asking before an action runs.
 *
 * pb:confirm puts a question between the reader and the action. The asking is
 * done by a dialogue the project may replace, so what is checked here is the
 * deciding: which question is asked, what an answer does, and that an action
 * that was not confirmed never reaches the server.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { Directives } from '../../pyblade/live/static/src/directives.js';
import { confirmationOf } from '../../pyblade/live/static/src/confirm.js';

/** Enough of an element for what is read off one here. */
function element(attributes = {}) {
    return {
        nodeType: 1,
        attributes: Object.entries(attributes).map(([name, value]) => ({ name, value })),
        getAttribute(name) {
            return this.attributes.find(a => a.name === name)?.value ?? null;
        },
        hasAttribute(name) {
            return this.getAttribute(name) !== null;
        },
    };
}

// What an element asks
// ---------------------------------------------------------------------------

test('an element that asks nothing is not a confirmation', () => {
    assert.equal(confirmationOf(element({ 'pb:click': 'save' })), null);
});

test('the question is what the directive was given', () => {
    const asking = confirmationOf(element({ 'pb:confirm': 'Delete this post?' }));

    assert.equal(asking.message, 'Delete this post?');
});

test('an element that asks without saying what still asks', () => {
    const asking = confirmationOf(element({ 'pb:confirm': '' }));

    assert.notEqual(asking, null);
    assert.ok(asking.message.length > 0);
});

test('the reader is asked to type the word when it is written .prompt', () => {
    const asking = confirmationOf(element({ 'pb:confirm.prompt': 'Type DELETE to confirm|DELETE' }));

    assert.equal(asking.message, 'Type DELETE to confirm');
    assert.equal(asking.prompt, 'DELETE');
});

test('a prompt with no word of its own asks for one anyway', () => {
    const asking = confirmationOf(element({ 'pb:confirm.prompt': 'Really?' }));

    assert.equal(asking.message, 'Really?');
    assert.ok(asking.prompt.length > 0);
});

// What an answer does
// ---------------------------------------------------------------------------

/** A component that remembers what it was asked to do. */
function fakeComponent() {
    return {
        calls: [],
        events: [],
        callServerMethod(name, args, options) {
            this.calls.push({ name, args, options });
            return Promise.resolve();
        },
        emit(event) {
            this.events.push(event);
        },
    };
}

/** Answer every question the same way, in place of the dialogue. */
function answering(value) {
    return () => Promise.resolve(value);
}

test('an action with no question to ask is called straight away', async () => {
    const component = fakeComponent();

    await Directives.invoke('save', component, element({ 'pb:click': 'save' }), answering(false));

    assert.deepEqual(component.calls.map(c => c.name), ['save']);
});

test('an action that was confirmed is called', async () => {
    const component = fakeComponent();
    const el = element({ 'pb:click': 'delete', 'pb:confirm': 'Sure?' });

    await Directives.invoke('delete', component, el, answering(true));

    assert.deepEqual(component.calls.map(c => c.name), ['delete']);
});

test('an action that was refused is never called', async () => {
    const component = fakeComponent();
    const el = element({ 'pb:click': 'delete', 'pb:confirm': 'Sure?' });

    await Directives.invoke('delete', component, el, answering(false));

    assert.deepEqual(component.calls, []);
});

test('the server is told the reader was asked', async () => {
    const component = fakeComponent();
    const el = element({ 'pb:click': 'delete', 'pb:confirm': 'Sure?' });

    await Directives.invoke('delete', component, el, answering(true));

    assert.equal(component.calls[0].options.confirmed, true);
});

test('an action nobody had to confirm says nothing of the sort', async () => {
    const component = fakeComponent();

    await Directives.invoke('save', component, element({ 'pb:click': 'save' }), answering(true));

    assert.equal(component.calls[0].options?.confirmed, undefined);
});

test('an event may be emitted behind a question too', async () => {
    const component = fakeComponent();
    const el = element({ 'pb:click': "emit('wipe')", 'pb:confirm': 'Sure?' });

    await Directives.invoke("emit('wipe')", component, el, answering(false));
    assert.deepEqual(component.events, []);

    await Directives.invoke("emit('wipe')", component, el, answering(true));
    assert.deepEqual(component.events.map(e => e.name), ['wipe']);
});
