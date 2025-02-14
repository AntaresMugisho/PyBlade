# LiveBlade Documentation

LiveBlade est un framework de composants réactifs pour Django, inspiré par Laravel Livewire. Il permet de créer des interfaces utilisateur dynamiques avec peu de JavaScript, en utilisant principalement du code Python.

## Table des matières
- [Installation](#installation)
- [Composants de base](#composants-de-base)
- [Directives](#directives)
- [État et Réactivité](#état-et-réactivité)
- [Cache et Performance](#cache-et-performance)
- [Traitement par lots](#traitement-par-lots)
- [Exemples complets](#exemples-complets)

## Installation

```bash
pip install pyblade
```

Ajoutez 'liveblade' à vos INSTALLED_APPS dans settings.py :
```python
INSTALLED_APPS = [
    ...
    'liveblade',
]
```

## Composants de base

### Création d'un composant

```python
# components/counter.py
from liveblade.base import Component, computed

class Counter(Component):
    def __init__(self, name):
        # Définir les propriétés réactives
        self.count = 0
        self.message = "Compteur"
        super().__init__(name)
    
    @computed
    def double_count(self):
        return self.count * 2
    
    def increment(self):
        self.count += 1
        return self.render()
    
    def render(self):
        return f"""
        <div>
            <h2>{self.message}: {self.count}</h2>
            <p>Double: {self.double_count}</p>
            <button b-click="increment">+1</button>
        </div>
        """
```

### Utilisation dans le template

```html
<div liveblade_id="counter">
    {{ component.render }}
</div>
```

## Directives

### b-text
Affiche du texte dynamique.
```html
<span b-text="message"></span>
```

### b-model
Liaison bidirectionnelle des données.
```html
<input b-model="username">
<p>Bonjour, <span b-text="username"></span>!</p>
```

### b-click
Gestion des événements de clic.
```html
<button b-click="increment">+1</button>
```

### b-loading
Gestion des états de chargement.
```html
<div b-loading>Chargement en cours...</div>
```

### b-error
Affichage des erreurs avec auto-hide.
```html
<div b-error b-error.auto-hide>Une erreur s'est produite</div>
```

### b-lazy
Chargement paresseux des composants.
```html
<div b-lazy="HeavyComponent">
    <!-- Le composant sera chargé quand visible -->
</div>
```

## État et Réactivité

### Propriétés réactives

```python
class ProductList(Component):
    def __init__(self, name):
        self.items = [
            {'price': 10, 'quantity': 2},
            {'price': 20, 'quantity': 1}
        ]
        super().__init__(name)
        
        # Ajouter un watcher
        self.watch('items', self._on_items_change)
    
    @computed
    def total(self):
        return sum(item['price'] * item['quantity'] for item in self.items)
    
    def _on_items_change(self, new_value, old_value):
        print(f"Items updated: {new_value}")
```

### Watchers

```python
class FormComponent(Component):
    def __init__(self, name):
        self.email = ''
        self.error = ''
        super().__init__(name)
        
        # Réagir aux changements d'email
        self.watch('email', self._validate_email)
    
    def _validate_email(self, new_value, old_value):
        if '@' not in new_value:
            self.error = 'Email invalide'
        else:
            self.error = ''
```

## Cache et Performance

### Mise en cache des méthodes

```python
class ExpensiveComponent(Component):
    @cached_blade(timeout=300)  # Cache pour 5 minutes
    def fetch_data(self):
        # Opération coûteuse
        return self.heavy_computation()
```

### Exemple de sortie avec cache :
```json
{
    "html": "<div>Données calculées</div>",
    "cached": true
}
```

## Traitement par lots

### Configuration du composant

```python
class BatchComponent(Component):
    def update_multiple(self, params):
        # Cette méthode sera exécutée en batch
        return self.process_updates(params)
```

### Template avec batch

```html
<button b-click="update_multiple" b-click.batch>
    Update Multiple
</button>
```

### Exemple de sortie batch :
```json
{
    "batch_results": [
        {
            "success": true,
            "component": "batch-component",
            "method": "update_multiple",
            "result": "<div>Updated content</div>"
        }
    ]
}
```

## Exemples complets

### Liste de tâches interactive

```python
class TodoList(Component):
    def __init__(self, name):
        self.todos = []
        self.new_todo = ''
        super().__init__(name)
    
    @computed
    def incomplete_count(self):
        return len([t for t in self.todos if not t['completed']])
    
    def add_todo(self):
        if self.new_todo:
            self.todos.append({
                'text': self.new_todo,
                'completed': False
            })
            self.new_todo = ''
        return self.render()
    
    def toggle_todo(self, params):
        index = int(params.get('index'))
        self.todos[index]['completed'] = not self.todos[index]['completed']
        return self.render()
    
    def render(self):
        return f"""
        <div class="todo-list">
            <h2>Todo List ({self.incomplete_count} remaining)</h2>
            
            <div class="add-todo">
                <input b-model="new_todo" placeholder="New todo">
                <button b-click="add_todo">Add</button>
            </div>
            
            <div b-loading>Loading...</div>
            
            <ul>
                {''.join(f'''
                    <li class="{'completed' if todo['completed'] else ''}">
                        <input type="checkbox" 
                               b-click="toggle_todo"
                               b-click.params="{{'index': {i}}}"
                               {'checked' if todo['completed'] else ''}>
                        {todo['text']}
                    </li>
                ''' for i, todo in enumerate(self.todos))}
            </ul>
        </div>
        """
```

### Utilisation dans le template Django

```html
{% extends 'base.html' %}

{% block content %}
<div liveblade_id="todo-list">
    {{ component.render }}
</div>

<style>
.todo-list {
    max-width: 500px;
    margin: 2rem auto;
}

.completed {
    text-decoration: line-through;
    color: #888;
}

.add-todo {
    margin: 1rem 0;
    display: flex;
    gap: 1rem;
}

[b-loading] {
    display: none;
    color: #666;
    font-style: italic;
}
</style>
{% endblock %}
```

## Bonnes pratiques

1. **Gestion d'état**
   - Utilisez `self.state` pour toutes les données réactives
   - Préférez les propriétés calculées aux méthodes pour les valeurs dérivées
   - Utilisez les watchers pour les effets secondaires

2. **Performance**
   - Utilisez `b-lazy` pour les composants lourds
   - Mettez en cache les opérations coûteuses avec `@cached_blade`
   - Utilisez le traitement par lots pour les mises à jour multiples

3. **UX**
   - Ajoutez toujours des indicateurs de chargement avec `b-loading`
   - Gérez les erreurs avec `b-error`
   - Utilisez les modificateurs appropriés (`.debounce`, `.throttle`) pour les événements fréquents

## Dépannage

### Problèmes courants

1. **Le composant ne se met pas à jour**
   - Vérifiez que vous utilisez `self.state.set()` pour modifier l'état
   - Assurez-vous que la méthode retourne `self.render()`

2. **Les propriétés calculées ne se mettent pas à jour**
   - Vérifiez que toutes les dépendances sont accédées via `state.get()`
   - Assurez-vous que les dépendances sont correctement définies

3. **Problèmes de performance**
   - Utilisez le mode debug pour identifier les goulots d'étranglement
   - Vérifiez l'utilisation appropriée du cache
   - Considérez le traitement par lots pour les opérations multiples
