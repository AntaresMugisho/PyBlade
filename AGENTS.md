# AGENTS.md

Instructions for AI agents working in this repository.

[CONTRIBUTING.md](CONTRIBUTING.md) is the reference for setup, commands, tests, code style and how
the code fits together. Read it first: everything in it applies to you. This file only adds what is
specific to agents.

## Environment

- The system Python has neither pytest nor Django. Run everything through `uv run` or the Makefile
  targets listed in CONTRIBUTING.md.
- Don't use `pip install` or create a virtual environment of your own, and don't add a dependency
  unless you were asked to.

## Before you finish

- Run the tests closest to your change while you work, then `make test` and `make pre-commit`.
  Both must pass.
- If you changed anything in `pyblade/live/static/src/`, run `make build-js`: the committed bundle
  is what the browser loads.
- Treat every failing test as caused by your change until you have shown otherwise.
- For a bug fix, run the new test once before the fix and see it fail.

## Scope

- Keep the change to what was asked. Don't refactor, rename or reformat code you weren't asked to
  touch; mention what you noticed instead.
- Nothing about the conversation that produced a change goes into the code, comments or docs.
- Changes to the live endpoints or `LiveComponent` are security-sensitive. If a change would relax
  any rule in the "Live components" section of CONTRIBUTING.md, stop and ask first.

## Git

- Don't commit, push or open pull requests unless you are asked to.
- Leave alone the files you didn't change, including uncommitted work that was already there.