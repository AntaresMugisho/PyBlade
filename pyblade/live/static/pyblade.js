// pyblade.js
document.addEventListener('DOMContentLoaded', () => {
    initPyBlade(document.body);
});

function initPyBlade(rootElement) {
    // 1. Trouver tous les composants PyBlade
    const components = rootElement.querySelectorAll('[pb\\:id]');
    
    components.forEach(el => {
        const componentId = el.getAttribute('pb:id');
        
        // 2. Écouter pb:click
        el.querySelectorAll('[pb\\:click]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const methodName = btn.getAttribute('pb:click');
                callServerMethod(el, componentId, methodName);
            });
        });

        // 3. Écouter pb:model (Two-way data binding)
        el.querySelectorAll('[pb\\:model]').forEach(input => {
            input.addEventListener('input', (e) => {
                const propertyName = input.getAttribute('pb:model');
                const newValue = input.value;
                updateServerProperty(el, componentId, propertyName, newValue);
            });
        });
    });
}

async function callServerMethod(componentEl, componentId, action, payload = {}) {
    // Récupérer le snapshot de l'état actuel du composant
    const snapshot = JSON.parse(componentEl.getAttribute('pb:snapshot'));
    
    // Récupérer le token CSRF depuis l'attribut data-csrf injecté par @pbscripts
    const csrfToken = document.querySelector('script[data-csrf]')?.getAttribute('data-csrf');

    const response = await fetch('/pyblade/live/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
            id: componentId,
            snapshot: snapshot,
            action: action, // ex: 'increment'
            payload: payload
        })
    });

    const data = await response.json();

    // 4. Utiliser Idiomorph pour mettre à jour le DOM intelligemment sans recharger
    Idiomorph.morph(componentEl, data.html);
}