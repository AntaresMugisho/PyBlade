/**
 * What is written after the name of a directive.
 *
 * A directive is written pb:name.one.two, and the segments after the name say
 * how it is to behave. Some are flags -- pb:model.live -- and some take the
 * segment that follows them as an argument -- pb:model.debounce.500ms. Reading
 * one is the same wherever it is written, so it is read here rather than in
 * every handler that happens to need it.
 */

/**
 * A duration written as a modifier, in milliseconds.
 *
 * Written as '500ms', as '2s', or as a bare number, which is milliseconds:
 * that is what the durations in the templates say and what timers take.
 */
function toMilliseconds(value, fallback = null) {
    if (typeof value !== 'string') return fallback;

    const match = /^(\d+(?:\.\d+)?)(ms|s)?$/.exec(value);
    if (!match) return fallback;

    const amount = parseFloat(match[1]);

    return Math.round(match[2] === 's' ? amount * 1000 : amount);
}

export class Modifiers {
    /** The modifiers of an attribute, read from its name: 'pb:model.live' -> ['live']. */
    static from(attributeName) {
        const [, ...list] = attributeName.replace(/^pb:/, '').split('.');

        return new Modifiers(list);
    }

    constructor(list = []) {
        this.list = list;
    }

    /** Whether a modifier is written at all, which is what a flag asks. */
    has(name) {
        return this.list.includes(name);
    }

    /** What a modifier was given, which is the segment written after it. */
    get(name, fallback = null) {
        const index = this.list.indexOf(name);
        if (index === -1) return fallback;

        const argument = this.list[index + 1];

        return argument === undefined ? fallback : argument;
    }

    /** What a modifier was given, read as a duration in milliseconds. */
    duration(name, fallback = null) {
        return toMilliseconds(this.get(name), fallback);
    }

    /**
     * A duration written on its own rather than after a name, as pb:poll.15s is.
     */
    timing(fallback = null) {
        for (const segment of this.list) {
            const milliseconds = toMilliseconds(segment);
            if (milliseconds !== null) return milliseconds;
        }

        return fallback;
    }

    /** The first modifier, which is all a directive taking one ever reads. */
    get first() {
        return this.list.length ? this.list[0] : null;
    }
}
