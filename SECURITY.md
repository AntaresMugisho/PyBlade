# Security Policy

## Feedback, and security reports

For general feedback on PyBlade and every product around it — the framework, the IDE extensions
such as PyBlade IntelliSense, the documentation — use the feedback portal at
[feedback.pyblade.com](https://feedback.pyblade.com): bug reports, ideas and suggestions are all
welcome there.

A security vulnerability is the one thing **not** to share there, or in any public issue,
discussion or pull request: report it privately, as described below. This applies to a
vulnerability in any PyBlade product, not only in the framework.

## Reporting a vulnerability

Report a vulnerability privately, in either of these ways:

- by email to <security@pyblade.com>, for any PyBlade product,
- or, for the framework, through GitHub's
  [private vulnerability reporting](https://github.com/antaresmugisho/pyblade/security/advisories/new)
  on this repository.

Include what you can of:

- the product and its version (PyBlade itself, or an extension), and the framework it runs under,
- a description of the vulnerability and what an attacker could do with it,
- the smallest template, component or request that reproduces it.

We will acknowledge your report, keep you informed as we work on a fix, and credit you in the
release that fixes it, unless you'd rather not be named.

## Supported versions

PyBlade is in an experimental phase: security fixes are made on the latest release only.

## Scope

PyBlade renders templates on the server and lets browsers call the actions of live components. In
scope are weaknesses in what PyBlade itself protects, for example:

- output escaping, and the sandbox template expressions run in,
- the signing of live components' state,
- which properties and methods of a live component the browser can reach,
- the live endpoints: CSRF protection, rate limits, uploads and previews,
- information leaked by errors when `DEBUG` is off.

Some things are not vulnerabilities in PyBlade, but choices an application makes:

- markup written with `{!! !!}`, which is rendered unescaped by design,
- templates whose source is built from user input,
- a live component action that doesn't check the user is allowed to do what it does,
- running with `DEBUG = True` in production, or with a `SECRET_KEY` others know.

The [security page](https://docs.pyblade.com/security) of the documentation
explains what PyBlade protects and what is left to the application.
