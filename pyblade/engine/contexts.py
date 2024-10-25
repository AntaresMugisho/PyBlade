class LoopContext:
    """Holds context information for loops."""

    def __init__(self, items):
        self._total_items = len(items)
        self._current_index = 0

    @property
    def index(self):
        return self._current_index

    @index.setter
    def index(self, value):
        self._current_index = value

    @property
    def iteration(self):
        return self._current_index + 1

    @property
    def remaining(self):
        return self._total_items - self.iteration

    @property
    def count(self):
        return self._total_items

    @property
    def first(self):
        return self.index == 0

    @property
    def last(self):
        return self.iteration == self.count

    @property
    def even(self):
        return self.iteration % 2 == 0

    @property
    def odd(self):
        return self.iteration % 2 != 0

    def _depth(self):
        """Should return the nesting level of the current loop."""
        pass

    def _parent(self):
        """Should return the parent's loop variable, when in a nested loop."""
        pass


class AttributesContext:
    def __init__(self, attributes):
        self._attributes = attributes

    def __str__(self):
        string = ""
        for key, value in self._attributes.items():
            if isinstance(value, str):
                string += f" {key}" + (f'="{value}"' if value != "" else "")
        return string

    def get(self, attr):
        return self._attributes.get(attr)

    def has(self, *args) -> bool:

        for attribute in args:
            if attribute not in self._attributes.keys():
                return False

        return True

    def has_any(self, *args) -> bool:
        for attribute in args:
            if attribute in self._attributes.keys():
                return True

        return False

    # TODO: Complete all these functions
    def merge(self, **kwargs):
        """
        Merge attribute.
        :param kwargs:
        :return:
        """
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

    def __init__(self, content: str):
        self.content = content

    def __str__(self):
        return self.content
