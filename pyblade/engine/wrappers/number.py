from .string import StringWrapper


class NumberWrapper:
    """Wrapper for numbers that adds template-specific methods."""

    def __init__(self, value):
        self._value = value

    def format(self, decimals=2):
        """Format number with specified decimal places."""
        return StringWrapper(f"{self._value:.{decimals}f}")

    def currency(self, symbol="$"):
        """Format as currency."""
        return StringWrapper(f"{symbol}{self._value:,.2f}")

    def percentage(self, decimals=1):
        """Format as percentage."""
        return StringWrapper(f"{self._value:.{decimals}f}%")

    def abs(self):
        """Return absolute value."""
        return NumberWrapper(abs(self._value))

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return f"NumberWrapper({self._value})"

    def __eq__(self, other):
        if isinstance(other, NumberWrapper):
            return self._value == other._value
        return self._value == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, NumberWrapper):
            return self._value < other._value
        return self._value < other

    def __le__(self, other):
        if isinstance(other, NumberWrapper):
            return self._value <= other._value
        return self._value <= other

    def __gt__(self, other):
        if isinstance(other, NumberWrapper):
            return self._value > other._value
        return self._value > other

    def __ge__(self, other):
        if isinstance(other, NumberWrapper):
            return self._value >= other._value
        return self._value >= other

    def __add__(self, other):
        if isinstance(other, NumberWrapper):
            return NumberWrapper(self._value + other._value)
        return NumberWrapper(self._value + other)

    def __sub__(self, other):
        if isinstance(other, NumberWrapper):
            return NumberWrapper(self._value - other._value)
        return NumberWrapper(self._value - other)

    def __mul__(self, other):
        if isinstance(other, NumberWrapper):
            return NumberWrapper(self._value * other._value)
        return NumberWrapper(self._value * other)

    def __truediv__(self, other):
        if isinstance(other, NumberWrapper):
            return NumberWrapper(self._value / other._value)
        return NumberWrapper(self._value / other)

    def __floordiv__(self, other):
        if isinstance(other, NumberWrapper):
            return NumberWrapper(self._value // other._value)
        return NumberWrapper(self._value // other)

    def __mod__(self, other):
        if isinstance(other, NumberWrapper):
            return NumberWrapper(self._value % other._value)
        return NumberWrapper(self._value % other)
