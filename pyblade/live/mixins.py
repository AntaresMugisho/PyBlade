"""Behaviour a live component takes from somewhere other than LiveComponent.

    class Sortable(ComponentMixin):
        sort = "name"

        def sort_by(self, column):
            self.sort = column

    class Posts(LiveComponent, Sortable):
        ...

What a class inheriting ComponentMixin declares is the component's own: its
public methods become actions the page may call, and what it holds becomes state,
travelling to the page and back like any other property. That is exactly what
makes a mixin useful, and exactly why it has to be asked for: the rest of a
component's bases -- a class from the project, from a library -- bring nothing,
so that building a component on one never hands that class to the browser.

Only the classes that inherit ComponentMixin count, not what they in turn are
built on. A mixin built on a class of the project brings what the mixin declares
and nothing of that class.

This module imports nothing, and ComponentMixin knows nothing of the framework
serving the component. A mixin says what a component is made of, and that is the
same whether it is Django answering or anything else.
"""


class ComponentMixin:
    """Mark a class as one whose methods and state belong to the component.

    It declares nothing and asks nothing of the classes built on it -- no
    constructor to cooperate with, no names to collide with -- so inheriting it
    is a statement about the class rather than a change to it. It is also where
    anything every mixin comes to share will live.
    """
