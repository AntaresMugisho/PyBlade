# PyBlade: Template Engine

## Introduction

PyBlade is a lightweight yet powerful template engine tailored for Python web applications. Unlike some templating engines, PyBlade keeps things simple while staying flexible, allowing you to use familiar Python syntax and expressions directly in your templates. Each PyBlade template is compiled into HTML code and cached to ensure optimal performance, meaning PyBlade adds virtually no overhead to your application. PyBlade templates use the `.pyblade` file extension and are typically stored within the `templates` directory of your app.

In Django or Flask applications, PyBlade views can be rendered directly within views or controllers, keeping data handling and template rendering clean and straightforward. Just pass the data you need as context, and PyBlade takes care of the rest, providing a seamless, Pythonic approach to building dynamic, secure web templates.

### Available Directives

1. **Conditionals and Logic:**
   - `@if`, `@elif`, `@else`, `@endif`
   - `@switch`, `@case`

2. **Auth and Guest:**
   - `@auth`, `@endauth`, `@guest`, `@endguest`

3. **Loops with Loop Variables:**
   - `@for`, `@endfor`, `@while`, `@endwhile`
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
<!-- components/button.blade.pyblade -->
@props(['label', 'type' => 'button'])

<button type="{{ type }}">{{ label }}</button>
```

This structure ensures default values and improves readability for the data passed into the component.

---
