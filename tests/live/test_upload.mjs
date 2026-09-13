/**
 * Sending a file, watching it go, and stopping it part way.
 *
 * The request is made the older way, by XMLHttpRequest, because that is the one
 * that reports bytes as they go and can be abandoned. Here it is a fake one, so
 * what is checked is what PyBlade does with it: what it sends, what it reports,
 * and what it does when the answer is no.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { cancelUpload, isUploading, uploadFile } from '../../pyblade/live/static/src/upload.js';

/** The last fake request made, so a test can answer it how it likes. */
let lastRequest = null;

class FakeXHR {
    constructor() {
        this.upload = { listeners: {}, addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); } };
        this.listeners = {};
        this.headers = {};
        this.status = 200;
        this.responseText = '';
        lastRequest = this;
    }

    addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
    setRequestHeader(name, value) { this.headers[name] = value; }
    open(method, url) { this.method = method; this.url = url; }
    send(body) { this.body = body; }
    abort() { this.fire('abort'); }

    fire(type) { (this.listeners[type] || []).forEach(fn => fn()); }
    progress(loaded, total) {
        (this.upload.listeners.progress || []).forEach(fn => fn({ lengthComputable: true, loaded, total }));
    }

    answer(status, payload) {
        this.status = status;
        this.responseText = JSON.stringify(payload);
        this.fire('load');
    }
}

/** Enough of the page and of a component for an upload to be made from one. */
function setUp() {
    lastRequest = null;
    global.XMLHttpRequest = FakeXHR;
    global.FormData = class {
        constructor() { this.parts = []; }
        append(k, v) { this.parts.push([k, v]); }
        get entries() { return Object.fromEntries(this.parts); }
        getAll(k) { return this.parts.filter(([name]) => name === k).map(([, value]) => value); }
    };
    global.document = { querySelector: () => ({ getAttribute: () => 'a-csrf-token' }) };

    return { id: 'c1', store: new Map([['c1', { state: {}, checksum: 'signed' }]]) };
}

const aFile = { name: 'holiday.jpg', size: 2048 };

test('the file, the property and the snapshot are what is sent', async () => {
    const component = setUp();

    const sending = uploadFile(component, 'photo', aFile);
    lastRequest.answer(200, { files: [{ reference: 'pyblade-upload:note', name: 'holiday.jpg', size: 2048 }] });
    await sending;

    assert.equal(lastRequest.method, 'POST');
    assert.equal(lastRequest.url, '/pyblade/live/upload/');
    assert.equal(lastRequest.body.entries.file, aFile);
    assert.equal(lastRequest.body.entries.property, 'photo');
    assert.deepEqual(JSON.parse(lastRequest.body.entries.snapshot), { state: {}, checksum: 'signed' });
});

test('the request carries the token the page was given', async () => {
    const component = setUp();

    const sending = uploadFile(component, 'photo', aFile);
    lastRequest.answer(200, { files: [{ reference: 'pyblade-upload:note' }] });
    await sending;

    assert.equal(lastRequest.headers['X-CSRFToken'], 'a-csrf-token');
});

test('the note that comes back is what is answered', async () => {
    const component = setUp();

    const sending = uploadFile(component, 'photo', aFile);
    lastRequest.answer(200, { files: [{ reference: 'pyblade-upload:note', name: 'holiday.jpg', size: 2048 }] });

    assert.equal((await sending).files[0].reference, 'pyblade-upload:note');
});

test('how far along it is, is reported as it goes', async () => {
    const component = setUp();
    const seen = [];

    const sending = uploadFile(component, 'photo', aFile, { onProgress: p => seen.push(p.percent) });
    lastRequest.progress(512, 2048);
    lastRequest.progress(1024, 2048);
    lastRequest.answer(200, { files: [{ reference: 'pyblade-upload:note' }] });
    await sending;

    assert.deepEqual(seen, [25, 50, 100]);
});

test('a file that is refused answers with what was wrong with it', async () => {
    const component = setUp();

    const sending = uploadFile(component, 'photo', aFile);
    lastRequest.answer(422, { errors: ['This file is too big. It must be no more than 2mb.'] });

    assert.deepEqual((await sending).errors, ['This file is too big. It must be no more than 2mb.']);
});

test('a request that never arrives is not waited on for ever', async () => {
    const component = setUp();

    const sending = uploadFile(component, 'photo', aFile);
    lastRequest.fire('error');

    assert.ok((await sending).errors.length);
});

test('a file on its way can be stopped', async () => {
    const component = setUp();

    const sending = uploadFile(component, 'photo', aFile);
    assert.equal(isUploading(component, 'photo'), true);

    assert.equal(cancelUpload(component, 'photo'), true);

    assert.equal(await sending, null);
    assert.equal(isUploading(component, 'photo'), false);
});

test('stopping one that is not going is nothing to do', () => {
    const component = setUp();

    assert.equal(cancelUpload(component, 'photo'), false);
});

test('choosing another file stops the one still going', async () => {
    const component = setUp();

    const first = uploadFile(component, 'photo', aFile);
    const firstRequest = lastRequest;

    const second = uploadFile(component, 'photo', { name: 'other.jpg', size: 10 });
    lastRequest.answer(200, { files: [{ reference: 'pyblade-upload:second' }] });

    assert.equal(await first, null);
    assert.equal((await second).files[0].reference, 'pyblade-upload:second');
    assert.notEqual(firstRequest, lastRequest);
});

test('two properties upload side by side without stopping each other', async () => {
    const component = setUp();

    const photo = uploadFile(component, 'photo', aFile);
    const photoRequest = lastRequest;

    const scan = uploadFile(component, 'scan', aFile);
    assert.equal(isUploading(component, 'photo'), true);

    photoRequest.answer(200, { files: [{ reference: 'pyblade-upload:photo' }] });
    lastRequest.answer(200, { files: [{ reference: 'pyblade-upload:scan' }] });

    assert.equal((await photo).files[0].reference, 'pyblade-upload:photo');
    assert.equal((await scan).files[0].reference, 'pyblade-upload:scan');
});

// Several files at once
// ---------------------------------------------------------------------------

const another = { name: 'sunset.jpg', size: 1024 };

test('every file chosen goes in the one request', async () => {
    const component = setUp();

    const sending = uploadFile(component, 'photos', [aFile, another]);
    lastRequest.answer(200, { files: [{ reference: 'a' }, { reference: 'b' }] });
    await sending;

    assert.deepEqual(lastRequest.body.getAll('file'), [aFile, another]);
});

test('a note comes back for each of them', async () => {
    const component = setUp();

    const sending = uploadFile(component, 'photos', [aFile, another]);
    lastRequest.answer(200, { files: [{ reference: 'a' }, { reference: 'b' }] });

    assert.deepEqual((await sending).files.map(file => file.reference), ['a', 'b']);
});

test('how far along the lot is, is what is reported', async () => {
    const component = setUp();
    const seen = [];

    const sending = uploadFile(component, 'photos', [aFile, another], {
        onProgress: p => seen.push(p.percent),
    });
    lastRequest.progress(1536, 3072);
    lastRequest.answer(200, { files: [{ reference: 'a' }, { reference: 'b' }] });
    await sending;

    assert.deepEqual(seen, [50, 100]);
});
