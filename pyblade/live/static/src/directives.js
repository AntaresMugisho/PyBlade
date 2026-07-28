export const Directives = {
    // Registry of built-in and custom directives
    handlers: {
        click({ el, expression, component, modifier }) {
            el.addEventListener('click', (e) => {
                if (modifier === 'prevent') e.preventDefault();
                component.callServerMethod(expression);
            });
        },

        model({ el, expression, component }) {
            // Two-way binding
            el.addEventListener('input', (e) => {
                component.setProperties([expression, e.target.value]);
            });
        },

        submit({ el, expression, component }) {
            el.addEventListener('submit', (e) => {
                e.preventDefault();
                
                // Disable form while submitting
                const submitButton = el.querySelector('button[type="submit"], input[type="submit"]');
                const inputs = el.querySelectorAll('input, textarea, select');
                
                if (submitButton) submitButton.disabled = true;
                inputs.forEach(input => input.readOnly = true);
                
                component.callServerMethod(expression).finally(() => {
                    if (submitButton) submitButton.disabled = false;
                    inputs.forEach(input => input.readOnly = false);
                });
            });
        },

        loading({ el, expression, component, modifier }) {
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
            });
            
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
            });
        },

        navigate({ el, component }) {
            el.addEventListener('click', (e) => {
                e.preventDefault();
                const href = el.getAttribute('href');
                if (href) {
                    component.navigate(href);
                }
            });
        },

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

        dirty({ el, expression, component }) {
            const originalClasses = el.className;
            
            component.onDirty(() => {
                if (expression === 'remove') {
                    el.style.display = 'none';
                } else if (expression) {
                    el.classList.add(...expression.split(' '));
                }
            });
            
            component.onClean(() => {
                if (expression === 'remove') {
                    el.style.display = '';
                } else if (expression) {
                    el.classList.remove(...expression.split(' '));
                }
            });
        },

        confirm({ el, expression, component }) {
            const originalHandler = el.onclick;
            
            el.addEventListener('click', (e) => {
                const confirmed = confirm(expression || 'Are you sure?');
                if (!confirmed) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            });
        },

        transition({ el, expression, component }) {
            const transitionClass = expression || 'transition';
            el.classList.add(transitionClass);
        },

        poll({ el, expression, component }) {
            const interval = parseInt(expression) || 2000;
            
            const pollInterval = setInterval(() => {
                component.refresh();
            }, interval);
            
            // Cleanup on component destroy
            component.onDestroy(() => {
                clearInterval(pollInterval);
            });
        },

        offline({ el }) {
            const updateOfflineStatus = () => {
                el.style.display = navigator.onLine ? 'none' : 'block';
            };
            
            window.addEventListener('online', updateOfflineStatus);
            window.addEventListener('offline', updateOfflineStatus);
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

        show({ el, expression, component }) {
            const evaluateExpression = () => {
                // Simple boolean evaluation - can be extended
                const state = component.getState();
                const value = state[expression];
                el.style.display = value ? '' : 'none';
            };
            
            evaluateExpression();
            component.onStateChange(evaluateExpression);
        },

        stream({ el, expression, component }) {
            el.setAttribute('data-pb-stream', expression);
            component.onStreamUpdate((data) => {
                if (data.target === expression) {
                    el.textContent = data.content;
                }
            });
        },

        text({ el, expression, component }) {
            const updateText = () => {
                const state = component.getState();
                el.textContent = state[expression] || '';
            };
            
            updateText();
            component.onStateChange(updateText);
        }
    },

    // Scans an element for any pb:* attributes
    apply(element, component) {
        const targets = [element, ...element.querySelectorAll('*')];

        targets.forEach(el => {
            Array.from(el.attributes || []).forEach(attr => {
                if (!attr.name.startsWith('pb:')) return;

                // Syntax parsing: "pb:click.prevent" -> name: "click", modifier: "prevent"
                const [directiveName, modifier] = attr.name.replace('pb:', '').split('.');
                const handler = this.handlers[directiveName];

                if (handler) {
                    handler({ el, expression: attr.value, component, modifier });
                }
            });
        });
    },

    // Allows users/plugins to easily extend PyBlade
    add(name, callback) {
        this.handlers[name] = callback;
    }
};