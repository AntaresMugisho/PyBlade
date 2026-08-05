import { Idiomorph } from '../vendor/idiomorph.esm.js';
import { Progress } from './progress.js';

/**
 * Moving from page to page without loading one.
 *
 * A link marked pb:navigate is followed by fetching the page it points at and
 * putting it in place of the one that is there, which leaves everything around
 * it alone: the components living outside the region that changes keep running,
 * with their state, their timers and their scroll position.
 *
 * The region is the element marked pb:root. A page that marks none is replaced
 * whole, through its body, so navigation works before a layout is marked up.
 */
export const Navigation = {
    root: 'pb\\:root',

    /**
     * Whether a click is one we are meant to answer.
     *
     * Anything the browser would do something else with is left to it: another
     * tab, another origin, a download, a right click.
     */
    intercepts(event, link) {
        if (!link || event.defaultPrevented) return false;
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;

        const href = link.getAttribute('href');
        if (!href || href.startsWith('#')) return false;
        if (link.hasAttribute('download') || (link.target && link.target !== '_self')) return false;

        const url = new URL(href, window.location.href);
        if (url.origin !== window.location.origin) return false;

        // A link to the very place we are, but for the fragment, is the page's own
        return url.pathname !== window.location.pathname || url.search !== window.location.search;
    },

    start(pyblade) {
        this.pyblade = pyblade;

        // Listened for on the document rather than bound to each link: a link
        // brought in by a navigation is answered without anything being bound
        // again, and no link is ever bound twice.
        document.addEventListener('click', (event) => {
            const link = event.target.closest?.('[pb\\:navigate]');
            if (!this.intercepts(event, link)) return;

            event.preventDefault();
            this.visit(link.getAttribute('href'));
        });

        window.addEventListener('popstate', (event) => {
            if (!event.state?.pyblade) return;
            this.visit(window.location.href, { push: false });
        });

        history.replaceState({ pyblade: true }, '', window.location.href);
    },

    async visit(href, { push = true } = {}) {
        const url = new URL(href, window.location.href);

        window.dispatchEvent(new CustomEvent('pb:navigating', { detail: { href: url.href } }));
        Progress.start();

        try {
            const response = await fetch(url.href, {
                headers: { 'X-PyBlade-Navigate': 'true' },
                credentials: 'same-origin',
            });

            // A redirect the server followed is the page we end up on
            const landed = response.redirected ? response.url : url.href;
            const document_ = new DOMParser().parseFromString(await response.text(), 'text/html');

            this.swap(document_);

            if (push) {
                history.pushState({ pyblade: true }, '', landed);
                window.scrollTo(0, 0);
            }

            window.dispatchEvent(new CustomEvent('pb:navigated', { detail: { href: landed } }));
        } catch (error) {
            // A page we cannot fetch is one the browser should try itself,
            // rather than leaving the reader on a page that did not change
            window.location.href = url.href;
        } finally {
            Progress.done();
        }
    },

    swap(incoming) {
        const target = document.querySelector(`[${this.root}]`) || document.body;
        const source = incoming.querySelector(`[${this.root}]`) || incoming.body;

        if (!source) return;

        // The components about to be taken away give up their timers and
        // listeners first, while their elements are still there to be found
        this.pyblade?.release(target);

        Idiomorph.morph(target, source.outerHTML);

        this.carrySnapshots(incoming);

        if (incoming.title) document.title = incoming.title;
        this.mergeHead(incoming);

        this.pyblade?.scan(target);
    },

    /**
     * Bring across the snapshots the components of the new page boot from.
     *
     * They sit in the body of the page they came with, which is not always
     * inside the region being replaced: a component that is a page has its
     * snapshot written at the end of the document, well outside pb:root. A
     * component booted without one has no state to send back, and the server
     * turns away the first action it asks for.
     */
    carrySnapshots(incoming) {
        incoming.querySelectorAll('script[pb\\:snapshot]').forEach((script) => {
            const id = script.getAttribute('pb:snapshot');
            if (document.querySelector(`script[pb\\:snapshot="${CSS.escape(id)}"]`)) return;

            document.body.appendChild(document.importNode(script, true));
        });
    },

    /**
     * Bring in the stylesheets and scripts the new page asks for.
     *
     * What is already there is left where it is: re-adding a stylesheet makes
     * the page flash, and re-adding a script runs it a second time.
     */
    mergeHead(incoming) {
        const identity = (el) => el.getAttribute('href') || el.getAttribute('src');
        const present = new Set(
            [...document.head.querySelectorAll('link[rel="stylesheet"], script[src]')].map(identity),
        );

        incoming.head.querySelectorAll('link[rel="stylesheet"], script[src]').forEach((el) => {
            if (present.has(identity(el))) return;

            const copy = document.createElement(el.tagName);
            for (const { name, value } of el.attributes) copy.setAttribute(name, value);
            document.head.appendChild(copy);
        });
    },
};
