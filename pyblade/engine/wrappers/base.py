from typing import Any


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
