# PyBlade Documentation
----

# Getting started

## Installation

To install PyBlade, simply use `pip`:

```bash
pip install pyblade
```
---

::: danger ⚠️ Warning: Experimental Feature
PyBlade is currently in experimental mode. While we are actively developing and testing its features, please be aware that it may contain bugs or incomplete functionality. We recommend using PyBlade exclusively in test environments or with caution in production settings.

Your feedback is invaluable as we work toward a stable release. Thank you for helping us improve PyBlade!
:::

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
    └── about.pyblade        # Optional base layout template
```

It is important to exactly name this folder `templates` in Flask.

### 3. Rendering PyBlade Templates in Flask

In Flask, you can render PyBlade templates using `pyblade.render`. Like in Django, reference the file without the `.pyblade` extension.

```python
# app.py
from flask import Flask
from pyblade import render

app = Flask(__name__)

@app.route('/')
def home():
    return render('index', {'title': 'Welcome to PyBlade', 'user': {'name': 'John Doe'}})
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
- **Use PyBlade’s Components for Modular Code**: Components let you create reusable template sections, improving maintainability and reducing repetition across your templates.
- **Editor Extensions**: To speed up development, install PyBlade Intellisense for editor support, especially useful for `.pyblade` syntax, autocomplete, and debugging.

These best practices will help you develop faster with PyBlade while maintaining code security, clarity, and
efficiency across your Python web projects.


## What’s Next?

Now that you've successfully configured PyBlade for your Django or Flask project, you're ready to dive deeper into the core of PyBlade—its powerful directives and features. PyBlade isn’t just a template engine; it’s designed to streamline your workflow by offering a clean, expressive syntax that makes writing dynamic templates faster and more intuitive.

Here’s what you can explore next to unlock the full potential of PyBlade:

#### 1. **Learn the PyBlade Directives**
   PyBlade provides a rich set of directives that can help you add logic and interactivity to your templates, all while keeping the code simple and readable. In the next section, we’ll cover how to use conditional statements (`@if`, `@else`, `@elif`, `@switch`), loops (`@for`, `@while`), and much more. These directives will allow you to control the flow of your templates in a way that’s both powerful and easy to follow.

#### 2. **Explore Component-based Templates with LiveBlade**
   With PyBlade’s LiveBlade integration, you can create reusable components that can be updated dynamically—without requiring server-side rendering. This is ideal for situations where you want to reduce the load on your server or make your frontend more interactive. You can start by learning how to create inline components and use the `@props` directive to pass data to components seamlessly.

#### 3. **Boost Productivity with Editor Extensions**
   PyBlade makes your development experience even better with editor extensions for popular IDEs like VSCode, Sublime Text, and JetBrains. These extensions bring intelligent code completion, snippets, syntax highlighting, and more to `.pyblade` files. This ensures you can write PyBlade templates with ease and confidence, reducing the time spent on looking up syntax and improving your overall workflow.

Once you have a good grasp of the basics, you’ll be able to fully leverage the power of PyBlade to create beautiful, dynamic templates that integrate seamlessly with your Django or Flask backend. So, get ready to explore the power of PyBlade’s directives, and start building more efficient and maintainable web applications today!
