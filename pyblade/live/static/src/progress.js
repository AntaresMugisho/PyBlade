/**
 * The bar that runs across the top of the page while it is being navigated to.
 *
 * A page takes as long as it takes, which is not known when the bar starts, so
 * it creeps towards the end without ever arriving and is sent the rest of the
 * way once the page is there. Everything it looks like is left to the style
 * sheet, which reads the custom properties documented in pyblade.css.
 */
export const Progress = {
    element: null,
    timer: null,
    depth: 0,

    // Below this, a page arrives fast enough that a bar would only flicker
    delay: 150,

    start() {
        this.depth += 1;
        if (this.depth > 1 || this.timer) return;

        this.timer = setTimeout(() => {
            this.timer = null;
            this.show();
        }, this.delay);
    },

    done() {
        this.depth = Math.max(0, this.depth - 1);
        if (this.depth > 0) return;

        if (this.timer) {
            clearTimeout(this.timer);
            this.timer = null;
            return;
        }

        this.finish();
    },

    show() {
        if (this.element || typeof document === 'undefined') return;

        this.element = document.createElement('div');
        this.element.className = 'pb-progress';
        this.element.setAttribute('role', 'progressbar');
        this.element.setAttribute('aria-hidden', 'true');
        document.body.appendChild(this.element);

        // Reading a layout property settles the style the element was added
        // with, so the transition has a starting point to run from rather than
        // being applied at once. Waiting for a frame would read better and is
        // what this used to do, but a tab that is not being painted is not
        // given frames, and the bar would sit at nought until it was.
        void this.element.offsetWidth;

        this.element.classList.add('pb-progress-running');
    },

    finish() {
        const element = this.element;
        if (!element) return;

        this.element = null;
        element.classList.add('pb-progress-done');

        const remove = () => element.remove();
        element.addEventListener('transitionend', remove, { once: true });

        // A bar that never transitions, because the page hid it or the user
        // asked for no motion, would otherwise stay where it is
        setTimeout(remove, 1000);
    },
};
