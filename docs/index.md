# PyBlade Documentation

## What is PyBlade ?

PyBlade is a lightweight web template engine for Python, initially designed for Django. Inspired by Laravel's Blade and
Livewire, it simplifies dynamic template creation with developer-friendly @-based directives and component support, all while prioritizing security."

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation and Quick Start](#installation-and-quick-start)
3. [Configuration by Framework](#configuration-by-framework)
4. [PyBlade Template Engine](#pyblade-template-engine)
   - [Available Directives](#available-directives)
   - [Variable Rendering and XSS Prevention](#variable-rendering-and-xss-prevention)
   - [Comments](#comments)
5. [LiveBlade for Components](#liveblade-for-components)
6. [Future Features and Community Contributions](#future-features-and-community-contributions)
7. [Support and Contribution](#support-and-contribution)

---


## Introduction

### What is PyBlade ?

**PyBlade** is a lightweight, secure template engine for Python, designed to be both powerful and easy to use. Drawing
inspiration from Laravel's Blade, PyBlade allows developers to build expressive, secure templates using an intuitive `@`-based syntax. While many template engines focus on backend logic, PyBlade extends into component-driven development through LiveBlade, helping you create complex, reusable UI components that reduce reliance on backend rendering and enhance performance.

Developed with flexibility in mind, PyBlade is designed to integrate with various Python web frameworks, though it currently supports Django and Flask. Its flexible `.pyblade` file extension makes it easy to identify and work with PyBlade templates across your project. Whether you're a developer familiar with Blade or simply looking for a streamlined template engine, PyBlade offers a refreshing and secure approach to building dynamic applications.

### Why PyBlade?

In today’s fast-paced development environment, efficiency and security are essential. PyBlade addresses these needs by:

- **Simplicity and Speed**: PyBlade’s `@`-based directives are concise and intuitive, reducing the amount of boilerplate code you need to write. This streamlined approach enables developers to quickly build and iterate on templates, significantly improving development time and efficiency.

- **Component-Driven Design with LiveBlade**: With LiveBlade, PyBlade introduces a frontend-like component architecture. Inspired by modern frontend frameworks, LiveBlade enables you to create reusable components that handle both UI and logic. This approach reduces the load on server-side rendering, allowing components to manage dynamic interactions directly on the client side, enhancing the user experience and reducing server load.

- **Framework-Agnostic Design**: While PyBlade currently supports Django and Flask, its adaptable architecture is intended to work with multiple Python web frameworks. This framework-agnostic design ensures that you can easily integrate PyBlade into various projects, giving you the freedom to use it across different Python web applications as needed.

- **Security by Default**: PyBlade takes security seriously. By default, all variables rendered in templates are securely escaped to protect against common vulnerabilities like Cross-Site Scripting (XSS) attacks. For specific cases where unescaped output is essential, PyBlade provides dedicated syntax, ensuring that developers can easily distinguish safe and unsafe operations.

- **Python-Powered, Logic-First Design**: PyBlade templates execute as Python code, aligning well with Python’s syntax
and conventions. However, as with Django's best practices, the majority of business logic should remain in the backend, while templates should focus on presentation. This approach keeps templates clean, efficient, and aligned with the MVC (Model-View-Controller) architecture, promoting a clear separation of concerns.
- **Powerful and Expressive Template Logic**: PyBlade provides a range of directives for handling logic within templates, from basic conditionals and loops to complex components. This rich directive set reduces the need to process data in the controller, making backend code cleaner and templates more capable. PyBlade simplifies common tasks such as conditional rendering, looping, and error handling, so developers can focus on delivering features instead of managing template complexity.

### Who Should Use PyBlade?

PyBlade is built for developers who want to maximize efficiency and maintainability in their template code. It’s ideal for:

1. **Python Developers Seeking Simple and Secure Templating**: PyBlade’s `@`-based syntax enables developers to write expressive templates with minimal overhead, providing a secure and feature-rich templating experience.

2. **Laravel Developers Transitioning to Python**: If you’re familiar with Laravel’s Blade syntax, PyBlade provides a
   familiar development environment within Python, making it easier to build dynamic templates without learning a new template syntax.

3. **Projects That Benefit from Component-Based Frontend Behavior**: By leveraging LiveBlade, PyBlade empowers
   projects with a modern component-driven model similar to frontend frameworks, allowing you to create modular, self-contained UI pieces that reduce server rendering needs.

4. **Multi-Framework Projects**: Since PyBlade’s design is framework-agnostic, it’s well-suited for applications that
may span multiple Python web frameworks. Current support includes Django and Flask, with a straightforward setup process and the potential for further compatibility in the future.

### How PyBlade Accelerates Development

With its concise syntax and component-driven approach, PyBlade helps developers build applications faster by reducing the amount of code required to create robust templates. By focusing on `@`-based directives, PyBlade provides a less verbose, more readable syntax that makes templates easy to maintain and extend. Developers can move from idea to implementation more quickly, thanks to PyBlade’s intuitive directive system and streamlined component architecture.

### Simple Demo

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
- **Auto-Escaped Variables**: Variables such as `{{ title }}` and `{{ user.name }}` are automatically escaped to prevent XSS attacks, ensuring secure data handling.
- **Simple Conditionals**: Conditional statements like `@if`, `@else`, and `@endif` allow for flexible, secure content rendering.
- **Efficient Loops**: The `@for` directive makes it easy to loop through data collections, providing clear, readable code.

PyBlade’s flexibility, secure defaults, and intuitive syntax make it a powerful addition to your Python development toolkit, helping you create dynamic, responsive, and secure applications effortlessly.
