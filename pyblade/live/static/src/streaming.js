/**
 * Reading an answer that arrives in pieces.
 *
 * An action written @streamed answers a line of JSON at a time: what it streams
 * while it runs, and then the answer itself. The pieces the network hands over
 * have nothing to do with those lines -- one may hold several of them, or half
 * of one -- so they are put back together here before anything is read.
 */

/**
 * Read a response body line by line, handing each one over as it is whole.
 *
 * A line that is not JSON is passed over: one line the server could not write
 * properly is no reason to stop reading the ones after it.
 */
export async function readLines(stream, onLine) {
    const reader = stream.getReader();
    const decoder = new TextDecoder();

    let held = '';

    const take = (text) => {
        const line = text.trim();
        if (!line) return;

        try {
            onLine(JSON.parse(line));
        } catch {
            // Not something to read; the lines around it still are
        }
    };

    for (;;) {
        const { done, value } = await reader.read();

        if (done) break;

        held += decoder.decode(value, { stream: true });

        const lines = held.split('\n');

        // Whatever follows the last newline is the start of a line that has not
        // all arrived, and waits here for the rest of it
        held = lines.pop();

        lines.forEach(take);
    }

    take(held);
}
