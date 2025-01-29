# PyBlade

**PyBlade** is a lightweight, flexible, and efficient template engine for Python, inspired by Laravel's Blade syntax. It makes transitioning from Laravel to Django seamless by offering familiar features like components (inspired by **Laravel Livewire**) and a simple, intuitive syntax. Designed primarily for **Django** projects, PyBlade allows developers to create dynamic, interactive templates with ease, while maintaining robust security measures.

## Roadmap

- [x] Basic template rendering with variable interpolation
- [x] Support for conditionals and loops
- [x] Template inheritance, partials, and slots
- [x] Integration with Django
- [x] Components similar to Laravel Livewire
- [x] Security measures
- [ ] Full documentation

## Features

- **Familiar Blade-Like Syntax**: Intuitive `@`-based directives for conditions, loops, and variable interpolation.
- **Component Support**: Fully functional component system inspired by Laravel Livewire, enabling developers to create reusable, dynamic components with real-time interactivity.
- **Easy Django Integration**: A powerful alternative to Django's default templating engine, while maintaining seamless integration.
- **Lightweight and Fast**: Optimized for performance and simplicity.
- **Security-Focused**: Enhanced security features including:
  - Automatic escaping of variables
  - Safe expression evaluation
  - Protection against XSS attacks
  - CSRF protection for components
  - Secure attribute handling
- **Ideal for Laravel Developers**: Designed to help Laravel developers easily understand and adapt to Django's ecosystem.

## Documentation

Comprehensive documentation is available at [pyblade.vercel.app](https://pyblade.vercel.app), covering:
- Getting started guide
- Template syntax
- Component system
- Best practices
- API reference


## Installation

Install PyBlade via pip:

```bash
pip install pyblade
```

## File Extension

PyBlade uses the standard `.html` file extension for templates, making it compatible with existing web development tools and workflows while maintaining familiar syntax highlighting and editor features.


## IDE Support

### Available Now
- [**PyBlade IntelliSense**](https://marketplace.visualstudio.com/items?itemName=antares.pyblade-intellisense) in the VS Code marketplace with support of:
  - Syntax highlighting
  - Snippets
  - Auto-completion for directives and components

### Coming Soon
- **JetBrains IDEs** (PyCharm, WebStorm, etc.)
- **Sublime Text**
- **Atom**

## Basic Usage

```html
<!-- template.html -->
@extends('layouts.base')

@section('content')
    <h1>Welcome, {{ user.name }}!</h1>
    
    @if(posts)
        @for(post in posts)
            <article>
                <h2>{{ post.title }}</h2>
                <p>{{ post.content }}</p>
            </article>
        @endfor
    @else
        <p>No posts found.</p>
    @endif
    
    <!-- Interactive Component Example -->
    @component('like-button', post_id=post.id)
        <span>Like this post</span>
    @endcomponent
@endsection
```

## Security

At PyBlade, we take security seriously. The template engine will automatically escape output unless explicitly marked as safe. This helps protect against **Cross-Site Scripting (XSS)** and ensures that user-generated content is handled securely. Additional features, such as CSRF token support and other security best practices, will be incorporated to ensure that your Django applications remain secure.

## Contributing

Contributions are welcome! PyBlade is an open-source project, and we invite developers from both the Django and Laravel communities to collaborate. Please refer to the [Contributing Guide](docs/docs/CONTRIBUTING.md) for more information.

PyBlade is open source and welcomes contributions! Here's how you can help:

- **Core Development**: Visit our [PyBlade GitHub repository](https://github.com/antaresmugisho/pyblade)
- **IDE Extensions**: Help develop extensions for various editors
    - [PyBlade IntelliSense for VS Code](https://github.com/antaresmugisho/pybladeintellisense-vscode)
    - [PyBlade IntelliSense for Sublime Text](https://github.com/antaresmugisho/pybladeintellisense-sublime)
    - [PyBlade IntelliSense for JetBrains IDEs](https://github.com/antaresmugisho/pybladeintellisense-jetbrains)
    - [PyBlade IntelliSense for Atom](https://github.com/antaresmugisho/pybladeintellisense-atom)
- **Documentation**: Improve our docs from the [core repository](https://github.com/antaresmugisho/pyblade)
- **Bug Reports**: Submit issues on GitHub
- **Feature Requests**: Share your ideas through GitHub discussions


## License

This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- Inspired by Laravel's Blade template engine and Livewire components.
- Thanks to the Python, Django, and Laravel communities for their ongoing support of open-source projects.
- Special thanks to [Michael Dimchuk](https://github.com/michaeldimchuk) for graciously releasing the
name **PyBlade** on PyPI for this project. Your kindness and support for the open-source community are truly appreciated!

---
Let's bring the power of Blade-like templating and Livewire-like interactivity to Django ! 🚀
