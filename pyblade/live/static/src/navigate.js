import { Idiomorph } from '../vendor/idiomorph.esm.js';
import { applyKeys, holdPersisted, morphCallbacks, restorePersisted } from './morph.js';
import { Progress } from './progress.js';
import { addPushes, pushesOf, readStacks, runScripts } from './stacks.js';

/**
 * What tells one element of a <head> from another: the file it loads, or, for
 * one written inline, the whole of it.
 */
export function headIdentity(el) {
    return el.getAttribute('src') || el.getAttribute('href') || el.outerHTML;
}

/**
 * What tells one run-once script from another, for knowing it has run.
 */
function onceIdentity(script) {
    return script.getAttribute('src') || script.textContent.trim();
}

/**
 * Whether an asset marked data-navigate-track has changed version: the same
 * file asked for with another query string, as a build writes it. Only then is
 * the page loaded whole, since running the page against assets it was not
 * built with is worse than the flash of a full load.
 */
export function trackedChanged(current, incoming) {
    const byPath = new Map(current.map((href) => {
        const url = new URL(href, window.location.href);
        return [url.origin + url.pathname, url.search];
    }));

    return incoming.some((href) => {
        const url = new URL(href, window.location.href);
        const search = byPath.get(url.origin + url.pathname);

        return search !== undefined && search !== url.search;
    });
}

/** The assets of a document marked data-navigate-track. */
function tracked(doc) {
    return [...doc.querySelectorAll('[data-navigate-track]')]
        .map(el => el.getAttribute('src') || el.getAttribute('href'))
        .filter(Boolean);
}

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
 *
 * Scripts are run as Livewire runs them on wire:navigate:
 *
 *     - every <script> in the region is run again on each page, as it would be
 *       on a page loaded whole, unless it is marked data-navigate-once and has
 *       already run;
 *     - a script, a stylesheet or a style in the new <head> that the page does
 *       not have is added, and run; one it has already is left alone;
 *     - an asset marked data-navigate-track that comes back with another query
 *       string -- a new build -- has the page loaded whole instead.
 *
 * What was pushed to a stack is kept once on a page, and that holds across a
 * navigation too: the new page's pushes are added to the stacks the page has,
 * wherever they are, and what the page held already is not run again.
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

        // What has run once already, on the page as it was first loaded
        this.ranOnce = new Set(
            [...document.querySelectorAll('script[data-navigate-once]')].map(onceIdentity),
        );
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

            // Built against other assets than the page has: loaded whole
            if (trackedChanged(tracked(document), tracked(document_))) {
                window.location.href = landed;
                return;
            }

            await this.swap(document_);

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

    async swap(incoming) {
        const target = document.querySelector(`[${this.root}]`) || document.body;
        const source = incoming.querySelector(`[${this.root}]`) || incoming.body;

        if (!source) return;

        // What was pushed to the page before this one, which is not run again
        const pushedBefore = readStacks(document.documentElement).held;

        // What was written @persist and the new page has a place for is taken
        // aside, components and all, rather than drawn again
        const held = holdPersisted(target, source);

        // The components about to be taken away give up their timers and
        // listeners first, while their elements are still there to be found.
        // What was taken aside is not among them: it carries on running.
        this.pyblade?.release(target);

        // A whole page is brought in, so nothing here belongs to anyone else;
        // pb:ignore, pb:replace and pb:key still say what to leave alone.
        applyKeys(target);

        Idiomorph.morph(target, applyKeys(source), { callbacks: morphCallbacks() });

        if (incoming.title) document.title = incoming.title;

        // Then what has to run, in the order a page loaded whole would run it:
        // the new page's pushes to the stacks around the region, what is new in
        // its <head>, and the scripts of the region itself
        const scripts = [
            ...addPushes(pushesOf(incoming)),
            ...this.mergeHead(incoming),
            ...this.scriptsToRun(target, pushedBefore),
        ];

        restorePersisted(target, held);

        await runScripts(scripts);

        this.pyblade?.scan(target);
    },

    /**
     * The scripts of the region to run again.
     *
     * Each of them, as on a page loaded whole, but for one marked
     * data-navigate-once that has run already, and for what was pushed to a
     * stack the page held before: a push is kept once on a page.
     */
    scriptsToRun(target, pushedBefore) {
        const pushed = new Map();
        readStacks(target).pushes.forEach(({ stack, key, nodes }) => {
            nodes.forEach((node) => {
                if (node.nodeType !== 1) return;

                [node, ...node.querySelectorAll('*')]
                    .filter(el => el.tagName === 'SCRIPT')
                    .forEach(script => pushed.set(script, `${stack}\0${key}`));
            });
        });

        return [...target.querySelectorAll('script')].filter((script) => {
            if (pushedBefore.has(pushed.get(script))) return false;

            if (script.hasAttribute('data-navigate-once')) {
                const identity = onceIdentity(script);
                if (this.ranOnce.has(identity)) return false;

                this.ranOnce.add(identity);
            }

            return true;
        });
    },

    /**
     * Bring in what the new page has in its <head> and this one does not.
     *
     * What is already there is left where it is: re-adding a stylesheet makes
     * the page flash, and re-adding a script runs it a second time. Stacks are
     * left out, their pushes being added by their own rules. Answers the
     * scripts added, which are yet to be run.
     */
    mergeHead(incoming) {
        const selector = 'link[rel="stylesheet"], style, script';
        const present = new Set([...document.head.querySelectorAll(selector)].map(headIdentity));

        const pushed = new Set(readStacks(incoming.head).pushes.flatMap(({ nodes }) => nodes));
        const scripts = [];

        incoming.head.querySelectorAll(selector).forEach((el) => {
            if (pushed.has(el) || present.has(headIdentity(el))) return;

            // Copied as markup, which a script is not run from: it is run with
            // the others, in order, once everything is in place
            const template = document.createElement('template');
            template.innerHTML = el.outerHTML;
            const copy = template.content.firstElementChild;

            document.head.appendChild(copy);
            present.add(headIdentity(el));

            if (copy.tagName === 'SCRIPT') scripts.push(copy);
        });

        return scripts;
    },
};
