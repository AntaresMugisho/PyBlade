/**
 * Asking for a component that was not built with the page.
 *
 * A component written @lazy does none of its work while the page is being
 * built: what arrives is a skeleton of it, carrying pb:lazy. The real thing is
 * asked for here -- as soon as the page has loaded, or, where the marker says
 * visible, once the skeleton has been scrolled to, which is what keeps a long
 * page from asking for everything below the fold at once.
 *
 * What comes back is an ordinary answer: new markup and a new state, morphed
 * into place like any other. There is nothing to undo afterwards, because what
 * the server sends has no marker on it.
 */

/** Whether the marker says to wait until the component has been scrolled to. */
function waitsToBeSeen(marker) {
    return marker.trim().toLowerCase() === 'visible';
}

/**
 * Ask for the component behind a skeleton, when it is time to.
 *
 * The marker is taken off the element first, so that a second scan of the page
 * -- after a navigation, or after markup was morphed in -- does not ask for the
 * same component twice.
 */
export function loadWhenReady(component, el) {
    const marker = el.getAttribute('pb:lazy');
    if (marker === null) return;

    el.removeAttribute('pb:lazy');

    const ask = () => component.callServerMethod('$lazy', []);

    if (!waitsToBeSeen(marker)) return ask();

    // A browser that cannot watch for it asks now rather than never: a
    // component nobody ever asks for is worse than one asked for early.
    if (typeof IntersectionObserver !== 'function') return ask();

    const observer = new IntersectionObserver((entries) => {
        if (!entries.some(entry => entry.isIntersecting)) return;

        observer.disconnect();
        ask();
    });

    observer.observe(el);
}
