/**
 * Showing the error page over the page being worked on.
 *
 * While developing, a request that goes wrong comes back with the PyBlade error
 * page. It is shown in a dialogue of its own, in an iframe: the page is a whole
 * document with a stylesheet of its own, and it must neither inherit the styles
 * of the page it covers nor leak into them.
 *
 * Nothing of this happens in production, because the server sends no page.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { showErrorPage, errorDialogue } from '../../pyblade/live/static/src/errors.js';

/** Enough of a document for a dialogue to be built in and opened. */
function setUp() {
    const created = [];

    const element = (tag) => {
        const el = {
            tagName: tag.toUpperCase(),
            attributes: {},
            children: [],
            listeners: {},
            open: false,
            className: '',
            setAttribute(name, value) { this.attributes[name] = value; },
            getAttribute(name) { return this.attributes[name] ?? null; },
            removeAttribute(name) { delete this.attributes[name]; },
            // As in a browser: an element is connected while the document that
            // is on screen holds it, and stops being so when that page is gone
            get isConnected() {
                return global.document?.body?.children.includes(this) ?? false;
            },
            append(...kids) { this.children.push(...kids); },
            appendChild(kid) { this.children.push(kid); return kid; },
            addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
            querySelector(selector) {
                return this.children.find(kid =>
                    kid.tagName === selector.toUpperCase() || kid.className.includes(selector.replace('.', ''))
                ) || null;
            },
            showModal() { this.open = true; },
            close() { this.open = false; },
            fire(type, event = {}) { (this.listeners[type] || []).forEach(fn => fn({ target: this, ...event })); },
        };

        created.push(el);

        return el;
    };

    global.document = {
        createElement: element,
        body: element('body'),
        querySelector: (selector) => global.document.body.children.find(
            kid => kid.className.includes(selector.replace('.', ''))
        ) || null,
    };

    return { created };
}

const page = '<!DOCTYPE html><html><body>ValueError: a post needs a title</body></html>';

test('the page is shown in a dialogue', () => {
    setUp();

    const dialogue = showErrorPage(page);

    assert.equal(dialogue.tagName, 'DIALOG');
    assert.equal(dialogue.open, true);
});

test('and is put in an iframe rather than in the page itself', () => {
    setUp();

    const dialogue = showErrorPage(page);
    const frame = dialogue.children.find(child => child.tagName === 'IFRAME');

    assert.ok(frame);
    assert.equal(frame.getAttribute('srcdoc'), page);
});

test('the dialogue is part of the page it covers', () => {
    setUp();

    const dialogue = showErrorPage(page);

    assert.ok(document.body.children.includes(dialogue));
});

test('a second error is shown in the same dialogue', () => {
    setUp();

    const first = showErrorPage(page);
    const second = showErrorPage('<!DOCTYPE html><html><body>And another</body></html>');

    assert.equal(first, second);
    assert.equal(document.body.children.filter(child => child.tagName === 'DIALOG').length, 1);
});

test('and it is the newer error that is shown', () => {
    setUp();

    showErrorPage(page);
    const dialogue = showErrorPage('<!DOCTYPE html><html><body>And another</body></html>');
    const frame = dialogue.children.find(child => child.tagName === 'IFRAME');

    assert.match(frame.getAttribute('srcdoc'), /And another/);
});

test('it can be closed and asks for nothing before it is', () => {
    setUp();

    const dialogue = showErrorPage(page);
    const close = dialogue.children.find(child => child.tagName === 'BUTTON');

    close.fire('click');

    assert.equal(dialogue.open, false);
});

test('clicking the page behind it closes it too', () => {
    setUp();

    const dialogue = showErrorPage(page);
    dialogue.fire('click', { target: dialogue });

    assert.equal(dialogue.open, false);
});

test('clicking the error itself does not', () => {
    setUp();

    const dialogue = showErrorPage(page);
    const frame = dialogue.children.find(child => child.tagName === 'IFRAME');
    dialogue.fire('click', { target: frame });

    assert.equal(dialogue.open, true);
});

test('nothing is built until something has gone wrong', () => {
    setUp();

    assert.equal(errorDialogue(), null);
});
