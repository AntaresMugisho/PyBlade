from html import escape as html_escape
from typing import Iterable


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


class AttributesContext:
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

        # Format the string representation of the attributes
        string = ""
        for key, value in attributes.items():
            if key not in self._props and isinstance(value, str):
                string += f" {key}" + (f'="{value}"' if value != "" else "")

        # Empty only and exclude keys
        self._only_keys = None
        self._exclude_keys = None

        return string

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


class SlotContext:

    def __init__(self, content: str = ""):
        self.content = content

    def __str__(self):
        return self.content

    def __bool__(self):
        return bool(self.content)

    def is_empty(self):
        return not self.content


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
