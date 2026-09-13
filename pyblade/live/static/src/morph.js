/**
 * What morphing is told to leave alone, replace outright, or match up.
 *
 * New markup is put over the old rather than in place of it, so that what the
 * browser holds and nothing else knows -- the caret, a selection, a video part
 * way through, whatever a script outside PyBlade has done -- survives an update.
 * Three directives say where that is not what is wanted:
 *
 *     pb:ignore         leave this element as it is
 *     pb:ignore.attrs   leave its attributes, its content may change
 *     pb:stream         its content comes from an action, not from the markup
 *     pb:replace        put the new content in place of the old
 *     pb:replace.self   put the new element in place of the old one
 *     pb:key="..."      this element is that one, wherever it has moved to
 *
 * They are read here rather than in the directive handlers: morphing happens
 * against elements that may have no component of their own yet, and the same
 * reading serves an update and a whole page brought in by navigating.
 */

import { enter, leave } from './transition.js';

/**
 * The modifiers a directive is written with on an element, or null for one that
 * is not written on it at all. A directive written bare gives an empty list,
 * which is not the same as its absence.
 */
function marked(el, name) {
    if (el?.nodeType !== 1 || !el.attributes) return null;

    for (const attribute of el.attributes) {
        if (attribute.name === `pb:${name}` || attribute.name.startsWith(`pb:${name}.`)) {
            return attribute.name.slice(`pb:${name}`.length).split('.').filter(Boolean);
        }
    }

    return null;
}

/** Whether an element is left exactly as it is, content and all. */
export function ignoresContent(el) {
    const modifiers = marked(el, 'ignore');

    // pb:ignore.attrs is about the attributes alone: what is inside the element
    // is still brought up to date
    if (modifiers !== null && !modifiers.includes('attrs')) return true;

    // What an action streamed into an element is what that element is for. The
    // server renders it empty -- it is the stream that fills it -- so morphing
    // it would wipe out what has just been read.
    return marked(el, 'stream') !== null;
}

/** Whether the attributes of an element are left as they are. */
export function ignoresAttributes(el) {
    return marked(el, 'ignore')?.includes('attrs') === true;
}

/** How an element asks to be replaced outright, or null if it does not. */
export function replacement(el) {
    const modifiers = marked(el, 'replace');
    if (modifiers === null) return null;

    return modifiers.includes('self') ? 'self' : 'children';
}

/**
 * Give a keyed element an id, which is what morphing tells elements apart by.
 *
 * A list rendered again is paired up by what its elements look like, so a row
 * inserted at the top can leave every row below it paired with its neighbour.
 * pb:key says which row is which; it becomes an id, an element that has one of
 * its own being left with it, since that is already what the pairing reads.
 */
export function applyKeys(root) {
    if (root?.querySelectorAll === undefined) return root;

    const keyed = [root, ...root.querySelectorAll('*')].filter(el => el.nodeType === 1 && el.hasAttribute?.('pb:key'));

    keyed.forEach((el) => {
        if (el.getAttribute('id')) return;

        el.setAttribute('id', `pb-key-${el.getAttribute('pb:key')}`);
    });

    return root;
}

/**
 * The callbacks morphing is driven with.
 *
 * `isOwn` says which elements belong to whoever is doing the morphing: a
 * component leaves the ones that belong to another alone, and a navigation,
 * which owns the whole page, leaves none.
 */
export function morphCallbacks({ isOwn = () => true } = {}) {
    return {
        beforeNodeMorphed(oldNode, newNode) {
            if (oldNode?.nodeType !== 1) return true;

            // Another component answers for itself, and for everything in it
            if (!isOwn(oldNode)) return false;

            if (ignoresContent(oldNode)) return false;

            const replace = replacement(oldNode);
            if (replace !== null) {
                if (replace === 'self') oldNode.replaceWith(newNode.cloneNode(true));
                else oldNode.replaceChildren(...newNode.cloneNode(true).childNodes);

                return false;
            }

            return true;
        },

        beforeAttributeUpdated(attributeName, element) {
            return !ignoresAttributes(element);
        },

        // An element the new markup brings with it is animated in, if it asks
        // to be. It is on the page by the time this runs, which is what makes
        // there be something to animate from.
        afterNodeAdded(node) {
            enter(node);
        },

        // And one the new markup no longer holds is animated out. Saying no
        // here leaves it on the page; it is removed when it has finished going.
        beforeNodeRemoved(node) {
            return !leave(node);
        },
    };
}
