/**
 * Reading an answer that arrives in pieces.
 *
 * An action written @streamed answers a line of JSON at a time: what it streams
 * as it goes, and then the answer itself. The pieces the network hands over
 * have nothing to do with the lines -- one piece may hold three of them, or
 * half of one -- so what matters here is that the lines are put back together
 * whatever the pieces looked like.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

import { readLines } from '../../pyblade/live/static/src/streaming.js';

/** A response body handed over in exactly these pieces. */
function body(pieces) {
    const encoder = new TextEncoder();
    let index = 0;

    return {
        getReader: () => ({
            read: async () => (index < pieces.length
                ? { done: false, value: encoder.encode(pieces[index++]) }
                : { done: true, value: undefined }),
        }),
    };
}

/** Read a whole response, collecting the lines it gave. */
async function linesOf(pieces) {
    const seen = [];

    await readLines(body(pieces), line => seen.push(line));

    return seen;
}

test('a line arriving on its own is read', async () => {
    assert.deepEqual(await linesOf(['{"a":1}\n']), [{ a: 1 }]);
});

test('several lines in one piece are read apart', async () => {
    assert.deepEqual(await linesOf(['{"a":1}\n{"a":2}\n']), [{ a: 1 }, { a: 2 }]);
});

test('a line split across two pieces is put back together', async () => {
    assert.deepEqual(await linesOf(['{"a":', '1}\n']), [{ a: 1 }]);
});

test('a line split in the middle of a word is too', async () => {
    assert.deepEqual(await linesOf(['{"greet":"he', 'llo"}\n']), [{ greet: 'hello' }]);
});

test('a line split across many pieces is too', async () => {
    const pieces = '{"greet":"hello"}\n'.split('').map(character => character);

    assert.deepEqual(await linesOf(pieces), [{ greet: 'hello' }]);
});

test('a last line with no newline after it is still read', async () => {
    assert.deepEqual(await linesOf(['{"a":1}']), [{ a: 1 }]);
});

test('blank lines are nothing to read', async () => {
    assert.deepEqual(await linesOf(['\n\n{"a":1}\n\n']), [{ a: 1 }]);
});

test('a line that is not JSON is passed over rather than ending the reading', async () => {
    assert.deepEqual(await linesOf(['not json\n{"a":1}\n']), [{ a: 1 }]);
});

test('the lines are read in the order they arrived', async () => {
    const lines = await linesOf(['{"n":1}\n{"n":2}\n', '{"n":3}\n']);

    assert.deepEqual(lines.map(line => line.n), [1, 2, 3]);
});

test('a body that says nothing gives nothing', async () => {
    assert.deepEqual(await linesOf([]), []);
});
