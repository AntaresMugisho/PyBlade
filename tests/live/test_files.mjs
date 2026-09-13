/**
 * Choosing files for a property.
 *
 * A file input written pb:model sends what was chosen the moment it is chosen,
 * and leaves the property holding the signed notes that came back -- one note
 * where the input takes one file, a list where it takes several. Each choosing
 * starts the property over, the way a file input itself starts over.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { Directives } from '../../pyblade/live/static/src/directives.js';

/** The last fake request made, so a test can answer it how it likes. */
let lastRequest = null;

class FakeXHR {
    constructor() {
        this.upload = { addEventListener() {} };
        this.listeners = {};
        this.status = 200;
        this.responseText = '';
        lastRequest = this;
    }

    addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
    setRequestHeader() {}
    open(method, url) { this.method = method; this.url = url; }
    send(body) { this.body = body; }
    abort() { (this.listeners.abort || []).forEach(fn => fn()); }

    answer(status, payload) {
        this.status = status;
        this.responseText = JSON.stringify(payload);
        (this.listeners.load || []).forEach(fn => fn());
    }
}

/** Enough of a file input for something to be chosen in one. */
class FakeFileInput {
    constructor({ multiple = false } = {}) {
        this.type = 'file';
        this.multiple = multiple;
        this.files = [];
        this.value = '';
        this.listeners = [];
    }

    addEventListener(type, handler) { this.listeners.push({ type, handler }); }

    /** What a browser does when something hands the field its files. */
    dispatchEvent(event) {
        this.settled = Promise.all(
            this.listeners.filter(l => l.type === event.type).map(l => l.handler({ target: this }))
        );

        return true;
    }

    choose(...files) {
        this.files = files;
        this.value = files.map(file => file.name).join(',');
        this.dispatchEvent({ type: 'change' });

        return this.settled;
    }
}

/** Enough of a component to be set, and a page to announce on. */
function setUp() {
    lastRequest = null;
    global.XMLHttpRequest = FakeXHR;
    global.FormData = class {
        constructor() { this.parts = []; }
        append(k, v) { this.parts.push([k, v]); }
        getAll(k) { return this.parts.filter(([name]) => name === k).map(([, value]) => value); }
    };
    global.document = { querySelector: () => null };
    global.Event = class { constructor(type) { this.type = type; } };

    const announced = [];
    global.CustomEvent = class { constructor(type, init) { this.type = type; this.detail = init?.detail; } };
    global.window = { dispatchEvent: (event) => announced.push(event) };

    return {
        announced,
        component: {
            id: 'c1',
            store: new Map([['c1', { state: {}, checksum: 'signed' }]]),
            local: {},
            sent: [],
            setLocal(name, value) { this.local[name] = value; },
            setProperties(pair) { this.sent.push(pair); },
        },
    };
}

const holiday = { name: 'holiday.jpg', size: 2048 };
const sunset = { name: 'sunset.jpg', size: 1024 };

const bind = (el, component, property = 'photo') =>
    Directives.bindFileInput({ el, expression: property, component, signal: undefined });

test('choosing a file sends it', async () => {
    const { component } = setUp();
    const input = new FakeFileInput();
    bind(input, component);

    const choosing = input.choose(holiday);
    lastRequest.answer(200, { files: [{ reference: 'pyblade-upload:one', name: 'holiday.jpg' }] });
    await choosing;

    assert.equal(lastRequest.url, '/pyblade/live/upload/');
    assert.deepEqual(lastRequest.body.getAll('file'), [holiday]);
});

test('an input taking one file leaves the property holding one note', async () => {
    const { component } = setUp();
    const input = new FakeFileInput();
    bind(input, component);

    const choosing = input.choose(holiday);
    lastRequest.answer(200, { files: [{ reference: 'pyblade-upload:one' }] });
    await choosing;

    assert.equal(component.local.photo, 'pyblade-upload:one');
    assert.deepEqual(component.sent, [['photo', 'pyblade-upload:one']]);
});

test('an input taking several sends every one of them', async () => {
    const { component } = setUp();
    const input = new FakeFileInput({ multiple: true });
    bind(input, component, 'photos');

    const choosing = input.choose(holiday, sunset);
    lastRequest.answer(200, { files: [{ reference: 'one' }, { reference: 'two' }] });
    await choosing;

    assert.deepEqual(lastRequest.body.getAll('file'), [holiday, sunset]);
});

test('and leaves the property holding a note for each', async () => {
    const { component } = setUp();
    const input = new FakeFileInput({ multiple: true });
    bind(input, component, 'photos');

    const choosing = input.choose(holiday, sunset);
    lastRequest.answer(200, { files: [{ reference: 'one' }, { reference: 'two' }] });
    await choosing;

    assert.deepEqual(component.local.photos, ['one', 'two']);
    assert.deepEqual(component.sent, [['photos', ['one', 'two']]]);
});

test('a list of one is still a list', async () => {
    const { component } = setUp();
    const input = new FakeFileInput({ multiple: true });
    bind(input, component, 'photos');

    const choosing = input.choose(holiday);
    lastRequest.answer(200, { files: [{ reference: 'one' }] });
    await choosing;

    assert.deepEqual(component.local.photos, ['one']);
});

test('choosing again starts the property over', async () => {
    const { component } = setUp();
    const input = new FakeFileInput({ multiple: true });
    bind(input, component, 'photos');

    let choosing = input.choose(holiday, sunset);
    lastRequest.answer(200, { files: [{ reference: 'one' }, { reference: 'two' }] });
    await choosing;

    choosing = input.choose(holiday);
    lastRequest.answer(200, { files: [{ reference: 'three' }] });
    await choosing;

    assert.deepEqual(component.local.photos, ['three']);
});

test('choosing nothing is nothing to send', async () => {
    const { component } = setUp();
    const input = new FakeFileInput();
    bind(input, component);

    await input.choose();

    assert.equal(lastRequest, null);
    assert.deepEqual(component.sent, []);
});

test('what was chosen is announced as it goes', async () => {
    const { component, announced } = setUp();
    const input = new FakeFileInput({ multiple: true });
    bind(input, component, 'photos');

    const choosing = input.choose(holiday, sunset);
    lastRequest.answer(200, { files: [{ reference: 'one' }, { reference: 'two' }] });
    await choosing;

    assert.deepEqual(
        announced.map(event => event.type),
        ['pb:upload-start', 'pb:upload-progress', 'pb:upload-finish'],
    );
    assert.equal(announced[0].detail.property, 'photos');
});

test('a refusal leaves the property alone and says what was wrong', async () => {
    const { component, announced } = setUp();
    const input = new FakeFileInput();
    bind(input, component);

    const choosing = input.choose(holiday);
    lastRequest.answer(422, { errors: ['This file is too big.'] });
    await choosing;

    assert.deepEqual(component.sent, []);
    assert.equal(input.value, '');
    assert.deepEqual(announced.at(-1).detail.errors, ['This file is too big.']);
});

// Dropping files on the page
// ---------------------------------------------------------------------------

/** Enough of an element for files to be dragged over it and let go. */
class FakeDropTarget {
    constructor({ input = null } = {}) {
        this.attributes = {};
        this.input = input;
        this.listeners = {};
    }

    addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
    setAttribute(name, value) { this.attributes[name] = value; }
    removeAttribute(name) { delete this.attributes[name]; }
    hasAttribute(name) { return name in this.attributes; }
    querySelector() { return this.input; }

    drag(type, ...files) {
        let prevented = false;
        const event = {
            type,
            preventDefault: () => { prevented = true; },
            dataTransfer: { files },
        };

        const answers = (this.listeners[type] || []).map(handler => handler(event));

        return { prevented, done: Promise.all(answers) };
    }
}

const dropOn = (el, component, property = 'photo') =>
    Directives.handlers.drop({ el, expression: property, component, signal: undefined });

test('an element being dragged over says so', () => {
    const { component } = setUp();
    const target = new FakeDropTarget();
    dropOn(target, component);

    target.drag('dragover', holiday);

    assert.equal(target.hasAttribute('pb:dropping'), true);
});

test('and the browser is not left to open the file itself', () => {
    const { component } = setUp();
    const target = new FakeDropTarget();
    dropOn(target, component);

    assert.equal(target.drag('dragover', holiday).prevented, true);
});

test('it stops saying so when the file is taken away again', () => {
    const { component } = setUp();
    const target = new FakeDropTarget();
    dropOn(target, component);

    target.drag('dragover', holiday);
    target.drag('dragleave');

    assert.equal(target.hasAttribute('pb:dropping'), false);
});

test('and when the file is let go', async () => {
    const { component } = setUp();
    const target = new FakeDropTarget();
    dropOn(target, component);

    target.drag('dragover', holiday);
    const { done } = target.drag('drop', holiday);
    lastRequest.answer(200, { files: [{ reference: 'one' }] });
    await done;

    assert.equal(target.hasAttribute('pb:dropping'), false);
});

test('a file let go on it is sent', async () => {
    const { component } = setUp();
    const target = new FakeDropTarget();
    dropOn(target, component);

    const { done } = target.drag('drop', holiday);
    lastRequest.answer(200, { files: [{ reference: 'one' }] });
    await done;

    assert.deepEqual(lastRequest.body.getAll('file'), [holiday]);
    assert.equal(component.local.photo, 'one');
});

test('letting go of nothing is nothing to send', async () => {
    const { component } = setUp();
    const target = new FakeDropTarget();
    dropOn(target, component);

    await target.drag('drop').done;

    assert.equal(lastRequest, null);
});

test('with a file input inside it, the files go through the input', async () => {
    const { component } = setUp();
    const input = new FakeFileInput({ multiple: true });
    const target = new FakeDropTarget({ input });
    Directives.bindFileInput({ el: input, expression: 'photos', component, signal: undefined });
    dropOn(target, component, 'photos');

    const { done } = target.drag('drop', holiday, sunset);
    await done;

    lastRequest.answer(200, { files: [{ reference: 'one' }, { reference: 'two' }] });
    await input.settled;

    assert.deepEqual([...input.files], [holiday, sunset]);
    assert.deepEqual(component.local.photos, ['one', 'two']);
});

test('a target written .multiple holds every file let go on it', async () => {
    const { component } = setUp();
    const target = new FakeDropTarget();
    Directives.handlers.drop({
        el: target,
        expression: 'photos',
        component,
        modifiers: { has: (name) => name === 'multiple' },
        signal: undefined,
    });

    const { done } = target.drag('drop', holiday, sunset);
    lastRequest.answer(200, { files: [{ reference: 'one' }, { reference: 'two' }] });
    await done;

    assert.deepEqual(lastRequest.body.getAll('file'), [holiday, sunset]);
    assert.deepEqual(component.local.photos, ['one', 'two']);
});

test('one written without it takes the first and leaves the rest', async () => {
    const { component } = setUp();
    const target = new FakeDropTarget();
    dropOn(target, component);

    const { done } = target.drag('drop', holiday, sunset);
    lastRequest.answer(200, { files: [{ reference: 'one' }] });
    await done;

    assert.deepEqual(lastRequest.body.getAll('file'), [holiday]);
    assert.equal(component.local.photo, 'one');
});
