let customDirectiveNames = new Set();
let components = new Map();

function matchesForCustomDirective(attributeName) {
    return attributeName.match(/^b-/);
}

function extractDirective(el, name) {
    let [value, ...modifiers] = name.replace(/^b-/, '').split('.');
    if (!value) return;
    return new Directive(value, modifiers, name, el);
}

function directive(name, callback) {
    if (customDirectiveNames.has(name)) {
        console.warn(`La directive '${name}' est déjà enregistrée.`);
        return;
    }

    customDirectiveNames.add(name);

    document.addEventListener('directive.init', (event) => {
        const { el, component, directive } = event.detail;
        if (directive && directive.value === name) {
            callback({ el, directive, component, $b: component });
        }
    });
}

function on(eventName, callback) {
    document.addEventListener(eventName, callback);
}

function emit(eventName, detail) {
    document.dispatchEvent(new CustomEvent(eventName, { detail }));
}

class StateManager {
    constructor() {
        this.state = {};
    }

    get(key) {
        return this.state[key];
    }

    set(key, value) {
        this.state[key] = value;
        this.notifyComponents(key);
    }

    notifyComponents(key) {
        components.forEach(component => {
            if (component._data.hasOwnProperty(key)) {
                component.updateDOM({ [key]: this.state[key] });
            }
        });
    }
}

const globalState = new StateManager();

class Component {
    constructor(data = {}) {
        this._data = new Proxy(data, {
            set: (target, key, value) => {
                target[key] = value;
                globalState.set(key, value);
                this.updateDOM({ [key]: value });
                return true;
            }
        });
        
        this.id = Math.random().toString(36).substr(2, 9);
        this._setupModelBindings();
    }

    _setupModelBindings() {
        const rootElement = document.querySelector(`[liveblade_id="${this.id}"]`);
        if (!rootElement) return;

        // Set up model bindings
        rootElement.querySelectorAll('[b-model]').forEach(el => {
            const modelName = el.getAttribute('b-model');
            
            // Initialize value if not exists
            if (!(modelName in this._data)) {
                this._data[modelName] = el.value;
            }

            // Update element with current value
            el.value = this._data[modelName];

            // Listen for input changes with debounce
            let debounceTimeout;
            el.addEventListener('input', (e) => {
                clearTimeout(debounceTimeout);
                debounceTimeout = setTimeout(() => {
                    this._data[modelName] = e.target.value;
                }, 300); // 300ms debounce
            });
        });
    }

    handleModelChange(key, value) {
        // Update all elements bound to this model
        const rootElement = document.querySelector(`[liveblade_id="${this.id}"]`);
        if (!rootElement) return;

        // Update input elements
        rootElement.querySelectorAll(`[b-model="${key}"]`).forEach(el => {
            if (el.value !== value) {
                el.value = value;
            }
        });

        // Update text elements
        rootElement.querySelectorAll(`[b-text="${key}"]`).forEach(el => {
            el.textContent = value;
        });

        // Update conditional elements
        rootElement.querySelectorAll(`[b-if="${key}"]`).forEach(el => {
            el.style.display = value ? '' : 'none';
        });

        // Sync with server
        this.syncModelWithServer(key, value);
    }

    async syncModelWithServer(key, value) {
        try {
            const response = await fetch('/liveblade/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    componentId: this.id.split('.')[1],
                    updates: { [key]: value }
                })
            });

            if (!response.ok) throw new Error('Network response was not ok');
            
            const data = await response.json();
            if (data.error) {
                console.error('Server error:', data.error);
                return;
            }

            if (data.data) {
                this.updateDOM(data.data);
            }
        } catch (error) {
            console.error('Error syncing model:', error);
        }
    }

    updateDOM(html) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;

        const currentComponent = document.querySelector(`[liveblade_id="${this.id}"]`);
        if (currentComponent) {
            morphdom(currentComponent, tempDiv.firstElementChild, {
                onBeforeElUpdated: (fromEl, toEl) => {
                    // Preserve input values
                    if (fromEl.hasAttribute('b-model')) {
                        const modelName = fromEl.getAttribute('b-model');
                        toEl.value = this._data[modelName];
                        return true;
                    }
                    // Preserve focus
                    if (fromEl === document.activeElement) {
                        const index = [...fromEl.parentNode.children].indexOf(fromEl);
                        setTimeout(() => {
                            const newElements = [...toEl.parentNode.children];
                            if (newElements[index]) {
                                newElements[index].focus();
                            }
                        });
                    }
                    return !fromEl.isEqualNode(toEl);
                }
            });
            
            // Re-setup model bindings after DOM update
            this._setupModelBindings();
        }
    }

    async callServerMethod(methodName, el, ...args) {
        const component = el.closest("[liveblade_id]").getAttribute('liveblade_id');
        const loadingTarget = document.querySelector(`[b-loading-target="${methodName}"]`);
        
        try {
            emit('request.start');
            showLoadingForMethod(methodName, loadingTarget || el);
            
            const response = await fetch('/liveblade/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    method: methodName,
                    args: args,
                    componentId: component.split('.')[1]
                })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            console.log('Response data:', data);
            
            if (data.error) {
                console.error('Server error:', data.error);
                return;
            }

            if (data.data) {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = data.data;
                const currentComponent = document.querySelector(`[liveblade_id="${component}"]`);
                if (currentComponent) {
                    morphdom(currentComponent, tempDiv.firstElementChild, {
                        onBeforeElUpdated: (fromEl, toEl) => {
                            // Preserve input values
                            if (fromEl.hasAttribute('b-model')) {
                                const modelName = fromEl.getAttribute('b-model');
                                toEl.value = this._data[modelName];
                                return true;
                            }
                            // Preserve focus
                            if (fromEl === document.activeElement) {
                                const index = [...fromEl.parentNode.children].indexOf(fromEl);
                                setTimeout(() => {
                                    const newElements = [...toEl.parentNode.children];
                                    if (newElements[index]) {
                                        newElements[index].focus();
                                    }
                                });
                            }
                            return !fromEl.isEqualNode(toEl);
                        }
                    });
                    
                    this._setupModelBindings();
                }
            }

            return data;
        } catch (error) {
            console.error('Erreur lors de l\'appel de la méthode serveur:', error);
            emit('blade.error', { message: error.message });
        } finally {
            hideLoadingForMethod(methodName);
            emit('request.end');
        }
    }

    async callServerMethodOld(methodName, el, ...args) {
        document.dispatchEvent(new Event('request.start')); 
        const component = el.closest("[liveblade_id]").getAttribute('liveblade_id')
        try {
            const formData = new FormData();
            formData.append('component', component); 
            formData.append('method', methodName.expression || methodName); 

            // Ajout des paramètres
            if (args.length > 0) {
                args.forEach((arg, index) => {
                    if (typeof arg === 'object') {
                        formData.append(`param${index}`, JSON.stringify(arg));
                        console.log('argument', arg);
                        
                    } else {
                        formData.append(`param${index}`, arg);
                    }
                });
            }
            const response = await fetch('/', {
                method: "POST",
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: formData 
            });

            console.log('Réponse du serveur:', response);

            if (!response.ok) {
                if (response.redirected) {
                    fetch('/scripts/error.html')
                    .then(res=>res.text())
                    .then(error=>{     
                         document.body.innerHTML = error
                          document.querySelector('[error-message]').textContent =  window.location.search
                          }
                     
                    )
                }
            }

               if (response.redirected){
                  window.location.replace(response.url)
                
               }
                // const data = await response.json();
                console.log('Données reçues:',await response.text());
    
                const rootElement = document.getElementById('app'); 
            // if(data.html["navigate"]){
            //     navigateTo(data.html['url'])
            // }   
            // if (rootElement) {
             
            //     morphdom(rootElement, data.html, {
            //         onBeforeElUpdated: (fromEl, toEl) => {
            //             if (fromEl.tagName === 'INPUT' && fromEl.type === 'text') {
            //                 toEl.value = fromEl.value;
            //                 return false; 
            //             }
            //             return true;
            //         }
            //     });
            // } else {
            //     console.error('Erreur : l\'élément racine est introuvable.');
            // }
        } catch (error) {
            console.error('Erreur:', error.message);
        } finally {
            document.dispatchEvent(new Event('request.end')); 
        }
    }

    updateDOM(newData) {
        // Mettre à jour tous les éléments avec b-text
        document.querySelectorAll('[b-text]').forEach(el => {
            const key = el.getAttribute('b-text');
            if (newData.hasOwnProperty(key)) {
                el.textContent = newData[key];
            }
        });

        // Mettre à jour tous les éléments avec b-model
        document.querySelectorAll('[b-model]').forEach(el => {
            const key = el.getAttribute('b-model');
            if (newData.hasOwnProperty(key)) {
                el.value = newData[key];
            }
        });

        // Mettre à jour les éléments avec b-show
        document.querySelectorAll('[b-show]').forEach(el => {
            const key = el.getAttribute('b-show');
            if (newData.hasOwnProperty(key)) {
                el.style.display = newData[key] ? '' : 'none';
            }
        });

        // Si nous avons reçu du HTML, mettre à jour le contenu
        if (newData.html) {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = newData.html;
            
            // Trouver l'élément parent avec l'attribut liveblade_id
            const currentComponent = document.querySelector(`[liveblade_id="${this.id}"]`);
            if (currentComponent) {
                currentComponent.innerHTML = tempDiv.firstElementChild.innerHTML;
            }
        }
    }
}

// Classe pour représenter une directive
class Directive {
    constructor(value, modifiers, rawName, el) {
        this.rawName = this.raw = rawName;
        this.value = value;
        this.modifiers = modifiers;
        this.el = el;
        this.eventContext = {};
        this.expression = el.getAttribute(rawName);
    }

    get params() {
        const regex = /\(([^)]+)\)/; 
        const match = this.el.getAttribute(this.rawName).match(regex);
        if (match) {
            const paramsArray = match[1].split(',').map(param => param.trim());
            return paramsArray.reduce((acc, param) => {
                acc[param] = this.el.getAttribute(param); 
                return acc;
            }, {});             
        }

        // Vérification pour les formulaires et les inputs
        if (this.el.tagName.toLowerCase() === 'form') {
            const params = {};
            const modelDirectives = this.el.querySelectorAll('[b-model], [b-upload]');

            modelDirectives.forEach(directiveEl => {
                const directiveName = directiveEl.getAttribute('b-model') || directiveEl.getAttribute('b-upload');
                params[directiveName] = directiveEl.value;
            });

            return params; 
        }

        return {}; 
    }
}

// Fonction pour extraire et formater les paramètres
function formatValue(value) {
    if (typeof value === 'number') return value;
    
    value = value.trim();
    
    if (!isNaN(value) && value !== '') {
        return Number(value);
    }
    
    if (value === 'true') return true;
    if (value === 'false') return false;
    if (value === 'null') return null;
    if (value === 'undefined') return undefined;
    
    try {
        if ((value.startsWith('{') && value.endsWith('}')) || 
            (value.startsWith('[') && value.endsWith(']'))) {
            return JSON.parse(value);
        }
    } catch (e) {}
    
    if ((value.startsWith('"') && value.endsWith('"')) || 
        (value.startsWith("'") && value.endsWith("'"))) {
        return value.slice(1, -1);
    }
    
    return value;
}

// Fonction pour extraire les paramètres
function extractParams(directive) {
    const expression = directive.expression;
    
    if (!expression.includes('(')) {
        return [];
    }
    
    let paramsStr = expression.substring(
        expression.indexOf('(') + 1,
        expression.lastIndexOf(')')
    ).trim();
    
    if (!paramsStr) return [];
    
    let params = [];
    let currentParam = '';
    let bracketCount = 0;
    let inString = false;
    let stringChar = '';
    
    for (let i = 0; i < paramsStr.length; i++) {
        const char = paramsStr[i];
        
        if ((char === '"' || char === "'") && paramsStr[i-1] !== '\\') {
            if (!inString) {
                inString = true;
                stringChar = char;
            } else if (char === stringChar) {
                inString = false;
            }
            currentParam += char;
            continue;
        }
        
        if (char === '{' || char === '[') bracketCount++;
        if (char === '}' || char === ']') bracketCount--;
        
        if (inString || bracketCount > 0) {
            currentParam += char;
            continue;
        }
        
        if (char === ',' && bracketCount === 0) {
            if (currentParam) {
                params.push(currentParam.trim());
            }
            currentParam = '';
            continue;
        }
        
        currentParam += char;
    }
    
    if (currentParam) {
        params.push(currentParam.trim());
    }
    
    return params.map(param => formatValue(param));
}

// Fonction pour récupérer les modèles d'un formulaire
function getFormModels(form, component) {
    const models = {};
    form.querySelectorAll('[b-model]').forEach(el => {
        const modelName = el.getAttribute('b-model');
        models[modelName] = component._data[modelName] || el.value;
    });
    return models;
}

// Directive b-text pour afficher du texte
directive('text', ({ el, component, directive }) => {
    el.textContent = component._data[directive.expression];
});

// Directive b-model pour la liaison de données
directive('model', ({ el, component, directive }) => {
    const updateModel = () => {
        component._data[directive.expression] = el.value;
    };

    el.addEventListener('input', updateModel);
    el.value = component._data[directive.expression] || '';
});

// Directive b-click pour gérer les clics
directive('click', ({ el, component, directive }) => {

    let isProcessing = false;
    
    el.addEventListener('click', async () => {
        // Si déjà en cours de traitement, ne rien faire
        console.log(el, 'click');
        
        if (isProcessing) {
            console.log('Click already processing');
            return;
        }
        
        try {
            isProcessing = true;
            const methodName = directive.expression.split('(')[0];
            const args = extractParams(directive);
            console.log('Method:', methodName, 'Args:', args);
            await component.callServerMethod(methodName, el, args);
        } catch (error) {
            console.error('Erreur lors du clic:', error);
        } finally {
            // Réinitialiser le flag après un court délai
            setTimeout(() => {
                isProcessing = false;
            }, 300); // 300ms de debounce
        }
    });
});

// Directive b-submit pour gérer les soumissions de formulaire
directive('submit', ({ el, component, directive }) => {
    el.addEventListener('submit', async (event) => {
        event.preventDefault();
        try {
            const params = getFormModels(el, component);
            console.log('Form data:', params);
            await component.callServerMethod(directive, el, [params]);
        } catch (error) {
            console.error('Erreur lors de la soumission:', error);
        }
    });
});

directive("valided",({el,component, directive})=>{
    fetch('/',{
        method:"POST",  
        body:'valided',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
    })
    if (el.tagName == "form"){
        el.querySelectorAll("[b-model]")
        .forEach((child)=>{

        })
    }
    
})

// Directive b-submit pour la soumission des formulaires
directive('submit', ({ el, component, directive }) => {
    el.addEventListener('submit', async (event) => {
        event.preventDefault();
        try {
            const formModels = getFormModels(el, component);
            
            const methodName = directive.expression.split('(')[0];
            
            await component.callServerMethod(methodName, el, {form_data: formModels});
            el.reset();
            Object.keys(formModels).forEach(key => {
                component._data[key] = '';
            });
        } catch (error) {
            console.error('Erreur lors de la soumission du formulaire:', error);
        }
    });
});

directive('live', ({ el, directive, component }) => {
    const methodName = directive.expression;
    console.log('Live directive setup for method:', directive);
    
    const debounceTime = 300;
    let timeout;
    
    // Gérer les événements input
    const handleInput = async (event) => {
        const value = event.target.value;
        console.log('Input value:', value);
        
        if (timeout) {
            clearTimeout(timeout);
        }
        
        // Créer un nouveau timeout
        timeout = setTimeout(async () => {
            try {
                console.log('Calling server method:', methodName, 'with value:', value);
                await component.callServerMethod(methodName, el, [value]);
            } catch (error) {
                console.error('Error in live directive:', error);
            }
        }, debounceTime);
    };
    
    // Ajouter l'écouteur d'événements
    el.addEventListener('input', handleInput);
    
    // Nettoyer quand l'élément est supprimé
    return () => {
        el.removeEventListener('input', handleInput);
        if (timeout) {
            clearTimeout(timeout);
        }
    };
});

directive('focus', ({ el }) => {
    el.focus();
});

directive('blur', ({ el, directive }) => {
    el.addEventListener('blur', () => {
        // Ajoutez ici le code pour gérer l'événement blur si nécessaire
    });
});

directive('show', ({ el, component, directive }) => {
    const updateVisibility = () => {
        el.style.display = component._data[directive.expression] ? '' : 'none';
    };
    updateVisibility();
    component.updateDOM = (newData) => {
        if (newData.hasOwnProperty(directive.expression)) {
            updateVisibility();
        }
    };
});

// Directive b-change pour gérer les changements de valeur
directive('change', ({ el, component, directive }) => {
    const debounceTime = parseInt(directive.modifiers.find(mod => mod.includes('debounce'))) || 300;
    let timeout;
    let lastExecution = 0;

    const executeChangeUpdate = async () => {
        try {
            const params = directive.params; 
            await component.callServerMethod({ expression: el.getAttribute(`b-${directive.value}`) },el, [el.getAttribute('b-model'), el.value]);
        } catch (error) {
            console.error('Erreur lors de la mise à jour avec changement:', error);
        }
    };

    const handleEvent = (event) => {
        const now = Date.now();
        let shouldUpdate = true;

        directive.modifiers.forEach(modifier => {
            if (modifier === 'debounce') {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    executeChangeUpdate();
                }, debounceTime);
                shouldUpdate = false;
            } else if (modifier === 'throttle') {
                if (now - lastExecution >= debounceTime) {
                    lastExecution = now;
                    if (shouldUpdate) {
                        executeChangeUpdate();
                    }
                }
                shouldUpdate = false;
            } else if (modifier === 'filter') {
                const filterCondition = directive.modifiers[1];
                if (filterCondition && !el.value.includes(filterCondition)) {
                    shouldUpdate = false;
                }
            }
        });

        if (shouldUpdate) {
            executeChangeUpdate();
        }
    };

    el.addEventListener('change', handleEvent);
});

directive('upload', ({ el, directive, component }) => {
    console.log('Upload directive setup:', directive);
    
    const methodName = directive.expression;
    const isMultiple = directive.modifiers.includes('multiple');
    
    // Configurer l'élément input
    el.setAttribute('type', 'file');
    if (isMultiple) {
        el.setAttribute('multiple', true);
    }
    
    // Gérer le changement de fichier
    const handleFileChange = async (event) => {
        const files = event.target.files;
        if (!files || files.length === 0) return;
        
        try {
            const filesData = {};
            
            // Ajouter tous les fichiers sélectionnés
            if (isMultiple) {
                Array.from(files).forEach((file, index) => {
                    const tmp_url = URL.createObjectURL(file);
                    filesData[`file${index}`] = {
                        name: file.name,
                        type: file.type,
                        size: file.size,
                        url_tmp: tmp_url
                    };
                });
            } else {
                const file = files[0];
                const tmp_url = URL.createObjectURL(file);
                filesData.file = {
                    name: file.name,
                    type: file.type,
                    size: file.size,
                    url_tmp: tmp_url
                };
            }
            
            // Récupérer l'ID du composant
            const componentId = el.closest("[liveblade_id]").getAttribute('liveblade_id');
            
            console.log('Files data to send:', filesData);
            
            // Appeler la méthode du serveur
            const response = await fetch('/liveblade/', {
                method: 'POST',
                body: JSON.stringify({
                    componentId: componentId.split('.')[1],
                    method: methodName,
                    files: filesData
                }),
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken()
                }
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('Upload result:', result);
            
            // Mettre à jour le composant avec la réponse
            if (result.data) {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = result.data;
                const newContent = tempDiv.firstElementChild;

                const currentComponent = document.querySelector(`[liveblade_id="${componentId}"]`);
                if (currentComponent) {
                    morphdom(currentComponent, newContent, {
                        onBeforeElUpdated: (fromEl, toEl) => {
                            // Preserve input values
                            if (fromEl.hasAttribute('b-model')) {
                                const modelName = fromEl.getAttribute('b-model');
                                const comp = new Component();
                                toEl.value = comp._data[modelName];
                                return true;
                            }
                            // Preserve focus
                            if (fromEl === document.activeElement) {
                                const index = [...fromEl.parentNode.children].indexOf(fromEl);
                                setTimeout(() => {
                                    const newElements = [...toEl.parentNode.children];
                                    if (newElements[index]) {
                                        newElements[index].focus();
                                    }
                                });
                            }
                            // Ne pas mettre à jour si les éléments sont identiques
                            if (fromEl.isEqualNode(toEl)) {
                                return false;
                            }
                            // Préserver les écouteurs d'événements sur les éléments avec des directives
                            if (fromEl.hasAttribute && Array.from(fromEl.attributes).some(attr => attr.name.startsWith('b-'))) {
                                toEl.getAttributeNames().forEach(name => {
                                    if (!name.startsWith('b-')) {
                                        fromEl.setAttribute(name, toEl.getAttribute(name));
                                    }
                                });
                                return true;
                            }
                            return true;
                        }
                    });

                    // Re-setup model bindings after DOM update
                    const comp = new Component();
                    comp._setupModelBindings();
                }
            }
            
        } catch (error) {
            console.error('Error uploading files:', error);
        }
        
        // Réinitialiser l'input pour permettre de sélectionner le même fichier
        el.value = '';
    };
    
    // Ajouter l'écouteur d'événements
    el.addEventListener('change', handleFileChange);
    
    // Nettoyer quand l'élément est supprimé
    return () => {
        el.removeEventListener('change', handleFileChange);
    };
});

// Fonction utilitaire pour obtenir le token CSRF
function getCsrfToken() {
    const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
    return tokenElement ? tokenElement.value : '';
}

directive('navigate', ({ el }) => {
    el.addEventListener('click', async (event) => {
        event.preventDefault();
        const url = el.getAttribute('href'); 
        if (url) {
            await navigateTo(url);
        }
    });
});

// Fonction pour gérer la navigation
async function navigateTo(url) {
    document.dispatchEvent(new Event('navigation.start')); 
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('Erreur lors du chargement de la page');
        }
        const data = await response.text();
        const rootElement = document.getElementById('app');
        
        rootElement.innerHTML = data;
        
        // Réinitialiser les directives sur le nouveau contenu
        initializeApp(rootElement, Component);
    } catch (error) {
        console.error('Erreur:', error.message);
    } finally {
        document.dispatchEvent(new Event('navigation.end')); 
    }
}

// Écouteur d'événements pour gérer les changements d'état de l'historique
window.addEventListener('popstate', async (event) => {
    const url = location.pathname;
    await navigateTo(url);
});

function initializeApp(rootElement, componentClass) {
    const component = new componentClass();
    components.set(rootElement, component);

    const directives = Array.from(rootElement.querySelectorAll('*'))
        .flatMap(el => Array.from(el.attributes)
            .filter(attr => matchesForCustomDirective(attr.name))
            .map(attr => extractDirective(el, attr.name)));

    directives.forEach(directive => {
        emit('directive.init', { el: directive.el, component, directive });
    });

    return component;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Styles pour le loading
const loadingStyles = `
.blade-loading {
    position: relative;
    pointer-events: none;
    opacity: 0.6;
    transition: opacity 0.3s;
}

/* Spinner classique */
.blade-loading-spinner::after {
    content: "";
    position: absolute;
    top: calc(50% - 0.5em);
    left: calc(50% - 0.5em);
    width: 1em;
    height: 1em;
    border: 2px solid #3498db;
    border-radius: 50%;
    border-top-color: transparent;
    animation: blade-spin 0.6s linear infinite;
}

/* Dots loading */
.blade-loading-dots::after {
    content: "...";
    position: absolute;
    animation: blade-dots 1.5s infinite;
    font-weight: bold;
    letter-spacing: 2px;
}

/* Pulse loading */
.blade-loading-pulse::after {
    content: "";
    position: absolute;
    top: calc(50% - 0.5em);
    left: calc(50% - 0.5em);
    width: 1em;
    height: 1em;
    background: #3498db;
    border-radius: 50%;
    animation: blade-pulse 1s ease-in-out infinite;
}

/* Progress bar */
.blade-loading-progress::after {
    content: "";
    position: absolute;
    bottom: 0;
    left: 0;
    height: 2px;
    background: #3498db;
    animation: blade-progress 1s ease-in-out infinite;
}

/* Skeleton loading */
.blade-loading-skeleton {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: blade-skeleton 1.5s infinite;
}

/* Fade loading */
.blade-loading-fade {
    animation: blade-fade 1s ease-in-out infinite alternate;
}

/* Bounce loading */
.blade-loading-bounce::after {
    content: "";
    position: absolute;
    top: calc(50% - 0.25em);
    left: calc(50% - 0.25em);
    width: 0.5em;
    height: 0.5em;
    background: #3498db;
    border-radius: 50%;
    animation: blade-bounce 0.5s cubic-bezier(0.19, 1, 0.22, 1) infinite alternate;
}

/* Overlay avec différents styles */
.blade-loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(255, 255, 255, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.blade-loading-overlay.blur {
    backdrop-filter: blur(3px);
}

.blade-loading-overlay.dark {
    background: rgba(0, 0, 0, 0.5);
}

/* Button loading styles */
.blade-loading-button {
    position: relative;
    padding-right: 2.5em;
}

.blade-loading-button::after {
    content: "";
    position: absolute;
    right: 0.75em;
    top: calc(50% - 0.5em);
    width: 1em;
    height: 1em;
    border: 2px solid currentColor;
    border-radius: 50%;
    border-top-color: transparent;
    animation: blade-spin 0.6s linear infinite;
}

/* Animations */
@keyframes blade-spin {
    to { transform: rotate(360deg); }
}

@keyframes blade-dots {
    0%, 20% { content: "."; }
    40% { content: ".."; }
    60%, 100% { content: "..."; }
}

@keyframes blade-pulse {
    0% { transform: scale(0.8); opacity: 0.5; }
    100% { transform: scale(1.2); opacity: 0; }
}

@keyframes blade-progress {
    0% { width: 0; }
    50% { width: 100%; }
    100% { width: 0; }
}

@keyframes blade-skeleton {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

@keyframes blade-fade {
    0% { opacity: 0.4; }
    100% { opacity: 0.8; }
}

@keyframes blade-bounce {
    from { transform: translateY(-50%); }
    to { transform: translateY(50%); }
}
`;

// Ajouter les styles au document
document.head.insertAdjacentHTML('beforeend', `<style>${loadingStyles}</style>`);

function updateLoadingState(el, isLoading) {
    // Récupérer les modifiers
    const modifiers = el.getAttribute('b-loading-modifiers')?.split(' ') || [];
    
    if (isLoading) {
        el.classList.add('blade-loading');
        
        // Appliquer les modifiers
        if (modifiers.includes('spinner')) {
            el.classList.add('blade-loading-spinner');
        }
        if (modifiers.includes('dots')) {
            el.classList.add('blade-loading-dots');
        }
        if (modifiers.includes('pulse')) {
            el.classList.add('blade-loading-pulse');
        }
        if (modifiers.includes('progress')) {
            el.classList.add('blade-loading-progress');
        }
        if (modifiers.includes('skeleton')) {
            el.classList.add('blade-loading-skeleton');
        }
        if (modifiers.includes('fade')) {
            el.classList.add('blade-loading-fade');
        }
        if (modifiers.includes('bounce')) {
            el.classList.add('blade-loading-bounce');
        }
        if (modifiers.includes('button')) {
            el.classList.add('blade-loading-button');
        }
        if (modifiers.includes('overlay')) {
            const overlay = document.createElement('div');
            overlay.className = 'blade-loading-overlay';
            if (modifiers.includes('blur')) overlay.classList.add('blur');
            if (modifiers.includes('dark')) overlay.classList.add('dark');
            el.appendChild(overlay);
        }
        if (modifiers.includes('disabled')) {
            el.setAttribute('disabled', 'disabled');
        }
    } else {
        el.classList.remove(
            'blade-loading',
            'blade-loading-spinner',
            'blade-loading-dots',
            'blade-loading-pulse',
            'blade-loading-progress',
            'blade-loading-skeleton',
            'blade-loading-fade',
            'blade-loading-bounce',
            'blade-loading-button'
        );
        el.removeAttribute('disabled');
        const overlay = el.querySelector('.blade-loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
}

// Gestion globale du loading
let activeRequests = new Map();

function showLoadingForMethod(method, el) {
    if (!activeRequests.has(method)) {
        activeRequests.set(method, new Set());
    }
    if (el) {
        activeRequests.get(method).add(el);
        updateLoadingState(el, true);
    }
}

function hideLoadingForMethod(method) {
    if (activeRequests.has(method)) {
        const elements = activeRequests.get(method);
        elements.forEach(el => updateLoadingState(el, false));
        activeRequests.delete(method);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const rootElement = document.querySelector('body');
    initializeApp(rootElement, Component); 
});
