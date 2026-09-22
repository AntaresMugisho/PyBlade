<p align="center">
  <a href="https://pyblade.com"><img src="https://raw.githubusercontent.com/antaresmugisho/pybladedocs/main/public/images/pyblade.png" width="280" height="280" alt="PyBlade Logo"/></a>
</p>

<h1 align="center">PyBlade</h1>

<div align="center"> 

**_The reactive template engine for Python web frameworks._**

</div>

<div align="center">

  ![GitHub License](https://img.shields.io/github/license/antaresmugisho/pyblade)
  [![PyPI](https://img.shields.io/pypi/v/pyblade.svg?color=yellow)](https://pypi.org/project/pyblade/)
  [![Downloads](https://pepy.tech/badge/pyblade)](https://pepy.tech/project/pyblade)
  ![GitHub Stars](https://img.shields.io/github/stars/antaresmugisho/pyblade)

</div>

PyBlade is a lightweight, reactive template engine for Python. It brings reusable UI components and server-driven interactivity to your web apps using Python and HTML, without requiring a frontend framework.

> **Beta:** PyBlade is still experimental. APIs may change between releases and it is not yet recommended for production applications.

## Installation

Install PyBlade from PyPI:

```bash
pip install pyblade
```

PyBlade integrates into your existing Python web application rather than replacing your application framework.

## CLI

PyBlade includes a CLI for common development tasks:

```bash
pyblade init
pyblade serve
pyblade make:template
pyblade make:component
pyblade make:livecomponent
```

To see the available commands and options, run `pyblade --help` or `pyblade <COMMAND> --help`.

See the [CLI documentation](https://docs.pyblade.com/cli) for more details.


## Templates

PyBlade templates are regular `.html` files with additional syntax for layouts, conditions, loops, and components.

### Layouts

```html
@extends('layouts.base')

@block('content')
    <h1>Hello, {{ user.name }}!</h1>
@endblock
```

### Conditions

```html
@if(user.is_authenticated)
    <p>Welcome back, {{ user.name }}.</p>
@else
    <p>Please sign in.</p>
@endif
```

### Loops

```html
@for(post in posts)
    <article>
        <h2>{{ post.title }}</h2>
    </article>
@empty
    <p>No posts found.</p>
@endfor
```

### Components

Reusable components as well as live components can be rendered directly from templates:

```html
<pb-user-profile :user="user" />
```

They can also be invoked with the component directive:

```html
@component('user-profile', {'user': user})
```


## Framework Integration

PyBlade is designed to work with Python web frameworks and can be introduced into an existing application.

Only django is fully supported for now, we will add other frameworks support incrementally.

<!-- Framework-specific setup, configuration, and integration details are available in the [documentation](https://docs.pyblade.com/framework-integration). -->


## Editor Support

[PyBlade IntelliSense for VS Code](https://marketplace.visualstudio.com/items?itemName=antares.pyblade-intellisense) provides:

* Syntax highlighting
* Snippets
* Directive completion
* Component completion

Additional editor integrations are planned.


## Project Status

PyBlade is currently in beta.

The template engine, component system, CLI, Live Components, and framework integrations are actively evolving. APIs and conventions may change before the first stable release.

If you want to follow the project, report a bug, request a feature, or share feedback, visit the [GitHub repository](https://github.com/antaresmugisho/pyblade) or [PyBlade Feedback](https://feedback.pyblade.com).

## Contributing

Contributions are welcome, including bug reports, fixes, documentation, examples, editor tooling, and new ideas.

Before contributing, please read:

* [Contributing Guide](CONTRIBUTING.md)
* [Code of Conduct](CODE_OF_CONDUCT.md)
* [Security Policy](SECURITY.md)

You can also contribute to the wider PyBlade ecosystem:

- [PyBlade Documentation](https://github.com/AntaresMugisho/PyBladeDocs), the source for [docs.pyblade.com](https://docs.pyblade.com)

- [PyBlade IntelliSense for VS Code](https://github.com/antaresmugisho/pybladeintellisense-vscode)
- [PyBlade IntelliSense for Sublime Text](https://github.com/antaresmugisho/pybladeintellisense-sublime)
- [PyBlade IntelliSense for JetBrains IDEs](https://github.com/antaresmugisho/pybladeintellisense-jetbrains)
- [PyBlade IntelliSense for Atom](https://github.com/antaresmugisho/pybladeintellisense-atom)


If you discover a security vulnerability, please follow the [Security Policy](SECURITY.md) instead of opening a public issue.

## Acknowledgements

PyBlade's template syntax is inspired by [Laravel Blade](https://laravel.com/docs/blade), while its Live Components are inspired by [Livewire](https://livewire.laravel.com).

PyBlade builds on ideas and work from the Python, Django, and Laravel communities.

Special thanks to [Michael Dimchuk](https://github.com/michaeldimchuk) for graciously releasing the **PyBlade** name on PyPI for this project.

## License

PyBlade is licensed under the [BSD 3-Clause License](LICENSE).
