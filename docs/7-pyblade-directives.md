# PyBlade Directives

## If statements

PyBlade provides a set of intuitive and developer-friendly directives for conditional statements, allowing you to control the flow of your templates easily. These conditionals work similarly to Python’s `if`, `elif`, and `else` statements, making it simple to render content based on certain conditions.

### Using `@if`, `@elif`, and `@else`

To create conditional statements in PyBlade, use the `@if` directive followed by `@elif` and `@else` as needed. This structure is useful for checking various conditions and displaying content accordingly.

#### Example

Suppose you have a variable `status` that can hold values like `'active'`, `'pending'`, or `'inactive'`. You can display different messages based on the value of `status` using conditional statements:

```python
# In your Django view
def show_status(request):
    context = {'status': 'active'}
    return render(request, 'status', context)
```

```html
<!-- In status.pyblade -->
@if(status == 'active')
    <p>Your account is active.</p>
@elif (status == 'pending')
    <p>Your account is pending approval.</p>
@else
    <p>Your account is inactive.</p>
@endif
```

### Output

If `status` is `'active'`, the output will be:

```html
<p>Your account is active.</p>
```

If `status` is `'pending'`, the output will be:

```html
<p>Your account is pending approval.</p>
```

And if `status` is anything else, the output will be:

```html
<p>Your account is inactive.</p>
```

:::info
In PyBlade, you can use the `@if` directive alone, pair it with `@else`, or chain one condition with `@elif`, just like in Python. Do not forget to end your conditional statement with the `@endif` directive.
:::

:::warning Missing feature
Multiple condition chaining with `@elif` are not supported yet.
:::

### Using `@unless`

::: info Upcoming feature
This feature is not yet implemented but should be ready in the next version. This part of documentation is provided for informative purpose only.
:::


The `@unless` directive works as a negation of `@if`. It executes the block only if the condition evaluates to `False`. This is useful for cases where you want to check if a variable does **not** meet a specific condition.

#### Example

If you want to display a message when a user does not have admin privileges:

```python
# In your Django view
def check_admin(request):
    context = {'is_admin': False}
    return render(request, 'admin_check', context)
```

```html
<!-- In admin_check.pyblade -->
@unless (is_admin)
    <p>You do not have admin privileges.</p>
@endunless
```

#### Output

If `is_admin` is `False`, the output will be:

```html
<p>You do not have admin privileges.</p>
```

If `is_admin` is `True`, nothing will be displayed.

### Nested Conditionals

You can also nest conditionals to create more complex logic. However, be cautious with excessive nesting as it can make the template harder to read and maintain.

#### Example

```html
@if (user.is_authenticated)
    @if (user.is_admin)
        <p>Welcome, Admin {{ user.name }}!</p>
    @else
        <p>Welcome, {{ user.name }}!</p>
    @endif
@else
    <p>Please log in to continue.</p>
@endif
```

#### Output

If `user.is_authenticated` is `True` and `user.is_admin` is `True`, the output will be:

```html
<p>Welcome, Admin {{ user.name }}!</p>
```

If `user.is_authenticated` is `True` but `user.is_admin` is `False`, the output will be:

```html
<p>Welcome, {{ user.name }}!</p>
```

And if `user.is_authenticated` is `False`, the output will be:

```html
<p>Please log in to continue.</p>
```

In PyBlade, you can also use logical expressions such as `and`, `or`, and `not` within conditional statements, similar to Python. This allows you to combine multiple conditions in a single directive for more complex checks.

:::warning Warning: Keep logic out of templates
For performance and readability, avoid complex or time-consuming logic within conditional statements. Templates should primarily focus on displaying pre-processed data, not performing heavy logic. Keep calculations and condition checks within views or controllers wherever possible to adhere to the principle of "Logic in the code, templates are for display only."
:::


## Switch statements

::: info Upcoming feature
This feature is not yet implemented but should be ready in the next version. This part of documentation is provided for informative purpose only.
:::


PyBlade also provides support for `@switch` statements, which are useful for handling multiple conditions based on the value of a single variable. This can help simplify templates by reducing the need for multiple `@if`, `@elif`, and `@else` statements.

With `@switch`, you can check a variable's value and define multiple `@case` conditions. If none of the cases match, an optional `@default` can be specified as a fallback.

### Basic Syntax

The `@switch` directive takes a variable as its argument. Within the `@switch` block, each condition is checked using `@case`, and the code in the matching `@case` block will execute. If no cases match, the `@default` block will execute (if it is provided).

```html
@switch(variable)
    @case('value1')
        <!-- Code to display if variable == 'value1' -->
    @case('value2')
        <!-- Code to display if variable == 'value2' -->
    @default
        <!-- Code to display if none of the cases match -->
@endswitch
```

### Example

Suppose you have a variable `status` with possible values like `'active'`, `'pending'`, `'inactive'`, or others. You can use `@switch` to display different messages based on `status`:

```python
# In your Django view
def show_status(request):
    context = {'status': 'pending'}
    return render(request, 'status', context)
```

```html
<!-- In status.pyblade -->
@switch(status)
    @case('active')
        <p>Your account is active.</p>
    @case('pending')
        <p>Your account is pending approval.</p>
    @case('inactive')
        <p>Your account is inactive.</p>
    @default
        <p>Status unknown.</p>
@endswitch
```

#### Output

If `status` is `'pending'`, the output will be:

```html
<p>Your account is pending approval.</p>
```

If `status` has a value other than `'active'`, `'pending'`, or `'inactive'`, the output will be:

```html
<p>Status unknown.</p>
```

### Nested `@switch` Statements

Just like other conditional structures, `@switch` statements can be nested, though it’s best to keep templates as simple as possible to maintain readability.


## Loops

PyBlade supports looping through lists, dictionaries, and other iterable data structures using the `@for` directive. These loops are similar to Python’s `for` loops and make it easy to display repeated elements in your templates.


### `@for` loop example

If you have a list of items, you can use `@for` to loop through them:

```python
# In your Django view
def show_items(request):
    context = {'fruits': ['Apple', 'Banana', 'Cherry']}
    return render(request, 'my_app.index', context)
```

```html
<!-- In items.pyblade -->
<ul>
    @for (fruit in fruits)
        <li>{{ fruit }}</li>
    @endfor
</ul>
```

#### Output

```html
<ul>
    <li>Apple</li>
    <li>Banana</li>
    <li>Cherry</li>
</ul>
```

### The `@empty` directive

Somethimes, you may need to handle cases where a loop has no items to iterate over. That's why PyBlade provides an `@empty` directive that specifies a fallback to display content if the list or iterable is empty.

```python
# In your Django view
def show_fruits(request):
    context = {'fruits': []}  # An empty list of fruits
    return render(request, 'fruits', context)
```

```html
<!-- In fruits.pyblade -->
<ul>
    @for(fruit in fruits)
        <li>{{ fruit }}</li>
    @empty
        <li>No fruits available.</li>
    @endfor
</ul>
```

### Output

```html
<ul>
    <li>No fruits available.</li>
</ul>
```

Using `@empty` ensures that the template provides meaningful feedback in cases where a list or iterable is empty, improving user experience.

### Using the `loop` Variable

In addition, PyBlade provides a special `loop` variable inside each loop, giving you helpful information about the current iteration. This variable allows you to access details like the current index, whether it’s the first or last iteration, and more.

Here is a full list of available properties on the loop variable.


| Property         | Description|
| -------------    | ---------- |
| `loop.index`     | The index of the current loop iteration (starts at 0).|
| `loop.iteration` | The current loop iteration (starts at 1).|
| `loop.first`     | Whether this is the first iteration through the loop.|
| `loop.last`      | Whether this is the last iteration through the loop.|
| `loop.count`     | The total number of items in the iterable being iterated.|
| `loop.remaining` | The iterations remaining in the loop.|
| `loop.even`      | Whether this is an even iteration through the loop.|
| `loop.odd`       | Whether this is an odd iteration through the loop.|


#### Example with `loop` Variable

Let’s enhance the previous example to use the `loop` variable for displaying additional information about each item:

```html
<!-- In items.pyblade -->
<ul>
    @for(fruit in fruits)
        <li>
            @if(loop.first)
                First item:
            @elif(loop.last)
                Last item:
            @else
                Item {{ loop.iteration }} of {{ loop.count }}:
            @endif
            {{ item }}
        </li>
    @endfor
</ul>
```

#### Output

```html
<ul>
    <li>First item: Apple</li>
    <li>Item 2 of 3: Banana</li>
    <li>Last item: Cherry</li>
</ul>
```

::: warning Missing feature
Nested loops are not supported yet.
:::


### Skipping and ending loop iterations

::: info Upcoming feature
This feature is not yet implemented but should be ready in the next version. This part of documentation is provided for informative purpose only.
:::

In PyBlade, you can use the `@continue` directive to skip the current iteration and move on to the next one, or the `@break` directive to exit the loop entirely based on a condition.

#### Example with `@continue` and `@break`

Suppose you have a list of fruits, and you want to display each fruit's name but want to skip "Banana" and stop the loop entirely once you reach "Date."

```python
# In your Django view
def show_fruits(request):
    context = {'fruits': ['Apple', 'Banana', 'Cherry', 'Date', 'Elderberry']}
    return render(request, 'fruits', context)
```

```html
<!-- In fruits.pyblade -->
<ul>
    @for(fruit in fruits)
        @if(fruit == 'Banana')
            @continue
        @endif

        <li>{{ fruit }}</li>

        @if(fruit == 'Date')
            @break
        @endif
    @endfor
</ul>
```

#### Output

```html
<ul>
    <li>Apple</li>
    <li>Cherry</li>
</ul>
```

In this example:
- The `@continue` directive skips the iteration for "Banana," so "Banana" does not appear in the list.
- The `@break` directive stops the loop entirely when it reaches "Date," so "Elderberry" is not displayed.

### Simplified `@continue` and `@break` with Conditions

You can also include the condition directly within the `@continue` and `@break` directives to make your code more concise.

```html
<ul>
    @for fruit in fruits
        @continue(fruit == 'Banana')
        <li>{{ fruit }}</li>
        @break(fruit == 'Date')
    @endfor
</ul>
```

This has the same output as the previous example. By including the condition directly within the `@continue` and `@break` directives, you make the code shorter and clearer.

### Why the `@while` directive is missing in PyBlade ?

In PyBlade, we’ve chosen not to include a `@while` directive to encourage best practices in template design. While loops, if not carefully controlled, can introduce risks such as infinite loops, which can significantly impact performance and even cause server issues. Since templates should ideally focus on presenting data rather than complex logic or repeated condition-based iterations, we prioritize directives that maintain a clean separation between logic and presentation.

#### Recommended approach

Instead of a `@while` directive, we recommend:
- **Handling Loops in the View Layer**: Perform complex or condition-based iterations in the view or controller, passing the results to the template.
- **Using the `@for` Directive**: For most display needs, the `@for` directive is well-suited for iterating over collections, lists, or dictionaries, providing sufficient flexibility for typical use cases in templates.

#### Future considerations

If there is strong demand from the community and a clear use case for `@while`, we may consider adding it in future updates. However, we encourage users to leverage the view layer for more control over complex logic.

## Conditional Classes

The `@class` directive in PyBlade lets you conditionally apply CSS classes based on specific conditions. It accepts a dictionary where `keys` represent the class names and `values` are booleans or boolean expressions. If an expression evaluates to `True`, the associated class is applied.

#### Example

In this example, we apply the `list-item` class to each item and `favorite` class to items marked as a favorite:

```python
# In your Django view
def show_fruits(request):
    context = {
        'fruits': [
            {'name': 'Apple', 'is_favorite': True},
            {'name': 'Banana', 'is_favorite': False},
            {'name': 'Cherry', 'is_favorite': True},
        ]
    }
    return render(request, 'fruits', context)
```

```html
<!-- In fruits.pyblade -->
<ul>
    @for fruit in fruits
        <li @class({"list-item": True, "favorite": fruit.is_favorite})>{{ fruit.name }}</li>
    @endfor
</ul>
```

### Output

```html
<ul>
    <li class="list-item favorite">Apple</li>
    <li class="list-item">Banana</li>
    <li class="list-item favorite">Cherry</li>
</ul>
```

## Inline Styles

::: info Upcoming feature
This feature is not yet implemented but should be ready in the next version. This part of documentation is provided for informative purpose only.
:::

The `@style` directive works similarly to `@class`, but it controls inline CSS styles. It also takes a dictionary where keys are CSS properties, and values are booleans or expressions. When an expression evaluates to `True`, the associated style is applied to the element.

#### Example

Here, we set a red color for fruits that are not favorites:

```html
<ul>
    @for(fruit in fruits)
        <li @style({"color: red;": not fruit.is_favorite})>{{ fruit.name }}</li>
    @endfor
</ul>
```

#### Output

```html
<ul>
    <li>Apple</li>
    <li style="color: red;">Banana</li>
    <li>Cherry</li>
</ul>
```

## Including partials

In PyBlade, partials allow you to include smaller template sections within a template file. This modular approach is useful for reusing common components (e.g., headers, footers, or menus) across multiple templates, keeping your code organized and reducing redundancy.

### Where to Store Partials

Partials should be stored within a `partials` directory inside the main project `templates` folder.

```
my_project/
├── templates/
│   ├── partials/
│   │   ├── header.pyblade
│   |   └── base.pyblade
└── settings.py
```

### Including a partial

Use the `@include` directive to insert a partial within a template. The path to the partial is specified as a string, excluding the `.pyblade` extension and separating direcoties with dots (`.`).

```html
<!-- In base.pyblade -->
<!DOCTYPE html>
<html>
<head>
    @include("header")
</head>
<body>
    <main class="content">
        The main content goes here !
    </main>
    @include("footer")
</body>
</html>
```

### Customizing partial directory path

::: info Upcoming feature
This feature is not yet implemented but should be ready in the next version. This part of documentation is provided for informative purpose only.
:::


You can customize the location of partials by setting custom paths in the PyBlade **OPTIONS**. This provides flexibility if your project has a different structure or if you want to organize templates differently. Configuration settings will vary depending on your framework, but they typically involve updating the options in your PyBlade setup.

## Raw Python code

In PyBlade, the focus is on maintaining a clear separation between logic and presentation, which is why we've opted not to include raw Python code execution within templates. Although technically possible, embedding raw Python can quickly lead to complex, hard-to-maintain templates, reducing readability and performance.

However, we understand that in some cases, direct Python code might seem useful. If there is strong demand from the community, we would consider adding a `@python` directive. This directive could allow developers to execute Python code within templates, but we encourage handling complex logic in the view layer or controller instead.

For now, we recommend:
- **Using the View Layer for Logic** : Prepare all necessary data and pass it to the template from the view or controller. This keeps templates cleaner and focused on displaying information.
- **Leveraging PyBlade's Existing Directives**: Use PyBlade's conditional statements, loops, and directives like `@class` and `@style` for most template logic.

If you feel strongly about adding raw Python capabilities in PyBlade, please reach out! We are open to suggestions and would love to hear more about how this feature might help your projects.
