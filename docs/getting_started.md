
# Getting started

## Installation

To install PyBlade, simply use `pip`:

```bash
pip install pyblade
```
---

## Configuration

### Django Configuration

To use **PyBlade** with Django, first ensure your Django project is correctly set up. If not, please refer to the [Django documentation](https://docs.djangoproject.com/en/stable/) for instructions.

### 1. Install PyBlade

Install PyBlade using pip:

```bash
pip install pyblade
```

### 2. Configure PyBlade in Django Settings

In `settings.py`, add PyBlade as a template backend to enable Django to recognize and process PyBlade as the default
template engine.

```python
# settings.py
TEMPLATES = [
    {
        'BACKEND': 'pyblade.backends.DjangoPyBlade',  # Specify DjangoPyBlade as the backend
        'DIRS': [BASE_DIR.joinpath("templates")],     # Path to your templates directory
        'APP_DIRS': True,                             # Enables template loading for each app
        'OPTIONS': {
           # Optional configurations for pyblade
        }
    },
]
```

### 3. Rendering PyBlade Templates in Django Views

In  Django views, PyBlade templates should be referenced without the `.pyblade` extension, and folders should use
dots `.` instead of slashes `/` for separation. This is consistent with PyBlade’s template loading conventions.

For example, given the structure:
```
my_project/
├── my_app/
│   ├── views.py                # Django views file
│   ├── models.py               # Django models file
│   └── templates/
│       └── my_app/             # App-specific folder for templates
│           ├── index.pyblade   # Template for a view in `my_app`
│           └── about.pyblade   # Other template
└── settings.py

```
To reference `index.pyblade` within `my_app/templates/my_app/`, use the path `"my_app.index"` in your Django view, as follows:

```python
# views.py
from django.shortcuts import render

def home_view(request):
    context = {'title': 'Welcome to PyBlade', 'user': {'name': 'John Doe'}}
    return render(request, 'my_app.index', context)
```

This dot notation approach provides a clean way to reference templates across folders and is timeless consuming.

---

## Flask Configuration

PyBlade can also be easily configured for Flask, requiring only minimal setup.

### 1. Install PyBlade

Install PyBlade as follows:

```bash
pip install pyblade
```

### 2. Organize Your Template Files

Within your Flask project, create a `templates` folder if it doesn’t already exist, and place your `.pyblade` templates there:

```
my_flask_project/
├── app.py                  # Main Flask application file
└── templates/
    ├── index.pyblade       # PyBlade template file
    └── base.pyblade        # Optional base layout template
```

### 3. Rendering PyBlade Templates in Flask

In Flask, you can render PyBlade templates using `pyblade.render_template`. Like Django, reference the file without the `.pyblade` extension.

```python
# app.py
from flask import Flask
from pyblade import render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index', title='Welcome to PyBlade')
```

---

## Editor Support

To improve productivity when working with PyBlade, **PyBlade Intellisense** offers editor support for popular editors, including **VSCode, Sublime Text, and JetBrains Editors**. These extensions provide:

- **Syntax Highlighting** for `.pyblade` files.
- **Intellisense and Code Completion** for PyBlade directives and syntax.
- **Snippets** for commonly used template structures.
- **Error Checking** to catch syntax issues in `.pyblade` files.

You can install **PyBlade Intellisense** extensions from your editor’s marketplace, enabling you to work seamlessly with PyBlade templates.

---

## Best Practices and Tips

Here are some best practices and tips to maximize efficiency and maintain clean code when using PyBlade:

- **Keep Logic in the Backend**: Like Django’s templating philosophy, avoid adding business logic in templates. Use PyBlade directives to simplify rendering, but keep calculations, data processing, and complex logic in your views or controllers.
- **Organize Templates by Feature**: Create subdirectories within `templates` for different sections of your app. This structure keeps templates maintainable, especially in large applications.
- **Escape Variables by Default**: By default, PyBlade escapes variables to protect against XSS attacks. Use `{!! var !!}` only when you’re certain the content is safe and does not require escaping.
- **Use PyBlade’s Components for Modular Code**: Components let you create reusable template sections, improving maintainability and reducing repetition across your templates.
- **Editor Extensions**: To speed up development, install PyBlade Intellisense for editor support, especially useful for `.pyblade` syntax, autocomplete, and debugging.

These best practices will help you develop faster with PyBlade while maintaining code security, clarity, and efficiency across Django and Flask projects.

## 4. PyBlade Template Engine

PyBlade includes various `@`-based directives, providing robust support for conditionals, loops, error handling, and more.

### Available Directives

1. **Conditionals and Logic:**
   - `@if`, `@elif`, `@else`, `@endif`
   - `@switch`, `@case`

2. **Auth and Guest:**
   - `@auth`, `@endauth`, `@guest`, `@endguest`

3. **Loops with Loop Variables:**
   - `@for`, `@endfor`, `@foreach`, `@endforeach`, `@while`, `@endwhile`
   - `@break`, `@continue`

    PyBlade provides a `loop` variable with properties in `@foreach` and `@for` loops:
   - `loop.index`: Current iteration (1-based).
   - `loop.index0`: Current iteration (0-based).
   - `loop.remaining`: Remaining iterations.
   - `loop.count`: Total number of iterations.
   - `loop.first`: True if this is the first iteration.
   - `loop.last`: True if this is the last iteration.

    ```html
    @foreach items as item
        <p>{{ item }} - Loop index: {{ loop.index }}</p>
        @if loop.last
            <p>This is the last item.</p>
        @endif
    @endforeach
    ```

4. **Form and Error Handling:**
   - `@csrf`, `@method`
   - `@error`: Checks if a form input has an error and sets a message variable within it.

    ```html
    <form method="POST">
        @csrf
        <input type="text" name="username">
        @error('username')
            <p class="error">{{ message }}</p>
        @enderror
    </form>
    ```

5. **HTML Attributes:**
   - `@class`, `@checked`, `@selected`, `@active`

6. **Template Structure:**
   - `@extends`, `@include`, `@yield`, `@section`, `@endsection`, `@block`

7. **URLs and Assets:**
   - `@static`, `@url`

8. **Python Code Execution:**
   - `@python`

---

### Variable Rendering and XSS Prevention

To prevent XSS attacks, PyBlade automatically escapes all variables rendered using `{{ variable }}` syntax. This ensures that any untrusted user input is sanitized, preventing potential JavaScript injection attacks.

If you need to render a variable unescaped, you can use the `{!! variable !!}` syntax. **Use this with caution**, as it bypasses XSS protection and should only be used with trusted content.

```html
<p>{{ user.name }} - Escaped</p>
<p>{!! user.raw_html !!} - Unescaped</p>
```

---

### Comments

Use `{# ... #}` for comments within templates. Content inside these comment blocks will not appear in the final rendered HTML output.

```html
{# This is a comment and will not be rendered #}
<p>Visible Content</p>
```

---

## 5. LiveBlade for Components

LiveBlade is PyBlade's component system, allowing developers to build reusable UI blocks with data and logic encapsulation.

### Defining a Component Class

1. **Define the Component Class:**

    ```python
    # components/button.py
    class Button:
        def __init__(self, label):
            self.label = label
    ```

2. **Use the Component in Template:**

   ```html
   @component('components.button', ['label' => 'Click Me'])
   @endcomponent
   ```

### Inline Components

PyBlade supports inline components using a self-closing HTML-like syntax:

```html
<b-button :label="'Click Me'" :type="'submit'"/>
```

This syntax allows setting attributes directly, making components cleaner and easier to use in templates.

### Props Directive in Inline Components

Within the component template, you can use the `@props` directive to define which props the component should receive:

```html
<!-- components/button.blade.html -->
@props(['label', 'type' => 'button'])

<button type="{{ type }}">{{ label }}</button>
```

This structure ensures default values and improves readability for the data passed into the component.

---

## 6. Future Features and Community Contributions

As PyBlade continues to grow, a few key directions for development are in consideration:

1. **Feature Suggestions**: While PyBlade currently lacks a system for custom directives, community suggestions for new built-in directives are highly encouraged and will be considered as PyBlade evolves.

2. **PyBlade Intellisense**: A planned extension, **PyBlade Intellisense**, will support syntax highlighting, autocompletion, and error checking in the four most popular code editors. This single, centralized extension will simplify PyBlade development across editors and serve as a base for the community to contribute.

3. **Extending PyBlade from Core Repository**: To keep contributions manageable and cohesive, any additional features should ideally extend from the official PyBlade repository rather than creating independent versions. This ensures continuity and ease of maintenance as the project matures.

---

## 7. Support and Contribution

For questions or to report issues, see the [Code of Conduct](#). Contributions are welcome! Please consider contributing to the PyBlade Intellisense project and helping improve the extension for the broader community.

---

This documentation now includes the latest information on future plans, highlighting how the community can shape PyBlade through official channels rather than separate forks, ensuring consistency and quality in the ecosystem.
