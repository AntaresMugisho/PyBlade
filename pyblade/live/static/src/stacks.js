/**
 * The stacks of a page, what has been pushed to them, and the scripts that
 * have to be run for what is added to a page after it has loaded.
 *
 * A page is rendered with its stacks filled: each push is preceded by a comment
 * saying which it is, and each stack ends with one saying its name.
 *
 *     <!--pb:push 3f2a...--><script src="/chart.js"></script><!--pb:stack scripts-->
 *
 * An update has no layout around it, so what the component pushed comes with
 * the answer instead; a navigation brings a whole page, with stacks of its own.
 * Either way, what the page already holds is left as it is, and the rest is
 * put at the end of its stack, in the order it was pushed. A push to a stack the
 * page does not have goes nowhere, as it would have on the server.
 */

const PUSH = 'pb:push ';
const STACK = 'pb:stack ';

/** What a comment is to the stacks: a push, the end of one, or neither. */
function marker(node) {
    if (node?.nodeType !== 8) return null;

    const text = node.data.trim();
    if (text.startsWith(PUSH)) return { push: text.slice(PUSH.length) };
    if (text.startsWith(STACK)) return { stack: text.slice(STACK.length) };

    return null;
}

/**
 * The stacks of a document or of an element, as rendered.
 *
 *     ends     the comment ending each stack, by name: where a push goes
 *     held     `stack\0key` for every push it holds
 *     pushes   each push, with its stack, its key and the nodes that make it up
 */
export function readStacks(root) {
    const ends = new Map();
    const held = new Set();
    const pushes = [];

    const doc = root.ownerDocument || root;
    const walker = doc.createTreeWalker(root, NodeFilter.SHOW_COMMENT);

    // Which stack a push belongs to is the end marker that follows it
    let waiting = [];
    while (walker.nextNode()) {
        const found = marker(walker.currentNode);
        if (!found) continue;

        if (found.push !== undefined) {
            const nodes = [];
            for (let node = walker.currentNode.nextSibling; node && !marker(node); node = node.nextSibling) {
                nodes.push(node);
            }

            waiting.push({ key: found.push, nodes });
        } else {
            ends.set(found.stack, walker.currentNode);
            waiting.forEach((push) => {
                held.add(`${found.stack}\0${push.key}`);
                pushes.push({ stack: found.stack, ...push });
            });
            waiting = [];
        }
    }

    return { ends, held, pushes };
}

/** The pushes of a page brought in by navigating, as an update sends them. */
export function pushesOf(incoming) {
    return readStacks(incoming.documentElement).pushes.map(({ stack, key, nodes }) => {
        const holder = document.createElement('div');
        nodes.forEach(node => holder.append(node.cloneNode(true)));

        return { stack, key, html: holder.innerHTML };
    });
}

/**
 * The pushes the page does not hold yet, each once, in the order they came.
 *
 * `held` is the keys already on the page, and `stacks` the names of the stacks
 * it has: a push to any other has nowhere to go.
 */
export function missing(pushes, held, stacks) {
    const seen = new Set();

    return pushes.filter(({ stack, key }) => {
        const id = `${stack}\0${key}`;
        if (held.has(id) || seen.has(id) || !stacks.has(stack)) return false;

        seen.add(id);
        return true;
    });
}

/**
 * Add to the page what was pushed that it does not hold yet.
 *
 * Answers the scripts it added. They are not run yet -- a script put on the
 * page as markup never is -- so the caller runs them, with `runScripts`.
 */
export function addPushes(pushes, root = null) {
    if (!pushes?.length) return [];

    root ??= document.documentElement;
    const { ends, held } = readStacks(root);
    const scripts = [];

    missing(pushes, held, new Set(ends.keys())).forEach(({ stack, key, html }) => {
        const template = document.createElement('template');
        template.innerHTML = html;

        scripts.push(...template.content.querySelectorAll('script'));
        ends.get(stack).before(document.createComment(`${PUSH}${key}`), template.content);
    });

    return scripts;
}

/**
 * Run scripts that are on the page but were put there as markup, in order.
 *
 * Each is replaced by a copy made afresh, which the browser does run. One that
 * loads a file is waited for before the next is run, so that a script using a
 * library runs after it, as it would have on a page loaded whole.
 */
export async function runScripts(scripts) {
    for (const old of scripts) {
        if (!old.isConnected) continue;

        const script = document.createElement('script');
        [...old.attributes].forEach(({ name, value }) => script.setAttribute(name, value));
        script.textContent = old.textContent;

        const waits = script.src && !script.hasAttribute('async') && script.type !== 'module';
        const loaded = waits
            ? new Promise((resolve) => { script.onload = script.onerror = resolve; })
            : null;

        if (waits) script.async = false;
        old.replaceWith(script);

        if (loaded) await loaded;
    }
}
