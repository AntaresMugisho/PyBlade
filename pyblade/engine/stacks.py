"""What @push gathers and @stack puts out.

A push is written wherever what it brings is needed -- a page, an include, a
component -- and comes out where the layout has a stack of that name, most often
in the <head> or at the end of the <body>. The two are rarely rendered in the
order that would make that easy: the layout's stack is met before the page's
pushes, and every component renders in a context of its own. So what is pushed
is kept aside for the whole of a render, and each stack is left as a marker that
is filled in once everything has been rendered.

The whole of a render is the outermost one: rendering a template opens a
collection unless one is open already, and the one that opened it fills the
stacks as it finishes. Anything rendered inside it -- a component, a layout, a
live component on the page -- pushes into the same collection.

A push is kept once. The same content pushed twice, by a component used twice
on the page, comes out once: a script run twice is rarely what anyone meant.

What reaches the page carries markers the client reads when a live component is
updated: each push is preceded by `<!--pb:push KEY-->`, and each stack ends
with `<!--pb:stack NAME-->`. An update has no layout around it, so what the
component pushed is sent along with it (`collecting`), and the client adds what
the page does not have yet just before the end of the stack.
"""

import hashlib
import re
from contextlib import contextmanager
from contextvars import ContextVar

_current = ContextVar("pyblade_stacks", default=None)

# What a stack is rendered as until the pushes are known. A NUL cannot come out
# of a template, so it cannot be mistaken for anything written in one.
_MARKER = "\0pb-stack:{}\0"
_MARKER_PATTERN = re.compile("\0pb-stack:(.*?)\0", re.DOTALL)


def key_of(content: str) -> str:
    """What tells one push from another: its content, spaces around it aside."""
    return hashlib.sha1(content.strip().encode("utf-8")).hexdigest()[:16]


class Collection:
    """What has been pushed during one render, in the order it was pushed."""

    def __init__(self):
        self.pushes = []  # (stack name, content)

    def push(self, stack: str, content: str):
        self.pushes.append((stack, content))

    def since(self, start: int):
        """What was pushed after the given point, for a render to remember."""
        return self.pushes[start:]

    def _kept(self):
        """The pushes as they come out: in order, each (stack, content) once."""
        seen = set()

        for stack, content in self.pushes:
            key = key_of(content)
            if (stack, key) in seen:
                continue

            seen.add((stack, key))
            yield stack, key, content.strip()

    def fill(self, html: str) -> str:
        """Put what was pushed in place of the stacks it was pushed to."""
        if "\0pb-stack:" not in html:
            return html

        kept = list(self._kept())

        def stack(match):
            name = match.group(1)
            items = "".join(f"<!--pb:push {key}-->{content}" for where, key, content in kept if where == name)
            return f"{items}<!--pb:stack {name}-->"

        return _MARKER_PATTERN.sub(stack, html)

    def pushes_for_client(self):
        """The pushes, for the client to add those the page does not have yet."""
        return [{"stack": stack, "key": key, "html": content} for stack, key, content in self._kept()]


def placeholder(name) -> str:
    """What a stack is rendered as, until the render it belongs to is over."""
    return _MARKER.format(name)


def push(stack, content: str):
    """Push content to a stack, if a render is collecting.

    Outside one -- a node rendered for itself -- there is nowhere for it to go.
    """
    collection = _current.get()
    if collection is not None:
        collection.push(str(stack), content)


def current():
    """The collection of the render going on, or None."""
    return _current.get()


@contextmanager
def rendering():
    """Take part in the render going on, or be it.

    Yields the collection and whether this render is the one that opened it,
    which is the one to fill the stacks.
    """
    collection = _current.get()
    if collection is not None:
        yield collection, False
        return

    collection = Collection()
    token = _current.set(collection)
    try:
        yield collection, True
    finally:
        _current.reset(token)


@contextmanager
def collecting():
    """Collect the pushes of what is rendered inside, to be read afterwards.

    Used where a render has no layout around it, and what it pushed has to
    reach the page some other way: the update of a live component. The renders
    inside do not fill the stacks themselves; `Collection.fill` is left to the
    caller.
    """
    collection = Collection()
    token = _current.set(collection)
    try:
        yield collection
    finally:
        _current.reset(token)
