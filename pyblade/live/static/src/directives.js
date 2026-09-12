import { Modifiers } from './modifiers.js';
import { fieldValue, writeField } from './fields.js';
import { ask, confirmationOf } from './confirm.js';
import { readCondition } from './expressions.js';
import { animateOut, enter, onPageVisibility, pageHidden, pollRate, transitionOf } from './transition.js';

export const Directives = {
    // Parse expression with arguments: "method('arg1', 'arg2')" or "method(key='val', key2='val2')"
    parseExpression(expression) {
        if (!expression) return { methodName: '', args: [] };

        // Match method name and arguments
        const match = expression.match(/^(\w+)\s*(?:\((.*)\))?$/);
        if (!match) return { methodName: expression, args: [] };

        const [, methodName, argsStr] = match;
        if (!argsStr) return { methodName, args: [] };

        const args = [];
        let current = '';
        let inString = false;
        let stringChar = '';
        let inKeyword = false;
        let keywordName = '';

        for (let i = 0; i < argsStr.length; i++) {
            const char = argsStr[i];

            if (!inString && (char === '"' || char === "'")) {
                inString = true;
                stringChar = char;
                current += char;
            } else if (inString && char === stringChar) {
                inString = false;
                current += char;
            } else if (!inString && char === '=' && !inKeyword) {
                inKeyword = true;
                keywordName = current.trim();
                current = '';
            } else if (!inString && char === ',') {
                // A comma ends an argument, keyword or not: one written after
                // another used to be swallowed by the value of the first.
                if (current.trim()) {
                    args.push(inKeyword
                        ? { [keywordName]: this.parseValue(current.trim()) }
                        : this.parseValue(current.trim()));
                }
                current = '';
                inKeyword = false;
                keywordName = '';
            } else if (!inString && char === ' ' && !inKeyword) {
                // Skip spaces outside strings and keywords
                continue;
            } else {
                current += char;
            }
        }

        // Add last argument
        if (current.trim()) {
            if (inKeyword) {
                args.push({ [keywordName]: this.parseValue(current.trim()) });
            } else {
                args.push(this.parseValue(current.trim()));
            }
        }

        return { methodName, args };
    },

    // Parse a single value (string, number, boolean, etc.)
    parseValue(value) {
        // Remove quotes from strings
        if ((value.startsWith('"') && value.endsWith('"')) || 
            (value.startsWith("'") && value.endsWith("'"))) {
            return value.slice(1, -1);
        }
        
        // Parse numbers
        if (!isNaN(value)) {
            return Number(value);
        }
        
        // Parse booleans
        if (value === 'true') return true;
        if (value === 'false') return false;
        if (value === 'null') return null;
        
        // Return as string for other cases
        return value;
    },

    // Registry of built-in and custom directives
    /**
     * Read an expression that emits an event rather than calling the server.
     *
     *     emit('show-post-modal', id=3)
     *     dispatch('saved').to('PostList')
     *     emit('saved').self()
     *
     * Returns the event to emit, or null when the expression is an ordinary
     * action, which is what most of them are.
     */
    parseEmit(expression) {
        const opening = /^\s*(?:emit|dispatch)\s*\(/.exec(expression || '');
        if (!opening) return null;

        // Walk to the parenthesis that closes the call, so that one written
        // inside a string or a nested call does not end it early
        let depth = 0;
        let inString = false;
        let quote = '';
        let i = opening[0].length - 1;

        for (; i < expression.length; i++) {
            const char = expression[i];

            if (inString) {
                if (char === quote) inString = false;
            } else if (char === '"' || char === "'") {
                inString = true;
                quote = char;
            } else if (char === '(') {
                depth++;
            } else if (char === ')') {
                depth--;
                if (depth === 0) break;
            }
        }

        if (depth !== 0) return null;

        const { args } = this.parseExpression(`emit(${expression.slice(opening[0].length, i)})`);
        const [name, ...rest] = args;

        if (typeof name !== 'string' || !name) return null;

        // Anything written as key=value is data the event carries
        const data = Object.assign({}, ...rest.filter(arg => arg && typeof arg === 'object'));
        const event = { name, data };

        // What follows the call says who the event is for
        const modifiers = expression.slice(i + 1);
        const modifier = /\.\s*(?:to\s*\(\s*['"]([^'"]*)['"]\s*\)|self\s*\(\s*\))/g;
        let match;

        while ((match = modifier.exec(modifiers)) !== null) {
            if (match[1] === undefined) event.self = true;
            else event.to = match[1];
        }

        return event;
    },

    /**
     * Whether what a request is doing is what an element was told to watch.
     *
     * An element says so with pb:target, naming the actions or the properties
     * it is about. Told nothing, it is about whatever the component is doing,
     * which is what an element with no target of its own has always been.
     *
     *     <span pb:loading pb:target="save">          the save action
     *     <span pb:loading pb:target="name, email">   either property
     */
    matchesTarget(el, payload) {
        const names = this.targetsOf(el);
        if (!names.length) return true;

        return names.some(name => this.requestIsAbout(payload, name));
    },

    /**
     * What a field was read as, once .number or .boolean has had its say.
     *
     * A form only ever gives text, so a property that is a number or a flag is
     * one the field has to be told to read as such. What a checkbox or a
     * multiple select already answers is left alone: it was never text.
     */
    castValue(value, { number = false, boolean = false } = {}) {
        if (typeof value !== 'string') return value;

        if (number) {
            if (value === '') return '';

            const parsed = parseFloat(value);

            // A field holding something that is not a number keeps what was
            // typed, rather than becoming a NaN nothing can be done with
            return Number.isNaN(parsed) ? value : parsed;
        }

        if (boolean) return ['true', '1', 'on', 'yes'].includes(value.toLowerCase());

        return value;
    },

    /** The actions or properties an element says it is about, if it says any. */
    targetsOf(el) {
        const target = el.getAttribute?.('pb:target');
        if (!target) return [];

        return target.split(',').map(name => name.trim()).filter(Boolean);
    },

    /** Whether a request is about the action, the event or the property named. */
    requestIsAbout(payload, name) {
        const { action, params = [] } = payload || {};

        // A property being set, and an event being handled, both name what they
        // are about in the first of the parameters rather than in the action
        if (action === '$set' || action === '$event') return params[0] === name;

        return action === name;
    },

    /**
     * Run what a directive was given: an event to emit, or an action to call.
     *
     * An element written pb:confirm is asked about first, and nothing runs
     * unless it is answered. The asking is done here rather than by a listener
     * of its own: a listener beside pb:click cannot stop it -- both are on the
     * same element, and stopping an event from travelling any further does not
     * stop what is already listening where it is.
     */
    async invoke(expression, component, el = null, asking = ask) {
        const confirmation = confirmationOf(el);

        if (confirmation) {
            const accepted = await asking(confirmation);
            if (!accepted) return undefined;
        }

        const event = this.parseEmit(expression);

        if (event) return component.emit(event);

        const { methodName, args } = this.parseExpression(expression);

        // The server is told the reader was asked, for an action that says it
        // must be: @confirm refuses one that arrives without it
        return component.callServerMethod(methodName, args, confirmation ? { confirmed: true } : undefined);
    },

    handlers: {
        click({ el, expression, component, modifiers, signal }) {
            el.addEventListener('click', (e) => {
                if (modifiers.has('prevent')) e.preventDefault();
                Directives.invoke(expression, component, el);
            }, { signal });
        },

        /**
         * Bind a form field to a property of the component.
         *
         *     <input pb:model="title">                  kept here until something is sent
         *     <input pb:model.live="query">             as it is typed
         *     <input pb:model.live.debounce.750ms="q">  once the typing has stopped
         *     <input pb:model.blur="title">             when the field is left
         *     <input pb:model.change="country">         when another option is chosen
         *     <input pb:model.number="quantity">        read as a number
         *
         * Written on its own it says nothing to the server: what is typed is
         * kept on the page and travels with whatever the component asks next,
         * so filling in a form costs no requests and saving it sees all of it.
         */
        model({ el, expression, component, modifiers, signal }) {
            const cast = { number: modifiers.has('number'), boolean: modifiers.has('boolean') };

            // .fill takes what the markup already holds for the property, for a
            // field the server wrote a value straight into
            if (modifiers.has('fill')) {
                component.setLocal(expression, Directives.castValue(fieldValue(el, expression), cast));
            } else {
                writeField(el, component.getState()[expression]);
                component.seedLocal(expression, component.getState()[expression]);
            }

            const read = () => Directives.castValue(fieldValue(el, expression), cast);

            const live = modifiers.has('live');
            const onBlur = modifiers.has('blur');
            const onChange = modifiers.has('change') || modifiers.has('lazy');
            const throttle = modifiers.duration('throttle', null);

            let lastSent = 0;

            const send = (value) => {
                if (throttle !== null) {
                    const now = Date.now();
                    if (now - lastSent < throttle) return;

                    lastSent = now;
                    component.setProperties([expression, value], 0);
                    return;
                }

                component.setProperties([expression, value], modifiers.duration('debounce', 150));
            };

            const typed = (andSend) => () => {
                const value = read();

                component.setLocal(expression, value);

                if (andSend) send(value);
            };

            // What is typed is always kept here; what differs is when, if ever,
            // the server is told about it
            el.addEventListener('input', typed(live), { signal });
            el.addEventListener('change', typed(live || onChange), { signal });

            if (onBlur) el.addEventListener('blur', typed(true), { signal });

            // An answer says what the property holds now; a field being typed
            // into is left alone, its own value being the newer of the two
            component.onStateChange(() => {
                if (el.ownerDocument?.activeElement === el) return;

                writeField(el, component.formState.values[expression]);
            }, signal);
        },

        submit({ el, expression, component, signal }) {
            el.addEventListener('submit', (e) => {
                e.preventDefault();
                
                // Disable form while submitting
                const submitButton = el.querySelector('button[type="submit"], input[type="submit"]');
                const inputs = el.querySelectorAll('input, textarea, select');
                
                if (submitButton) submitButton.disabled = true;
                inputs.forEach(input => input.readOnly = true);
                
                Promise.resolve(Directives.invoke(expression, component, el)).finally(() => {
                    if (submitButton) submitButton.disabled = false;
                    inputs.forEach(input => input.readOnly = false);
                });
            }, { signal });
        },

        /**
         * Show an element while the server is being asked something.
         *
         *     <span pb:loading>saving...</span>
         *     <span pb:loading.remove>save</span>
         *     <button pb:loading.attr="disabled" pb:target="save">
         *     <div pb:loading.flex.delay.300ms>
         *
         * pb:target narrows it to one action or one property; without it the
         * element is about whatever the component is doing.
         */
        loading({ el, expression, component, modifiers, signal }) {
            const inverted = modifiers.has('remove');
            const display = ['flex', 'grid', 'inline-flex', 'inline-block', 'block', 'table']
                .find(name => modifiers.has(name)) || 'block';
            const delay = modifiers.duration('delay', 0);

            const shown = () => {
                if (modifiers.has('class')) el.classList.add(...(expression || 'loading').split(' '));
                else if (modifiers.has('attr')) el.setAttribute(expression || 'disabled', 'true');
                else el.style.display = inverted ? 'none' : display;
            };

            const hidden = () => {
                if (modifiers.has('class')) el.classList.remove(...(expression || 'loading').split(' '));
                else if (modifiers.has('attr')) el.removeAttribute(expression || 'disabled');
                else el.style.display = inverted ? display : 'none';
            };

            let showing = false;
            let waiting = null;

            const apply = () => (showing ? shown() : hidden());

            // Nothing is in flight yet, so an element that only shows while
            // something is starts out of the way
            apply();

            component.onLoadingStart((payload) => {
                if (!Directives.matchesTarget(el, payload)) return;

                // A request answered sooner than the delay never shows anything,
                // which is the point of asking for one
                const show = () => { showing = true; shown(); };

                if (delay) waiting = setTimeout(show, delay);
                else show();
            }, signal);

            component.onLoadingEnd((payload) => {
                if (!Directives.matchesTarget(el, payload)) return;

                clearTimeout(waiting);
                waiting = null;
                showing = false;
                hidden();
            }, signal);

            // New markup is put over the old on every update, and what it says
            // about this element is what the server rendered, which knows
            // nothing of what is in flight. Said again here.
            component.onStateChange(apply, signal);

            signal?.addEventListener('abort', () => clearTimeout(waiting), { once: true });
        },

        // pb:navigate is answered on the document rather than here, so that a
        // link outside any component is followed as well as one inside. This is
        // left as a directive so that a plugin can still take it over.
        navigate() {},

        current({ el, expression, component }) {
            const currentPath = window.location.pathname;
            const href = el.getAttribute('href');
            
            if (href === currentPath) {
                const classes = expression ? expression.split(' ') : [];
                el.classList.add(...classes);
            }
        },

        /**
         * Hide an element until PyBlade is up.
         *
         * A component is markup before it is anything else, so what it renders
         * is on the page before any of this runs. pb:cloak hides what would
         * otherwise be seen in that moment, and is taken off here -- a handler
         * only runs once the component it belongs to has been built.
         */
        cloak({ el, component, signal }) {
            const uncloak = () => {
                el.style.display = '';
                el.removeAttribute('pb:cloak');
            };

            uncloak();

            // The server renders pb:cloak every time, so every update puts it
            // back on the element and it has to come off again
            component.onStateChange(uncloak, signal);
        },

        /**
         * Show an element while what the page holds differs from the server's.
         *
         *     <span pb:dirty>unsaved</span>
         *     <span pb:dirty.remove>saved</span>
         *     <input pb:dirty.class="border-red" pb:target="title">
         */
        dirty({ el, expression, component, modifiers, signal }) {
            const classes = modifiers.has('class') ? (expression || '').split(' ').filter(Boolean) : [];
            const inverted = modifiers.has('remove');
            const originalDisplay = el.style.display || '';

            const apply = (isDirty) => {
                const on = inverted ? !isDirty : isDirty;

                if (classes.length) {
                    on ? el.classList.add(...classes) : el.classList.remove(...classes);
                } else {
                    el.style.display = on ? originalDisplay : 'none';
                }
            };

            let isDirty = false;

            apply(false);

            component.onDirtyChange((dirty) => {
                // What this element was told to watch, or anything at all
                const watched = Directives.targetsOf(el);

                isDirty = watched.length ? watched.some(name => dirty.has(name)) : dirty.size > 0;
                apply(isDirty);
            }, signal);

            // What an update brings is what the server rendered, which knows
            // nothing of what has been typed since
            component.onStateChange(() => apply(isDirty), signal);
        },

        // pb:confirm is asked about by whatever runs the action, in invoke():
        // a listener of its own could not stop pb:click on the same element
        // from running whatever the answer was. Declared so that a project can
        // still take it over with PyBlade.directive().
        confirm() {},

        // pb:transition is read by morphing itself, off the element it is
        // written on: an element arriving has no binding yet, and one leaving
        // is gone before anything could be asked of it. pb:show reads it too.
        // Declared so that a project can take it over with PyBlade.directive().
        transition() {},

        /**
         * Ask the server again, over and over.
         *
         *     <div pb:poll>                      every two seconds
         *     <div pb:poll.15s>                  every fifteen
         *     <div pb:poll="refresh_posts">      calling an action of its own
         *     <div pb:poll.visible>              only while it is on screen
         *     <div pb:poll.keep-alive>           even with the page in the background
         *
         * A page nobody is looking at polls at a twentieth of its rate, which
         * is the traffic of a tab left open all afternoon rather than that of
         * one being read. .keep-alive is for what must not fall behind.
         */
        poll({ el, expression, component, modifiers, signal }) {
            const interval = modifiers.timing(2000);
            const keepAlive = modifiers.has('keep-alive');
            const onlyWhenSeen = modifiers.has('visible');

            let timer = null;
            let inFlight = false;
            let seen = !onlyWhenSeen;

            const tick = async () => {
                // A server slower than the interval would otherwise be asked
                // again before it has answered, and again, and again
                if (inFlight || !seen) return;

                inFlight = true;
                try {
                    await (expression ? component.callServerMethod(expression, []) : component.refresh());
                } finally {
                    inFlight = false;
                }
            };

            const schedule = () => {
                clearInterval(timer);
                timer = setInterval(tick, pollRate(interval, { hidden: pageHidden(), keepAlive }));
            };

            schedule();

            // The rate is not the same with the page in the background, so it
            // is worked out again whenever that changes
            onPageVisibility(schedule, signal);

            let watcher = null;
            if (onlyWhenSeen && typeof IntersectionObserver === 'function') {
                watcher = new IntersectionObserver(([entry]) => { seen = entry.isIntersecting; });
                watcher.observe(el);
            }

            // One timer per binding: it is cleared when the binding is renewed,
            // when the element goes away and when the component is destroyed.
            const stop = () => {
                clearInterval(timer);
                watcher?.disconnect();
            };

            signal.addEventListener('abort', stop, { once: true });
            component.onDestroy(stop, signal);
        },

        offline({ el, component, signal }) {
            const updateOfflineStatus = () => {
                el.style.display = navigator.onLine ? 'none' : '';
            };

            window.addEventListener('online', updateOfflineStatus, { signal });
            window.addEventListener('offline', updateOfflineStatus, { signal });
            component.onStateChange(updateOfflineStatus, signal);
            updateOfflineStatus();
        },

        // pb:ignore, pb:replace and pb:key are read by morphing itself, off the
        // elements they are written on: what they say has to be known of an
        // element that has no binding yet, and of a page being navigated to,
        // where no component is doing the morphing. They are declared here so
        // that a project can still take one over with PyBlade.directive().
        ignore() {},
        replace() {},
        key() {},

        /**
         * Keep an element on the page only while a condition holds.
         *
         *     <div pb:show="visible">
         *     <div pb:show="!archived">
         *     <div pb:show="count > 3">
         *     <div pb:show="status == 'done'" pb:transition>
         *
         * The element stays where it is either way -- it is hidden rather than
         * taken out -- so what is inside it keeps whatever state it had.
         */
        show({ el, expression, component, signal }) {
            const spec = transitionOf(el);
            const hidden = () => { el.style.display = 'none'; };
            const shown = () => { el.style.display = ''; };

            let showing = null;

            const apply = (andAnimate) => {
                const wanted = readCondition(expression, component.getState());
                if (wanted === showing) return;

                const first = showing === null;
                showing = wanted;

                if (!spec || !andAnimate || first) {
                    wanted ? shown() : hidden();
                    return;
                }

                if (wanted) {
                    shown();
                    enter(el, spec);
                } else {
                    // Hidden rather than removed once it has finished going:
                    // the element belongs to the markup, not to the animation
                    animateOut(el, spec, hidden);
                }
            };

            apply(false);

            // What an update brings is the markup as the server renders it,
            // which says nothing about what is hidden here
            component.onStateChange(() => apply(true), signal);
        },

        /**
         * Show what an action streams here, as it streams it.
         *
         *     <div pb:stream="summary"></div>
         *     <div pb:stream.replace="status"></div>
         *
         * What arrives is added to what is there, so an answer written a word
         * at a time reads as it is written. Written .replace, each piece stands
         * in place of the last, which is what a status line wants.
         */
        stream({ el, expression, component, modifiers, signal }) {
            const replacing = modifiers.has('replace');

            component.onStreamUpdate((chunk) => {
                if (chunk.to !== expression) return;

                if (chunk.replace || replacing) el.textContent = chunk.content;
                else el.textContent += chunk.content;
            }, signal);

            // A second run starts from nothing rather than from where the first
            // one left off: what is streamed is the answer, not more of it
            component.onLoadingStart((payload) => {
                if (!replacing && Directives.matchesTarget(el, payload)) el.textContent = '';
            }, signal);
        },

        text({ el, expression, component, signal }) {
            const updateText = () => {
                const state = component.getState();
                el.textContent = state[expression] || '';
            };
            
            updateText();
            component.onStateChange(updateText, signal);
        }
    },

    // Scans an element for any pb:* attributes.
    //
    // Runs again after every update, on a DOM that morphing left mostly in
    // place. An element already carrying a directive keeps the binding it was
    // given: binding it a second time would add a second event listener, and
    // one click would then count twice. A binding is renewed only when the
    // expression it was made from has changed, and dropped when the element
    // it belongs to is gone.
    apply(element, component) {
        const bindings = component._bindings || (component._bindings = new Map());

        // A component written inside this one binds its own directives: what
        // belongs to it would otherwise be bound twice, and its actions asked
        // of the component around it, which never declared them.
        const targets = [element, ...element.querySelectorAll('*')].filter(
            el => el === element || (el.closest?.('[pb\\:id]') ?? element) === element,
        );
        const present = new Set(targets);

        for (const el of [...bindings.keys()]) {
            if (!present.has(el)) {
                bindings.get(el).forEach(binding => binding.controller.abort());
                bindings.delete(el);
            }
        }

        targets.forEach(el => {
            Array.from(el.attributes || []).forEach(attr => {
                if (!attr.name.startsWith('pb:')) return;

                // "pb:model.live.debounce.500ms" -> name: "model", modifiers: the rest
                const [directiveName] = attr.name.replace('pb:', '').split('.');
                const modifiers = Modifiers.from(attr.name);
                const handler = this.handlers[directiveName];

                if (!handler) return;

                let bound = bindings.get(el);
                const existing = bound && bound.get(attr.name);

                if (existing && existing.expression === attr.value) return;
                if (existing) existing.controller.abort();

                if (!bound) {
                    bound = new Map();
                    bindings.set(el, bound);
                }

                // Everything a directive holds on to is tied to this signal, so
                // that renewing or dropping the binding takes it all with it.
                const controller = new AbortController();
                bound.set(attr.name, { expression: attr.value, controller });

                handler({
                    el,
                    expression: attr.value,
                    component,
                    modifiers,
                    // What a handler taking a single modifier has always read,
                    // kept for the directives a project registers of its own
                    modifier: modifiers.first,
                    signal: controller.signal,
                });
            });
        });
    },

    // Drops every binding made for a component
    release(component) {
        const bindings = component._bindings;
        if (!bindings) return;

        bindings.forEach(bound => bound.forEach(binding => binding.controller.abort()));
        bindings.clear();
    },

    // Allows users/plugins to easily extend PyBlade
    add(name, callback) {
        this.handlers[name] = callback;
    }
};