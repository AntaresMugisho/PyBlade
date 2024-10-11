# PyBlade

**PyBlade** is an upcoming lightweight, flexible, and efficient template engine for Python, inspired by Laravel's Blade syntax. It aims to make transitioning from Laravel to Django seamless by offering familiar features like components (inspired by **Laravel Livewire**) and a simple, intuitive syntax. Designed primarily for **Django** projects, PyBlade will allow developers to create dynamic, interactive templates with ease, while keeping **security** at the forefront.

## Features (Planned)

- **Familiar Blade-Like Syntax**: Intuitive `@`-based directives for conditions, loops, and variable interpolation.
- **Component Support**: Inspired by Laravel Livewire, PyBlade will offer component-based templating, allowing developers to create reusable, dynamic components directly within their Django templates.
- **Easy Django Integration**: Aims to be a powerful alternative to Django's default templating engine, while staying easy to integrate.
- **Lightweight and Fast**: Focus on performance and simplicity.
- **Security-Focused**: PyBlade will prioritize security by providing automatic escaping of variables and safe handling of user-generated content to protect against XSS and other common web vulnerabilities.
- **Ideal for Laravel Developers**: PyBlade is designed to help Laravel developers easily understand and adapt to Django’s ecosystem.

## Custom Template Extension

PyBlade will use a custom template file extension (`.pyblade`) to facilitate the development of extensions for text editors. This allows for enhanced features such as:

- **Snippets**: Quickly insert common patterns in your templates.
- **IntelliSense**: Get suggestions and completions as you type.
- **Syntax Highlighting**: Color-coded syntax for better readability.
- **Auto-Completion**: Automatically complete directives and component names.
- **Additional Extensions**: The ability for developers to create their own extensions for various text editors.

We aim to provide support for popular text editors such as Visual Studio Code, Sublime Text, Atom and JetBrains IDEs.
Extensions will be developed to improve usability in these environments.

## Status

**PyBlade** is currently in development and not ready for production use. Key features are still being built, but the project will soon allow developers to experiment with Blade-like templating in Django.

## Installation

Once released, you will be able to install PyBlade via pip:

```bash
pip install pyblade
```

## Usage (Coming Soon)

The usage instructions, including setup and examples for components and directives, will be available once the core features are implemented.

## Security

At PyBlade, we take security seriously. The template engine will automatically escape output unless explicitly marked as safe. This helps protect against **Cross-Site Scripting (XSS)** and ensures that user-generated content is handled securely. Additional features, such as CSRF token support and other security best practices, will be incorporated to ensure that your Django applications remain secure.

## Contributing

Contributions are welcome! PyBlade is an open-source project, and we invite developers from both the Django and Laravel communities to collaborate. Please refer to the [Contributing Guide](CONTRIBUTING.md) for more information.

## Roadmap

- [x] Basic template rendering with variable interpolation
- [ ] Support for conditionals and loops
- [ ] Template inheritance, partials, and slots
- [ ] Components similar to Laravel Livewire
- [ ] Security measures like automatic output escaping
- [ ] Integration with Django
- [ ] Full documentation

## License

This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- Inspired by Laravel's Blade template engine and Livewire components.
- Thanks to the Python, Django, and Laravel communities for their ongoing support of open-source projects.
That's a great idea! Here’s a suggestion for how you might word the credit in your README file:
- Special thanks to [Michael Dimchuk](https://github.com/michaeldimchuk) for graciously releasing the 
name **PyBlade** on PyPI for this project. Your kindness and support for the open-source community are truly appreciated!

---
Let's bring the power of Blade-like templating and Livewire-like interactivity to Django ! 🚀