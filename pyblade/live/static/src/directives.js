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
                component.setProperties({ [expression]: e.target.value });
            });
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