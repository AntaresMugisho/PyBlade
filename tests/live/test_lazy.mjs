/**
 * Asking for a component that was not built with the page.
 *
 * A component written @lazy arrives as a skeleton carrying pb:lazy. The page
 * asks the server for the real thing as soon as it has loaded -- or, where the
 * marker says visible, once the skeleton has been scrolled to.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { loadWhenReady } from '../../pyblade/live/static/src/lazy.js';

/** Enough of a skeleton element to carry the marker and be watched. */
class FakeElement {
    constructor(attributes = {}) {
        this.attributes = { ...attributes };
    }

    getAttribute(name) { return name in this.attributes ? this.attributes[name] : null; }
    removeAttribute(name) { delete this.attributes[name]; }
    hasAttribute(name) { return name in this.attributes; }
}

/** Enough of a component to be asked for. */
function fakeComponent() {
    return { asked: [], async callServerMethod(action) { this.asked.push(action); } };
}

/** An IntersectionObserver a test drives itself. */
function watching() {
    const observers = [];

    global.IntersectionObserver = class {
        constructor(callback) {
            this.callback = callback;
            this.watched = [];
            this.stopped = false;
            observers.push(this);
        }

        observe(el) { this.watched.push(el); }
        disconnect() { this.stopped = true; }

        // A real observer hands nothing over once it has been disconnected
        seen() { if (!this.stopped) this.callback([{ isIntersecting: true }], this); }
        passedBy() { if (!this.stopped) this.callback([{ isIntersecting: false }], this); }
    };

    return observers;
}

test('a component that is not waiting to be seen is asked for at once', () => {
    const component = fakeComponent();

    loadWhenReady(component, new FakeElement({ 'pb:lazy': '' }));

    assert.deepEqual(component.asked, ['$lazy']);
});

test('one that carries no marker is not asked for at all', () => {
    const component = fakeComponent();

    loadWhenReady(component, new FakeElement());

    assert.deepEqual(component.asked, []);
});

test('the marker is taken off, so a second look does not ask again', () => {
    const component = fakeComponent();
    const el = new FakeElement({ 'pb:lazy': '' });

    loadWhenReady(component, el);
    loadWhenReady(component, el);

    assert.deepEqual(component.asked, ['$lazy']);
});

test('one written visible is not asked for until it is seen', () => {
    watching();
    const component = fakeComponent();

    loadWhenReady(component, new FakeElement({ 'pb:lazy': 'visible' }));

    assert.deepEqual(component.asked, []);
});

test('and is asked for once it has been', () => {
    const observers = watching();
    const component = fakeComponent();

    loadWhenReady(component, new FakeElement({ 'pb:lazy': 'visible' }));
    observers[0].seen();

    assert.deepEqual(component.asked, ['$lazy']);
});

test('something scrolled past without being reached is still not asked for', () => {
    const observers = watching();
    const component = fakeComponent();

    loadWhenReady(component, new FakeElement({ 'pb:lazy': 'visible' }));
    observers[0].passedBy();

    assert.deepEqual(component.asked, []);
});

test('nothing is watched for it once it has been asked for', () => {
    const observers = watching();
    const component = fakeComponent();

    loadWhenReady(component, new FakeElement({ 'pb:lazy': 'visible' }));
    observers[0].seen();
    observers[0].seen();

    assert.deepEqual(component.asked, ['$lazy']);
    assert.equal(observers[0].stopped, true);
});

test('a browser that cannot watch asks at once rather than never', () => {
    delete global.IntersectionObserver;
    const component = fakeComponent();

    loadWhenReady(component, new FakeElement({ 'pb:lazy': 'visible' }));

    assert.deepEqual(component.asked, ['$lazy']);
});
