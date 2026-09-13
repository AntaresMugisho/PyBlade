/**
 * An element coming and going, rather than blinking in and out.
 *
 * New markup is put over the old on every update, so an element the server has
 * stopped rendering is simply gone from one frame to the next, and one it has
 * started rendering is simply there. pb:transition says to animate the two.
 *
 * Leaving is the awkward half: an element on its way out has to stay on the
 * page until it has finished going, which is why the removal is held back here
 * and done afterwards rather than left to morphing.
 */

import { Modifiers } from './modifiers.js';

const DEFAULT_DURATION = 150;

/** How much less a page nobody is looking at polls: 95% less of it. */
const BACKGROUND_FACTOR = 20;

/**
 * What an element asks for when it comes and goes, or null if it asks nothing.
 *
 *     pb:transition
 *     pb:transition.duration.400ms
 *     pb:transition.out.opacity
 *     pb:transition.scale.origin.top
 */
export function transitionOf(el) {
    if (el?.nodeType !== 1 || !el.attributes) return null;

    const attribute = [...el.attributes].find(
        ({ name }) => name === 'pb:transition' || name.startsWith('pb:transition.'),
    );

    if (!attribute) return null;

    const modifiers = Modifiers.from(attribute.name);

    // Naming one of them asks for that one alone; naming neither asks for both
    const named = modifiers.has('opacity') || modifiers.has('scale');

    // Likewise for the direction: .in is about coming, .out about going, and
    // saying neither is about both
    const directed = modifiers.has('in') || modifiers.has('out');

    return {
        duration: modifiers.duration('duration', DEFAULT_DURATION),
        delay: modifiers.duration('delay', 0),
        opacity: named ? modifiers.has('opacity') : true,
        scale: named ? modifiers.has('scale') : true,
        origin: modifiers.get('origin', 'center'),
        entering: directed ? modifiers.has('in') : true,
        leaving: directed ? modifiers.has('out') : true,
    };
}

/** How often to poll, given whether anyone is looking at the page. */
export function pollRate(interval, { hidden = false, keepAlive = false } = {}) {
    return hidden && !keepAlive ? interval * BACKGROUND_FACTOR : interval;
}

/**
 * Whether the page is one nobody is looking at.
 *
 * Asked of the document, where there is one: what runs this outside a browser
 * is a test, and a page nobody can see is not a page in the background.
 */
export function pageHidden() {
    return typeof document !== 'undefined' && document.hidden === true;
}

/** Say when that changes, for as long as the binding lasts. */
export function onPageVisibility(handler, signal) {
    if (typeof document === 'undefined') return;

    document.addEventListener('visibilitychange', handler, { signal });
}

/** The look of an element that is not there yet, or no longer there. */
function hiddenStyle(spec) {
    const transform = spec.scale ? 'scale(0.95)' : '';

    return { opacity: spec.opacity ? '0' : '', transform };
}

/** The look of an element that is there. */
function shownStyle(spec) {
    return { opacity: spec.opacity ? '1' : '', transform: spec.scale ? 'scale(1)' : '' };
}

function apply(el, style) {
    Object.entries(style).forEach(([name, value]) => { el.style[name] = value; });
}

/** What the browser is told to animate, and for how long. */
function arm(el, spec) {
    const properties = [spec.opacity && 'opacity', spec.scale && 'transform'].filter(Boolean);

    el.style.transitionProperty = properties.join(', ') || 'opacity';
    el.style.transitionDuration = `${spec.duration}ms`;
    el.style.transitionDelay = `${spec.delay}ms`;
    el.style.transitionTimingFunction = 'ease';
    el.style.transformOrigin = spec.origin;
}

/** Put back what was borrowed from the element to animate it. */
function disarm(el) {
    ['transitionProperty', 'transitionDuration', 'transitionDelay', 'transitionTimingFunction',
        'transformOrigin', 'opacity', 'transform'].forEach((name) => { el.style[name] = ''; });
}

/**
 * Bring an element in.
 *
 * It is on the page already -- morphing put it there -- so it is taken back to
 * where it would have come from and let go of on the next frame, which is what
 * gives the browser something to animate between.
 */
export function enter(el, spec = transitionOf(el)) {
    if (!spec || !spec.entering) return;

    apply(el, hiddenStyle(spec));

    requestAnimationFrame(() => {
        arm(el, spec);

        requestAnimationFrame(() => {
            apply(el, shownStyle(spec));

            setTimeout(() => disarm(el), spec.duration + spec.delay + 20);
        });
    });
}

/**
 * See an element out, and do something with it once it has gone.
 *
 * What that is differs: an element the markup no longer holds is removed, while
 * one pb:show is hiding stays where it is, so the two say so themselves.
 */
export function animateOut(el, spec, done) {
    arm(el, spec);

    requestAnimationFrame(() => apply(el, hiddenStyle(spec)));

    setTimeout(() => {
        done();
        disarm(el);
    }, spec.duration + spec.delay + 20);
}

/**
 * See an element out, and remove it once it has gone.
 *
 * Answers whether it took the element on: morphing removes the ones it does not.
 */
export function leave(el, spec = transitionOf(el)) {
    if (!spec || !spec.leaving) return false;

    // An element already on its way out is left to finish rather than started over
    if (el.dataset?.pbLeaving) return true;
    if (el.dataset) el.dataset.pbLeaving = 'true';

    animateOut(el, spec, () => el.remove());

    return true;
}
