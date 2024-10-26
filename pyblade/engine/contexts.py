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
    def __init__(self, props: dict, attributes: dict, context: dict):
        self._props = props
        self._attributes = {**self._props, **attributes}
        self._context = context

    def __str__(self):
        string = ""
        for key, value in self._attributes.items():
            if key not in self._props and isinstance(value, str):
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

    def merge(self, attrs: dict):
        """
        Merge attribute.
        :param args:
        :return:
        """

        for key, value in attrs.items():
            self._attributes[key] = f"{attrs[key]} {self._attributes[key]}"
        return self

    def class_(self, attrs: dict):
        """
        Conditionally marge classes
        :param attrs: A dictionary containing a class : condition key values.
        :return:
        """
        return ClassContext(attrs, self._context)

    # TODO: Complete all these functions
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


class ClassContext:
    def __init__(self, attrs: dict, context: dict):
        self._class = ""
        for key, value in attrs.items():
            if eval(str(value), {}, context):
                self._class += f"{key} "

    def __str__(self):
        return f'class="{self._class.strip()}"'
