from .number import TNumber
from .string import TString


class TList:
    """Wrapper for lists that adds template-specific methods."""

    def __init__(self, value):
        self._value = list(value) if not isinstance(value, list) else value

    def join(self, separator=", "):
        """Join list elements into string."""
        return TString(separator.join(str(item) for item in self._value))

    def first(self):
        """Get first element."""
        return wrap_value(self._value[0]) if self._value else None

    def last(self):
        """Get last element."""
        return wrap_value(self._value[-1]) if self._value else None

    def count(self):
        """Get list length."""
        return TNumber(len(self._value))

    def reverse(self):
        """Reverse list."""
        return TList(list(reversed(self._value)))

    def sort(self):
        """Sort list."""
        return TList(sorted(self._value))

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return f"TList({self._value})"


class TDict:
    """Wrapper for dictionaries that adds template-specific methods."""

    def __init__(self, value):
        self._value = dict(value) if not isinstance(value, dict) else value

    def keys(self):
        """Get dictionary keys."""
        return TList(list(self._value.keys()))

    def values(self):
        """Get dictionary values."""
        return TList(list(self._value.values()))

    def items(self):
        """Get dictionary items."""
        return TList(list(self._value.items()))

    def get(self, key, default=None):
        """Get value by key with default."""
        return self._value.get(key, default)

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return f"TDict({self._value})"
