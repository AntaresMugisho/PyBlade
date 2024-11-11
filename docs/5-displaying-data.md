# Displaying Data in PyBlade

In PyBlade, displaying data inside templates is straightforward and designed to feel intuitive for developers, especially those familiar with Blade from Laravel. To display variables, PyBlade uses the <span v-pre>`{{ }}`</span> syntax, which is both secure and simple to use.

Here's how you can display data in PyBlade templates:

## Basic variable display

To display a variable, simply wrap it within double curly braces <span v-pre>`{{ }}`</span>.

### Example

Assuming you have a variable named `name` passed to the template, you can display it like this:

```python
# In your rendiring view function
def show_greeting(request):
    context = {'name': 'John Doe'}
    return render(request, 'greeting.html', context)
```

```html
<!-- In greeting.pyblade -->
<p>Hello, {{ name }} !</p>
```

### Output
```html
<p>Hello, John Doe !</p>
```
---

When you insert data using this syntax, PyBlade will automatically escape the content to protect against XSS (Cross-Site Scripting) attacks. For cases where you need to output unescaped HTML, there is another syntax.

## Displaying unescaped HTML data

For data that includes HTML, such as `<strong>`, `<em>`, or custom HTML content, use `{!! !!}` to output the data without escaping. This is useful for displaying HTML content stored in your variables.

### Example

If a variable `message` contains HTML, such as `"<strong>Welcome back!</strong>"`, you can display it like this:

```python
# In your rendiring view function
def show_message(request):
    context = {'message': '<strong>Welcome back!</strong>'}
    return render(request, 'message.html', context)
```

```html
<!-- In message.pyblade -->
<p>{!! message !!}</p>
```

### Output
```html
<p><strong>Welcome back!</strong></p>
```

::: warning
Use `{!! !!}` with caution. Always ensure that the content is safe to display to avoid security risks.
:::

## Displaying data with default values

::: danger Upcoming feature
This feature is not yet implemented but should be ready in the next version. This part of documentation is provided for informative purpose only.
:::

In PyBlade, you can also define default values for variables. This is helpful in cases where the variable might not always be defined.

### Example

If you want to display `name`, but fallback to "Guest" if it’s undefined, you can use the following syntax:

```html
<p>Hello, {{ name or 'Guest' }} !</p>
```

If `name` is undefined, the output will be:

```html
<p>Hello, Guest !</p>
```

## Using methods on variables

In PyBlade, you can not only display variables but also call methods on them directly within the curly braces.

For example, if you have a string variable like `name`, you can use Python string methods such as `.upper()` or `.capitalize()` directly within <span v-pre>`{{ }}`</span> to transform the data before displaying it.

### Example

If `name` is a string variable, you can call `.upper()` to display it in uppercase:

```python
# In your rendiring view function
def show_greeting(request):
    context = {'name': 'Jane'}
    return render(request, 'greeting.html', context)
```

```html
<!-- In greeting.pyblade -->
<p>Hello, {{ name.upper() }} !</p>
```

### Output
```html
<p>Hello, JANE !</p>
```

This flexibility allows you to use any method that is available on the variable type (e.g., strings, lists, dictionaries), including custom methods if the variable is an object.


::: warning
Avoid using too many methods or computationally expensive operations within {{ }} in your templates. While PyBlade supports calling methods directly on variables, it’s best to keep these calls minimal and efficient. Overusing or relying on time-consuming methods can slow down rendering, impacting user experience.
:::

### Other useful examples

Here are a few more examples to illustrate the versatility of using methods directly in the template.

#### Capitalizing a String

If you want to capitalize only the first letter of `name`, you can use `.capitalize()`:

```html
<p>Welcome, {{ name.capitalize() }}!</p>
```

### Getting the length of a ist

If you have a list called `items`, you can display its length with `len()`:

```html
<p>You have {{ len(items) }} items in your list.</p>
```

#### Accessing Dictionary Keys

If `user` is a dictionary with a key `email`, you can access it like this:

```html
<p>Your email: {{ user.get('email') }}</p>
```

Using methods within curly braces allows for greater flexibility and keeps your template expressions clear and readable.

:::tip
For best performance and maintainability, follow the principle of “Logic in the code, templates are for display only.” Perform complex logic and data transformations in your views or controllers, passing only the final, display-ready data to your templates. This keeps templates focused solely on presentation, enhancing readability and performance.
:::
