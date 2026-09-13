/**
 * The little a directive asks about the state of a component.
 *
 * pb:show says when an element is on the page, in terms of what the component
 * holds: a property, its opposite, or a comparison against something written in
 * the template. That is the whole of it. The work belongs in Python, and a
 * template is no place to start writing another language -- so what is not
 * understood here is not guessed at either.
 *
 * Nothing is evaluated as code: a page that forbids it, as a page with a strict
 * content policy does, is a page PyBlade still works on.
 */

/** What a piece of an expression could not be read as. */
const UNREADABLE = Symbol('unreadable');

const PATH = /^[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*$/;

/** A value written in the template rather than read from the component. */
function literalOf(text) {
    if (/^-?\d+(?:\.\d+)?$/.test(text)) return Number(text);

    if (/^(['"]).*\1$/.test(text)) return text.slice(1, -1);

    if (text === 'true' || text === 'True') return true;
    if (text === 'false' || text === 'False') return false;
    if (text === 'null' || text === 'None') return null;

    return UNREADABLE;
}

/** What the component holds under a dotted path. */
function walk(path, state) {
    return path.split('.').reduce(
        (value, part) => (value === null || value === undefined ? undefined : value[part]),
        state,
    );
}

/** One side of a comparison: something written, or something held. */
function valueOf(text, state) {
    const literal = literalOf(text);
    if (literal !== UNREADABLE) return literal;

    return PATH.test(text) ? walk(text, state) : UNREADABLE;
}

function compare(left, operator, right) {
    switch (operator) {
        case '===': return left === right;
        case '!==': return left !== right;
        case '==':
        case '=': return left == right; // eslint-disable-line eqeqeq
        case '!=': return left != right; // eslint-disable-line eqeqeq
        case '>': return left > right;
        case '>=': return left >= right;
        case '<': return left < right;
        case '<=': return left <= right;
        default: return UNREADABLE;
    }
}

/**
 * Whether the condition an element was written with holds.
 *
 *     pb:show="visible"
 *     pb:show="!archived"
 *     pb:show="count > 3"
 *     pb:show="status == 'done'"
 *
 * A condition this cannot read leaves the element on the page: a page missing
 * what it was meant to show is worse than one showing more than it meant to.
 */
export function readCondition(expression, state = {}) {
    const text = (expression || '').trim();
    if (!text) return false;

    if (text.startsWith('!')) return !readCondition(text.slice(1), state);

    const comparison = /^(.+?)\s*(===|!==|==|!=|>=|<=|=|>|<)\s*(.+)$/.exec(text);

    if (comparison) {
        const [, left, operator, right] = comparison;
        const a = valueOf(left.trim(), state);
        const b = valueOf(right.trim(), state);

        if (a === UNREADABLE || b === UNREADABLE) return true;

        const answer = compare(a, operator, b);

        return answer === UNREADABLE ? true : answer;
    }

    return PATH.test(text) ? !!truthy(walk(text, state)) : true;
}

/** What a template means by a value being there: an empty list is not. */
function truthy(value) {
    return Array.isArray(value) ? value.length > 0 : !!value;
}
