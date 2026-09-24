# Contributing

Thank you for wanting to contribute to PyBlade! Every contribution counts: a bug report, a fix, a
test, a clearer sentence in the docs, an example, an idea.

If you're new to open source, GitHub's
[How to Contribute to Open Source](https://opensource.guide/how-to-contribute/) explains how
contributing works, from finding a project to opening your first pull request. It is well worth a
read before you start.

By taking part in PyBlade, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Finding ways to help

- **Report a bug.** Open an issue with the smallest template or component that reproduces it, what
  you expected, and what happened instead. Include your versions of PyBlade, Python and your web
  framework.
- **Fix a bug.** Issues labeled `bug` and `good first issue` are good places to start. Comment on
  the issue to say you're working on it, so that two people don't do the same work.dpoint that builds a component verifies the signed snapshot first and is wrapped in @throttled, as update_component and upload_file are. An endpoint that serves a file checks a signed note, as preview_upload does.
In production, an error's message never reaches the browser, except a PermissionError, which is a refusal meant for the user.
- **Improve the documentation.** The docs live in their own repository,
  [PyBladeDocs](https://github.com/AntaresMugisho/PyBladeDocs), included here as the `docs`
  submodule. A fix for a confusing sentence is as welcome as a new page.
- **Propose a feature.** Open an issue or a discussion **before** writing the code. PyBlade follows
  Blade and Livewire closely, and a feature has to fit with the rest of the framework: talking it
  through first saves you work that could not be merged.
- **Share feedback** on [feedback.pyblade.com](https://feedback.pyblade.com), the portal for
  PyBlade and every product around it, such as the IDE extensions.

Security issues are the exception: **never** report them in a public issue. See
[SECURITY.md](SECURITY.md).

## Use of AI

You may use AI tools to help you contribute, but you are the author of what you submit:

- understand every line of your pull request, and be ready to explain and change it,
- run the tests yourself, and say in the pull request how you checked your change,
- don't submit issues, reviews or pull requests generated without your own review.

Pull requests that look generated and unreviewed will be closed. Agents working in this repository
also follow [AGENTS.md](AGENTS.md).

## Setup

PyBlade needs Python 3.10 or newer. Development uses [uv](https://docs.astral.sh/uv/):

```console
$ git clone git@github.com:antaresmugisho/pyblade.git
$ cd pyblade
$ uv sync
$ uv run pre-commit install
```

`uv sync` installs PyBlade in editable mode, with the development dependencies. Run Python commands
through `uv run` (or the Makefile), and add dependencies with `uv add` (`uv add --dev` for
development tools), committing `pyproject.toml` and `uv.lock` together.

The client side of live components is JavaScript. You need [Node.js](https://nodejs.org) 22 or
newer, whose built-in test runner runs the JavaScript tests, and [esbuild](https://esbuild.github.io)
to build the bundle:

```console
$ bun add --global esbuild
```

## Commands

The Makefile holds the commands you'll use day to day:

| Command           | What it does                                                   |
| ----------------- | -------------------------------------------------------------- |
| `make test`       | Runs the whole test suite, Python and JavaScript               |
| `make test-py`    | Runs the Python tests: the engine and the live server side     |
| `make test-js`    | Runs the JavaScript tests: the live components' client         |
| `make build-js`   | Builds the browser bundle once                                 |
| `make watch-js`   | Rebuilds the bundle on every change while you work             |
| `make pre-commit` | Runs the formatting and linting hooks on the whole repository  |

## Testing

While you work, run the tests closest to your change, then `make test` before you open a pull
request:

```console
$ uv run pytest tests/engine/test_components.py
$ uv run pytest tests/live/test_validation.py -k "email"
$ node --test tests/live/test_navigate.mjs
```

- **Every change comes with tests.** A bug fix starts with a test that fails without it: run it
  once before the fix to see it fail.
- **Match the tests around yours.** Follow the nearest test module: its fixtures, its docstrings,
  its naming. Test names read as sentences, such as `test_a_method_is_refused`.
- **Keep module names unique.** Test module basenames must differ across `tests/engine/` and
  `tests/live/`, because pytest refuses to collect two modules with the same name.
- **Use real objects.** Django is configured once for the whole suite in `tests/conftest.py`. Use
  what Django provides (`RequestFactory`, `override_settings`, `SimpleUploadedFile`) and real
  components rather than mocks, and never replace a module in `sys.modules`: it leaks into every
  other test of the run.
- **Test what the user sees.** Prefer rendering a template and checking the output over checking an
  internal function.

### JavaScript tests

The JavaScript tests run in Node, without a DOM. They exercise the client's decisions (which
scripts run, what `$pb` sends) with small fake objects. Code that touches the DOM must therefore
cope with those fakes, or with no `document` at all. DOM behavior itself is checked in a real
browser.

### The JavaScript bundle

The browser loads `pyblade/live/static/pyblade.min.js`, built from the modules in
`pyblade/live/static/src/`, not the modules themselves. After changing any of them, run
`make build-js` (or keep `make watch-js` running) and commit the bundle along with your change.

### Trying a change in a real project

The unit tests cover the engine, but not everything a browser does: layouts, navigation, morphing
the page. For a change to live components, try it in a Django project too, with your clone
installed in editable mode so that your changes apply without reinstalling:

```console
$ uv add --editable /path/to/your/pyblade     # if the project uses uv
$ pip install -e /path/to/your/pyblade         # otherwise
```

## Formatting and linting

PyBlade is formatted and linted with [Ruff](https://docs.astral.sh/ruff/), with lines up to 120
characters. It does the work Black, isort and Flake8 used to do between them, and it is configured
under `[tool.ruff]` in `pyproject.toml`: the rules selected there are pyflakes, pycodestyle and
import order, so what is checked is what was checked before.

The pre-commit hooks run it on every commit; `make pre-commit` runs it on the whole repository, and
it must pass before you open a pull request. `ruff check` fixes what it can on its own, and
`ruff format` rewrites the files it needs to, so a run that reports changes has already made them:
look at what it did and run it again.

## Project structure

| Path                           | What it holds                                                                            |
| ------------------------------ | ---------------------------------------------------------------------------------------- |
| `pyblade/engine/`              | The template engine: lexer, parser, nodes, expression sandbox, loader and render cache   |
| `pyblade/live/`                | Live components: `LiveComponent`, the endpoints, uploads, pagination, rate limits        |
| `pyblade/live/static/src/`     | The live components' client, in plain JavaScript modules                                 |
| `pyblade/backends/`            | Integrations with web frameworks                                                         |
| `pyblade/cli/`                 | The `pyblade` command line                                                               |
| `tests/engine/`, `tests/live/` | The tests, split the same way                                                            |

Configuration is read through `pyblade.config.config`, from a project's `pyblade.toml` or the
`[tool.pyblade]` table of its `pyproject.toml`. Its tables are `[project]`, `[stack]`, `[paths]`,
`[live]` and `[i18n]`, reached by name: `config.paths.templates`, `config.i18n.locale`. Every key
has a default in `pyblade/config.py`, so add one there before reading it anywhere else, and a key
that names a place on disk comes back as a `Path`.

A Django project may also write a `PYBLADE` dictionary in its settings, which wins over the file.
PyBlade reads it only once Django is configured and reads it again until then, because PyBlade is
imported well before `django.setup()` runs. Never read a framework's settings at import time.

In a test, say something different with the context manager rather than by reaching inside:

```python
with config.override({"paths.templates": str(tmp_dir)}):
    ...
```

## Writing code

- **Follow the code around yours.** Match its naming, its structure and how much it comments.
- **Comments explain why**, in full sentences: what a piece of code is for, and why it is done this
  way rather than the obvious way. The code already says what it does. Don't write history into
  comments ("changed from X", "fixed the bug where"): that belongs in the commit message.
- **Keep changes focused.** A pull request does one thing. Refactoring, reformatting or renaming
  unrelated code belongs in a pull request of its own.
- **Update the documentation** when you change behavior. Document a new feature in the existing
  page where a reader would look for it rather than adding a page, and check that every name used
  in an example exists in the code as it is.

### The template engine

A new directive needs:

- a branch in `Parser._parse_directive`,
- its closing directive, if it has one, added to `Parser._closing_directives`,
- a `Node` subclass in `pyblade/engine/nodes.py`, imported into the parser.

Block directives parse their body with `_parse_until_directives([...])`, then call
`expect("DIRECTIVE", value_prefix="@end...")`. A directive that stores a value is written
`@name(as VARIABLE)`, as `@lang` and `@now` are.

When rendering:

- **Output is escaped.** Whatever a node writes from a value goes through `html_escape`, unless it
  is markup the node built itself.
- **Each component renders in a context of its own.** Anything that must cross renders, such as
  the pushes gathered for `@stack`, goes through a render-scoped collection in
  `pyblade/engine/stacks.py`, not through the context.
- **The render cache stores `(output, pushes)`.** Any other side effect of a render has to be
  cached alongside them, or it is lost on a cache hit.

### Live components

Anything that arrives from the browser is untrusted input: properties, action arguments, event
data, uploaded files, and the snapshot itself. Before changing the live endpoints or
`LiveComponent`, read the [security page](https://docs.pyblade.com/security) of the docs. The rules
the server side relies on:

- Names starting with `_` are private: never sent to the browser, never settable, never callable.
- Only methods a component declares, or takes from a `ComponentMixin`, are actions.
- The browser may only set properties the component holds (see `_check_settable_from_client`).
- An endpoint that builds a component verifies the signed snapshot first and is wrapped in
  `@throttled`, as `update_component` and `upload_file` are. An endpoint that serves a file checks
  a signed note, as `preview_upload` does.
- In production, an error's message never reaches the browser, except a `PermissionError`, which
  is a refusal meant for the user.

On the client side, directives are attributes written `pb:name`, never `pb-name`. `$pb` is a
component as JavaScript sees it, and `PyBlade` is the global object.

## Pull requests

1. Fork the repository and create a branch from `main`, named after what it does
   (`fix-slot-escaping`, `add-persist-directive`).
2. Make your change, with tests.
3. Run `make test` and `make pre-commit`, and rebuild the bundle if you touched the client.
4. Open a pull request that explains **what** changes, **why**, and **how you checked it**. Link the
   issue it closes.

Keep commit messages short and in the imperative: "Add the @persist directive", "Fix escaping in
slots". A maintainer will review your pull request; don't be discouraged by requests for changes,
they are part of how every contribution gets merged.

## Releases

Releases are made by the maintainers. Publishing a release on GitHub builds the package and uploads
it to [PyPI](https://pypi.org/project/pyblade/).

## Questions

If something in this guide is unclear, or you're stuck, open a discussion or an issue: asking is a
contribution too, since it shows us what to explain better.dpoint that builds a component verifies the signed snapshot first and is wrapped in @throttled, as update_component and upload_file are. An endpoint that serves a file checks a signed note, as preview_upload does.
In production, an error's message never reaches the browser, except a PermissionError, which is a refusal meant for the user.
