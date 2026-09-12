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
     * Run what a directive was given: an event to emit, or an action to call.
     */
    invoke(expression, component) {
        const event = this.parseEmit(expression);

        if (event) return component.emit(event);

        const { methodName, args } = this.parseExpression(expression);
        return component.callServerMethod(methodName, args);
    },

    handlers: {
        click({ el, expression, component, modifier, signal }) {
            el.addEventListener('click', (e) => {
                if (modifier === 'prevent') e.preventDefault();
                Directives.invoke(expression, component);
            }, { signal });
        },

        model({ el, expression, component, modifier, signal }) {
            const state = component.getState();
            
            // Set initial value from state
            if (state[expression] !== undefined) {
                el.value = state[expression];
                component.formState.values[expression] = state[expression];
            }

            // Parse modifiers
            const modifiers = modifier ? modifier.split('.') : [];
            const isLive = modifiers.includes('live');
            const isNumber = modifiers.includes('number');
            
            // Parse debounce delay (e.g., "debounce.500ms" -> 500)
            const debounceModifier = modifiers.find(m => m.startsWith('debounce'));
            let debounceDelay = 300; // default 300ms
            if (debounceModifier) {
                const match = debounceModifier.match(/debounce\.(\d+)ms/);
                if (match) {
                    debounceDelay = parseInt(match[1]);
                }
            }

            const updateValue = (value) => {
                // Cast to number if modifier is present
                let finalValue = value;
                if (isNumber) {
                    finalValue = value === '' ? '' : parseFloat(value);
                }

                // Update local form state immediately (react-hook-form pattern)
                component.formState.values[expression] = finalValue;
                component.formState.dirtyFields.add(expression);
                component.formState.touchedFields.add(expression);

                if (isLive) {
                    // Use component's batched update mechanism (debounced)
                    component.setProperties([expression, finalValue]);
                }
                // If not live, don't send to server - wait for blur
            };

            if (isLive) {
                // Live mode: update on input with debouncing
                el.addEventListener('input', (e) => {
                    updateValue(e.target.value);
                }, { signal });
            } else {
                // Lazy mode (default): update on blur
                el.addEventListener('blur', (e) => {
                    updateValue(e.target.value);
                }, { signal });
            }

            // Preserve value during DOM updates - read from local form state
            component.onStateChange(() => {
                const localValue = component.formState.values[expression];
                // Only update if the value changed on the server (not from local input)
                if (document.activeElement !== el && localValue !== undefined) {
                    el.value = localValue;
                }
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
                
                Promise.resolve(Directives.invoke(expression, component)).finally(() => {
                    if (submitButton) submitButton.disabled = false;
                    inputs.forEach(input => input.readOnly = false);
                });
            }, { signal });
        },

        loading({ el, expression, component, modifier, signal }) {
            const target = modifier === 'remove' ? el : el;
            const originalDisplay = target.style.display || '';
            
            component.onLoadingStart(() => {
                if (modifier === 'remove') {
                    target.style.display = 'none';
                } else if (modifier === 'class') {
                    target.classList.add(expression || 'loading');
                } else if (modifier === 'attr') {
                    target.setAttribute('disabled', 'true');
                } else {
                    target.style.display = 'block';
                }
            }, signal);
            
            component.onLoadingEnd(() => {
                if (modifier === 'remove') {
                    target.style.display = originalDisplay;
                } else if (modifier === 'class') {
                    target.classList.remove(expression || 'loading');
                } else if (modifier === 'attr') {
                    target.removeAttribute('disabled');
                } else {
                    target.style.display = 'none';
                }
            }, signal);
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

        cloak({ el }) {
            el.style.display = 'none';
            // Will be removed by PyBlade initialization
            setTimeout(() => {
                el.style.display = '';
            }, 0);
        },

        dirty({ el, expression, component, signal }) {
            const originalClasses = el.className;
            
            component.onDirty(() => {
                if (expression === 'remove') {
                    el.style.display = 'none';
                } else if (expression) {
                    el.classList.add(...expression.split(' '));
                }
            }, signal);
            
            component.onClean(() => {
                if (expression === 'remove') {
                    el.style.display = '';
                } else if (expression) {
                    el.classList.remove(...expression.split(' '));
                }
            }, signal);
        },

        confirm({ el, expression, component, signal }) {
            el.addEventListener('click', (e) => {
                const confirmed = confirm(expression || 'Are you sure?');
                if (!confirmed) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            }, { signal });
        },

        transition({ el, expression, component }) {
            const transitionClass = expression || 'transition';
            el.classList.add(transitionClass);
        },

        poll({ el, expression, component, signal }) {
            const interval = parseInt(expression) || 2000;

            const pollInterval = setInterval(() => {
                component.refresh();
            }, interval);

            // One timer per binding: it is cleared when the binding is renewed,
            // when the element goes away and when the component is destroyed.
            signal.addEventListener('abort', () => clearInterval(pollInterval), { once: true });
            component.onDestroy(() => clearInterval(pollInterval), signal);
        },

        offline({ el, signal }) {
            const updateOfflineStatus = () => {
                el.style.display = navigator.onLine ? 'none' : 'block';
            };

            window.addEventListener('online', updateOfflineStatus, { signal });
            window.addEventListener('offline', updateOfflineStatus, { signal });
            updateOfflineStatus();
        },

        ignore({ el, modifier }) {
            el.setAttribute('data-pb-ignore', 'true');
            if (modifier === 'attrs') {
                el.setAttribute('data-pb-ignore-attrs', 'true');
            }
        },

        replace({ el, modifier }) {
            el.setAttribute('data-pb-replace', 'true');
            if (modifier === 'self') {
                el.setAttribute('data-pb-replace-self', 'true');
            }
        },

        show({ el, expression, component, signal }) {
            const evaluateExpression = () => {
                // Simple boolean evaluation - can be extended
                const state = component.getState();
                const value = state[expression];
                el.style.display = value ? '' : 'none';
            };
            
            evaluateExpression();
            component.onStateChange(evaluateExpression, signal);
        },

        stream({ el, expression, component, signal }) {
            el.setAttribute('data-pb-stream', expression);
            component.onStreamUpdate((data) => {
                if (data.target === expression) {
                    el.textContent = data.content;
                }
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

                // Syntax parsing: "pb:click.prevent" -> name: "click", modifier: "prevent"
                const [directiveName, modifier] = attr.name.replace('pb:', '').split('.');
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

                handler({ el, expression: attr.value, component, modifier, signal: controller.signal });
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