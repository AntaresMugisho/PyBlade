/**
 * Asking the reader before an action runs.
 *
 * The browser has confirm(), and it stops everything: no timer runs, no request
 * comes back, nothing is painted, until it is answered. So the question is put
 * in a <dialog> instead, which asks the same thing without stopping the page,
 * and which a project can replace with markup of its own.
 *
 * A project replaces it by putting an element marked pb-confirm-dialogue in the
 * page -- in its layout, say -- built from the stub that ships with PyBlade.
 * Whatever inside it is marked pb-confirm-message, pb-confirm-accept,
 * pb-confirm-cancel and pb-confirm-prompt is what is used. Failing that, the
 * plain one below is built and styled from pyblade.css.
 */

const DEFAULT_MESSAGE = 'Are you sure?';
const DEFAULT_PROMPT = 'CONFIRM';

/**
 * What an element asks before its action runs, or null if it asks nothing.
 *
 *     pb:confirm="Delete this post?"
 *     pb:confirm.prompt="Type DELETE to confirm|DELETE"
 *
 * The word the reader must type is written after the message, so that both are
 * one attribute rather than two that could disagree.
 */
export function confirmationOf(el) {
    if (el?.nodeType !== 1 || !el.attributes) return null;

    const attribute = [...el.attributes].find(
        ({ name }) => name === 'pb:confirm' || name.startsWith('pb:confirm.'),
    );

    if (!attribute) return null;

    const prompted = attribute.name.split('.').includes('prompt');
    const [message, word] = (attribute.value || '').split('|');

    return {
        message: message.trim() || DEFAULT_MESSAGE,
        prompt: prompted ? (word || '').trim() || DEFAULT_PROMPT : null,
    };
}

/** The dialogue the page provides, if it provides one. */
function provided() {
    return document.querySelector('[pb-confirm-dialogue]');
}

/** The plain dialogue, built once and kept for every question after the first. */
let fallback = null;

function plainDialogue() {
    if (fallback?.isConnected) return fallback;

    fallback = document.createElement('dialog');
    fallback.className = 'pb-confirm';
    fallback.innerHTML = `
        <form method="dialog" class="pb-confirm-body">
            <p pb-confirm-message class="pb-confirm-message"></p>
            <input pb-confirm-prompt class="pb-confirm-prompt" hidden>
            <div class="pb-confirm-actions">
                <button value="cancel" pb-confirm-cancel class="pb-confirm-cancel">Cancel</button>
                <button value="accept" pb-confirm-accept class="pb-confirm-accept">Confirm</button>
            </div>
        </form>
    `;

    document.body.appendChild(fallback);

    return fallback;
}

/**
 * Ask the question, and answer whether it was accepted.
 *
 * Nothing here waits on the reader: the promise is settled when the dialogue
 * closes, which is when they answer it, press Escape, or click the backdrop.
 */
export function ask({ message, prompt }) {
    const dialogue = provided() || plainDialogue();

    if (typeof dialogue.showModal !== 'function') {
        // A browser without <dialog>: better to ask the old way than not at all
        return Promise.resolve(window.confirm(message));
    }

    const form = dialogue.querySelector('form') || dialogue;
    const say = dialogue.querySelector('[pb-confirm-message]');
    const field = dialogue.querySelector('[pb-confirm-prompt]');
    const accept = dialogue.querySelector('[pb-confirm-accept]');

    if (say) say.textContent = message;

    if (field) {
        field.hidden = prompt === null;
        field.value = '';
        field.placeholder = prompt || '';
    }

    // A word to type is a word to get right: until it is, there is nothing to
    // accept, so the button that would is not one to press
    const watch = () => {
        if (accept) accept.disabled = prompt !== null && field?.value.trim() !== prompt;
    };

    const typed = () => prompt === null || field?.value.trim() === prompt;

    watch();
    field?.addEventListener('input', watch);
    dialogue.returnValue = '';

    return new Promise((resolve) => {
        let settled = false;

        const done = (accepted) => {
            if (settled) return;
            settled = true;

            form.removeEventListener('submit', onSubmit);
            dialogue.removeEventListener('close', onClose);
            dialogue.removeEventListener('cancel', onCancel);
            dialogue.removeEventListener('click', onClickOutside);
            field?.removeEventListener('input', watch);

            if (dialogue.open) dialogue.close();
            dialogue.returnValue = '';

            resolve(accepted);
        };

        // Which of these arrives is the browser's business: a dialogue closed
        // by its own form does not always say so with a close event, so the
        // answer is taken from whichever comes first.
        function onSubmit(event) {
            done((event.submitter?.value ?? dialogue.returnValue) === 'accept' && typed());
        }

        function onClose() {
            done(dialogue.returnValue === 'accept' && typed());
        }

        function onCancel() {
            done(false);
        }

        // Clicking beside the dialogue rather than in it: a <dialog> fills the
        // window, so a click landing on the element itself landed on the backdrop
        function onClickOutside(event) {
            if (event.target === dialogue) done(false);
        }

        form.addEventListener('submit', onSubmit);
        dialogue.addEventListener('close', onClose);
        dialogue.addEventListener('cancel', onCancel);
        dialogue.addEventListener('click', onClickOutside);

        dialogue.showModal();
        (prompt !== null && field ? field : accept)?.focus();
    });
}
