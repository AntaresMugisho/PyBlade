from datetime import date, datetime
from typing import Any

from .collection import DictWrapper, ListWrapper
from .datetime import DateTimeWrapper
from .number import NumberWrapper
from .string import StringWrapper


class BaseWrapper:
    """Base wrapper for adding type-specific properties"""

    def __init__(self, value: Any):
        self._value = value

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return repr(self._value)

    def __bool__(self):
        return bool(self._value)


def wrap_value(value: Any):
    """Automatically wrap values with appropriate wrapper based on type."""
    if isinstance(value, (StringWrapper, NumberWrapper, ListWrapper, DictWrapper, DateTimeWrapper)):
        return value  # Already wrapped
    elif isinstance(value, str):
        return StringWrapper(value)
    elif isinstance(value, (int, float)):
        return NumberWrapper(value)
    elif isinstance(value, (list, tuple)):
        return ListWrapper(value)
    elif isinstance(value, dict):
        return DictWrapper(value)
    elif isinstance(value, (datetime, date)):
        return DateTimeWrapper(value)
    else:
        return value  # Return as-is for other types
