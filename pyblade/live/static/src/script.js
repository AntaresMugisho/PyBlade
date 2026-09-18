/**
 * $pb, and the @script blocks it is handed to.
 *
 * $pb is a component as JavaScript sees it, what $wire is to Livewire:
 *
 *     $pb.count                 what a property holds
 *     $pb.count = 5             set it, to be sent with the next request
 *     $pb.save(1)               call an action
 *     $pb.$get('count')         the same as $pb.count
 *     $pb.$set('count', 5)      set it, and send it now
 *     $pb.$call('save', 1)      the same as $pb.save(1)
 *     $pb.$refresh()            render the component again
 *     $pb.$el, $pb.$id          its root element, its id
 *     $pb.$emit('saved', {...}) emit an event, as emit() does in pb:click
 *     $pb.$dispatch(...)        the same
 *     $pb.$on('saved', fn)      listen for an event, until the component goes
 *     $pb.$watch('count', fn)   be told when a property changes: fn(new, old)
 *
 * A name the component holds is a property; any other is an action. Every
 * call to the server answers a promise, settled once the server has answered.
 *
 * A @script block is rendered inert, in <template pb:script="key">, inside the
 * component it belongs to. It is run once each time the component comes onto
 * the page -- loaded with it, navigated to, brought in by an update, loaded
 * lazily -- and not again when the component is updated. The key says which
 * block it is, so one that appears later, inside an @if, is run when it does.
 */

const MAGIC = new Set([
    '$el', '$id', '$get', '$set', '$call', '$refresh', '$emit', '$dispatch', '$on', '$watch',
]);

/** What a property holds, as the page has it: what was set here comes first. */
function valueOf(component, name) {
    const local = component.formState?.values || {};

    return Object.prototype.hasOwnProperty.call(local, name) ? local[name] : component.getState()[name];
}

/** The $pb of a component. */
export function pbFor(component) {
    const magic = {
        $get: (name) => valueOf(component, name),

        $set: (name, value) => {
            component.setLocal(name, value);
            return component.sendRequest({ action: '$set', params: [name, value] });
        },

        $call: (name, ...params) => component.callServerMethod(name, params),

        $refresh: () => component.refresh(),

        $emit: (name, data = {}) => component.emit({ name, data }),

        $dispatch: (name, data = {}) => component.emit({ name, data }),

        // What an event carries is what the callback is given, and the listener
        // goes with the component rather than outliving it
        $on: (name, callback) => {
            const off = window.PyBlade.on(name, (event) => callback(event.detail));
            const forget = component.onDestroy(off);

            return () => { off(); forget?.(); };
        },

        $watch: (name, callback) => {
            let last = valueOf(component, name);

            return component.onStateChange(() => {
                const now = valueOf(component, name);
                if (JSON.stringify(now) === JSON.stringify(last)) return;

                const before = last;
                last = now;
                callback(now, before);
            });
        },
    };

    return new Proxy({}, {
        get(_, name) {
            if (typeof name !== 'string') return undefined;

            if (name === '$el') return component.element;
            if (name === '$id') return component.id;
            if (MAGIC.has(name)) return magic[name];

            // Not something to be awaited itself: `await $pb` is $pb
            if (name === 'then') return undefined;

            if (Object.prototype.hasOwnProperty.call(component.getState(), name)) return valueOf(component, name);

            return (...params) => component.callServerMethod(name, params);
        },

        set(_, name, value) {
            component.setLocal(name, value);
            return true;
        },

        has(_, name) {
            return MAGIC.has(name) || Object.prototype.hasOwnProperty.call(component.getState(), name);
        },
    });
}

/**
 * The @script blocks of a component not run yet, in the order they are written.
 *
 * One inside a component written in this one belongs to that one. Each is
 * marked as run as it is handed out, so that it is handed out once.
 */
export function scriptsToRun(component, blocks) {
    component._scriptsRun ??= new Set();

    return blocks.filter((block) => {
        const key = block.getAttribute('pb:script');
        if (!key || component._scriptsRun.has(key) || component.isNested(block)) return false;

        component._scriptsRun.add(key);
        return true;
    });
}

/** The JavaScript written in a block, inside its <script> tag or not. */
function sourceOf(block) {
    const script = block.content.querySelector('script');

    return script ? script.textContent : block.content.textContent;
}

let counter = 0;

/**
 * Run a component's @script blocks that have not run yet.
 *
 * Each is run as a script the page adds -- so that the same rules apply to it as
 * to any other inline script, a Content Security Policy included -- wrapped in
 * an async function handed $pb. An error in one is reported and does not stop
 * the others.
 */
export function runComponentScripts(component) {
    if (typeof component.element?.querySelectorAll !== 'function') return;

    const blocks = [...component.element.querySelectorAll('template[pb\\:script]')];

    scriptsToRun(component, blocks).forEach((block) => {
        const name = `__pbScript${++counter}`;
        const holder = (window.PyBlade.scripts ??= {});

        const script = document.createElement('script');
        const nonce = document.querySelector('script[nonce]')?.nonce;
        if (nonce) script.nonce = nonce;

        script.textContent = `window.PyBlade.scripts.${name} = async function ($pb) {\n${sourceOf(block)}\n};`;
        document.head.appendChild(script);
        script.remove();

        const run = holder[name];
        delete holder[name];

        if (typeof run !== 'function') return;

        run.call(component.element, component.$pb).catch((error) => {
            console.error(`PyBlade: a @script of ${component.id} failed.`, error);
        });
    });
}
