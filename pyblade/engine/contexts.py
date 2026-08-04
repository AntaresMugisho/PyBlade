from html import escape as html_escape
from typing import Iterable

from .exceptions import PyBladeException


class SafeContent:
    """Content that is HTML markup already and must not be escaped when displayed.

    Values of this type are recognized by VarNode, which renders them as they
    are. Everything else displayed by a template is data and keeps being escaped.
    """

    def render(self, context):
        """Render the content within the given context."""
        return str(self)


class LoopContext:
    """Holds context information for loops."""

    def __init__(self, items, parent=None):
        self._total_items = len(items)
        self._current_index = 0
        self._current_iteration = 1
        self._parent = parent

    @property
    def index(self):
        """The index of the current loop iteration (starts at 0)"""
        return self._current_index

    @index.setter
    def index(self, value):
        self._current_index = value
        self._current_iteration = value + 1

    @property
    def iteration(self):
        """The current iteration of the loop (starts at 1)"""
        return self._current_iteration

    @property
    def remaining(self):
        """The number of iterations remaining in the loop"""
        return self._total_items - self._current_iteration

    @property
    def count(self):
        """The total number of iterations in the loop"""
        return self._total_items

    @property
    def first(self):
        """True if this is the first iteration of the loop"""
        return self._current_index == 0

    @property
    def last(self):
        """True if this is the last iteration of the loop"""
        return self._current_iteration == self._total_items

    @property
    def even(self):
        """True if this is an even iteration of the loop"""
        return self._current_iteration % 2 == 0

    @property
    def odd(self):
        """True if this is an even iteration of the loop"""
        return self._current_iteration % 2 != 0

    @property
    def parent(self):
        """The parent's loop variable, when in a nested loop."""
        return self._parent

    @property
    def depth(self):
        """The nesting level of the current loop."""
        return self._parent.depth + 1 if self._parent else 0


class AttributesContext(SafeContent):
    """The attributes a component was passed and did not declare as properties.

    Displaying it spreads them over the component's root element, which is
    markup, not data, hence the SafeContent.
    """

    def __init__(self, props: dict, attributes: dict, context: dict):
        self._props = props
        self._attributes = {**self._props, **attributes}
        self._context = context

        self._only_keys = None
        self._exclude_keys = None

    def __str__(self):
        attributes = self._attributes.copy()

        # Filter attributes
        if self._only_keys:
            attributes = {key: value for key, value in attributes.items() if key in self._only_keys}
        if self._exclude_keys:
            attributes = {key: value for key, value in attributes.items() if key not in self._exclude_keys}

        # Format the string representation of the attributes. Only the attribute
        # syntax is markup here: the values are data and are escaped, or the
        # component could be handed one that closes the tag and opens another.
        string = ""
        for key, value in attributes.items():
            if key in self._props:
                continue

            if value is True or value == "":
                # A bare attribute, as the 'disabled' of <pb-button disabled />
                string += f" {key}"
            elif isinstance(value, str):
                string += f' {key}="{html_escape(value)}"'

        # Empty only and exclude keys
        self._only_keys = None
        self._exclude_keys = None

        return string

    def declare(self, props: dict):
        """
        Mark attributes as component properties.

        Declared properties belong to the component itself, so they are consumed
        rather than spread over its root element, and their default value is kept
        for the attributes the caller did not pass.
        :param props: the properties declared with @props, mapped to their default
        :return: self
        """
        self._props = {**self._props, **props}
        self._attributes = {**props, **self._attributes}
        return self

    def get(self, attr, default: str = ""):
        """
        Get the value of the given attribute
        :param attr: the attribute to get
        :param default: the default value to return if the attribute is not found
        :return: the value of the attribute
        """
        return self._attributes.get(attr, default)

    def has(self, *args) -> bool:
        """
        Check if the given attribute exists
        :param args: list of attributes to check
        :return: bool
        """
        for attribute in args:
            if attribute not in self._attributes.keys():
                return False

        return True

    def has_any(self, *args) -> bool:
        """
        Check if at least one of the given attribute exists
        :param args: list of attributes to check
        :return: bool
        """
        for attribute in args:
            if attribute in self._attributes.keys():
                return True

        return False

    def exclude(self, *args):
        """
        Exclude the given attributes
        :param args: list of attributes to exclude
        :return: self
        """
        self._exclude_keys = set(args)
        return self

    def only(self, *args):
        """
        Only keep the given attributes
        :param args: list of attributes to keep
        :return: self
        """
        self._only_keys = set(args)
        return self

    def merge(self, attrs: dict):
        """
        Merge attribute.
        :param args:
        :return:
        """
        if not isinstance(attrs, dict):
            raise TypeError("Attributes must be a dictionary")

        for key, value in attrs.items():
            self._attributes[key] = f"{value} {self._attributes.get(key, '')}"
        return self

    # TODO: Complete all these functions
    def prepends(self, attrs: dict):
        pass

    def where_starts_with(self, needle: str) -> str:
        """
        Return all the attributes starting with the given string
        :param needle: the string to search
        :return:
        """
        pass

    def where_does_not_start_with(self, needle: str) -> str:
        """
        Return all the attributes that do not start with the given string
        :param needle: the string to search
        :return:
        :param needle:
        :return:
        """
        pass


class RenderableContent(SafeContent):
    """Template content kept as AST nodes and rendered lazily in the consuming context.

    Being SafeContent, it is rendered with the context at hand instead of being
    coerced to a string. This is what allows a template to hand over content
    (directives, expressions, components...) to the component it calls or to the
    layout it extends without flattening it to plain text first.
    """

    def __init__(self, nodes=None, context=None):
        self._nodes = list(nodes) if nodes else []
        self._context = context

    def __repr__(self):
        return f"{self.__class__.__name__}(nodes={self._nodes})"

    def __str__(self):
        return self.render({})

    def __bool__(self):
        return bool(self._nodes)

    @property
    def nodes(self):
        return self._nodes

    def bind(self, context):
        """Return the same content tied to the context it was written in.

        A component renders its template with its own props, but the content it
        was handed belongs to the template that wrote it and must keep seeing
        that template's variables.
        """
        return self.__class__(self._nodes, context)

    def render(self, context):
        """Render the underlying nodes within the given context."""
        if self._context is not None:
            context = {**context, **self._context}

        try:
            return "".join(node.render(context) for node in self._nodes)
        except PyBladeException as exc:
            # These nodes were written in the template that handed them over, so
            # whoever renders them must not report the error against its own file.
            exc.belongs_to_caller = True
            raise


class SlotContent(RenderableContent):
    """The content a child template passes to the template it extends."""


class SlotContext:
    """Manages named and unnamed slots for template inheritance and components."""

    def __init__(self):
        self._named_slots = {}
        self._unnamed_slots = []

    def set_slot(self, name: str, content: str):
        """Set a named slot's content."""
        self._named_slots[name] = content

    def get_slot(self, name: str, default: str = "") -> str:
        """Get a named slot's content, or default if not found."""
        return self._named_slots.get(name, default)

    def has_slot(self, name: str) -> bool:
        """Check if a named slot exists."""
        return name in self._named_slots

    def add_unnamed(self, content: str):
        """Add content to the unnamed slots list."""
        self._unnamed_slots.append(content)

    def get_unnamed(self, index: int = 0, default: str = "") -> str:
        """Get an unnamed slot by index, or default if not found."""
        if 0 <= index < len(self._unnamed_slots):
            return self._unnamed_slots[index]
        return default

    def get_all_unnamed(self) -> list:
        """Get all unnamed slots."""
        return self._unnamed_slots

    def __str__(self):
        return str(self._named_slots)

    def __bool__(self):
        return bool(self._named_slots or self._unnamed_slots)

    def is_empty(self):
        return not (self._named_slots or self._unnamed_slots)


class CycleContext:
    def __init__(self, values):
        self.values = list(values) if isinstance(values, (list, tuple)) else [values]
        self.index = 0

    def __str__(self):
        if not self.values:
            return ""
        val = str(self.values[self.index])
        # str() is very important here to handle the case where the variable is a CycleContext instance

        self.index = (self.index + 1) % len(self.values)
        return html_escape(val)

    def current(self):
        if not self.values:
            return ""
        return str(self.values[self.index])

    def reset(self):
        self.index = 0


class ErrorMessageContext:
    def __init__(self, error_list: Iterable):
        self._error_list = error_list

    def __str__(self):
        return self._error_list[0]

    def __iter__(self):
        return self._error_list
