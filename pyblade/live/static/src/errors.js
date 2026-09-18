/**
 * Showing the error page over the page being worked on.
 *
 * While developing, a request that goes wrong comes back with the PyBlade error
 * page: what went wrong, where, and the code or the frames around it. Leaving
 * that in the console would be a waste of a page somebody drew, and reloading
 * to see it would lose whatever the developer had on screen. So it is shown
 * where it happened, over the page, and dismissed when it has been read.
 *
 * It goes in an iframe rather than in the page itself. The error page is a
 * whole document with a stylesheet of its own: rendered inline it would inherit
 * the styles of the page it covers and leak its own into them, and two <html>
 * documents in one is not something a browser is asked to make sense of.
 *
 * Nothing here ever runs in production, because the server sends no page.
 */

/** The one dialogue, built when something first goes wrong and kept after. */
let dialogue = null;

/** The dialogue, if there is one on the page. */
export function errorDialogue() {
    return dialogue?.isConnected ? dialogue : null;
}

/**
 * Show an error page, in the dialogue if there is one and in a new one if not.
 *
 * One dialogue for every error rather than one each: a request that fails
 * fails again on the next keystroke, and a stack of dialogues would bury the
 * page underneath them.
 */
export function showErrorPage(page) {
    // One that is no longer on the page -- after a navigation took its page
    // away -- is no use: what is wanted is one the reader can see.
    const shown = errorDialogue() || build();

    shown.querySelector('iframe').setAttribute('srcdoc', page);

    if (!shown.open) shown.showModal();

    return shown;
}

function build() {
    dialogue = document.createElement('dialog');
    dialogue.className = 'pb-error';
    dialogue.setAttribute('aria-label', 'PyBlade error');

    const frame = document.createElement('iframe');
    frame.className = 'pb-error-page';
    frame.setAttribute('title', 'What went wrong');

    // Nothing in the error page needs to do anything, and the page it covers is
    // not its to reach into
    frame.setAttribute('sandbox', '');

    const close = document.createElement('button');
    close.className = 'pb-error-close';
    close.setAttribute('type', 'button');
    close.setAttribute('aria-label', 'Close');
    close.textContent = '×';

    close.addEventListener('click', () => dialogue.close());

    // Clicking beside the error closes it, the way clicking beside a dialogue
    // usually does; clicking the error itself is for reading it
    dialogue.addEventListener('click', (event) => {
        if (event.target === dialogue) dialogue.close();
    });

    dialogue.append(close, frame);
    document.body.appendChild(dialogue);

    return dialogue;
}
