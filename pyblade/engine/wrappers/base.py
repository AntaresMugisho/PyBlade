from datetime import date, datetime
from typing import Any

from .collection import TList, TDict
from .datetime import TDateTime
from .number import TNumber
from .string import TString


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
    if isinstance(value, (TString, TNumber, TList, TDict, TDateTime)):
        return value  # Already wrapped
    elif isinstance(value, str):
        return TString(value)
    elif isinstance(value, (int, float)):
        return TNumber(value)
    elif isinstance(value, (list, tuple)):
        return TList(value)
    elif isinstance(value, dict):
        return TDict(value)
    elif isinstance(value, (datetime, date)):
        return TDateTime(value)
    else:
        return value  # Return as-is for other types
