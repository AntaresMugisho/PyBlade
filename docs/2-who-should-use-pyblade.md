
# Who should use PyBlade?

::: danger ⚠️ Warning: Experimental Feature
PyBlade is currently in experimental mode. While we are actively developing and testing its features, please be aware that it may contain bugs or incomplete functionality. We recommend using PyBlade exclusively in test environments or with caution in production environments.

Your feedback is invaluable as we work toward a stable release. Thank you for helping us improve PyBlade!
:::


PyBlade is built for developers who want to maximize efficiency and maintainability in their template code. It’s ideal for:

1. **Python Developers Seeking Simple and Secure Templating**: PyBlade’s `@`-based syntax enables developers to write expressive templates with minimal overhead, providing a secure and feature-rich templating experience.

2. **Laravel Developers Transitioning to Python**: If you’re familiar with Laravel’s Blade syntax, PyBlade provides a
   familiar development environment within Python, making it easier to build dynamic templates without learning a new template syntax.

3. **Projects That Benefit from Component-Based Frontend Behavior**: By leveraging LiveBlade, PyBlade empowers
   projects with a modern component-driven model similar to frontend frameworks, allowing you to create modular, self-contained UI pieces that reduce server rendering needs.

4. **Multi-Framework Projects**: Since PyBlade’s design is framework-agnostic, it’s well-suited for applications that
may span multiple Python web frameworks. Current support includes Django and Flask, with a straightforward setup process and the potential for further compatibility in the future.


## Simple Demo

To get a quick glimpse of PyBlade’s capabilities, here’s an example template:

**Template File (`example.pyblade`):**


```html
<!DOCTYPE html>
<html lang="en">
<head>
    <title>{{ title }}</title>
</head>
<body>
    <h1>Welcome, {{ user.name }}!</h1>

    @if (user.is_authenticated)
        <p>You're logged in!</p>
    @else
        <p>Please log in to access more features.</p>
    @endif

    @for (post in posts)
        <article>
            <h2>{{ post.title }}</h2>
            <p>{{ post.content }}</p>
        </article>
    @endfor
</body>
</html>
```


In this example:
- **Auto-Escaped Variables**: Variables such as <span v-pre>`{{ title }}` and `{{ user.name }}`  </span> are automatically escaped to prevent XSS attacks, ensuring secure data handling.

- **Simple Conditionals**: Conditional statements like `@if`, `@else`, and `@endif` allow for flexible, secure content rendering.

- **Efficient Loops**: The `@for` directive makes it easy to loop through data collections, providing clear, readable pythonic code.

PyBlade’s flexibility, secure defaults, and intuitive syntax make it a powerful addition to your Python development toolkit, helping you create dynamic, responsive, and secure applications effortlessly.

Check out the documentation for the [full list of PyBlade features](/3-getting-started).
