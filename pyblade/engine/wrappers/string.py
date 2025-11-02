class StringWrapper:
    """Wrapper for strings that adds template-specific methods."""

    def __init__(self, value):
        self._value = str(value)

    def slugify(self):
        """Convert string to URL-friendly slug."""
        import re

        value = self._value.lower()
        value = re.sub(r"[^\w\s-]", "", value)
        value = re.sub(r"[-\s]+", "-", value)
        return StringWrapper(value.strip("-"))

    def excerpt(self, length=100, suffix="..."):
        """Truncate string to specified length."""
        if len(self._value) <= length:
            return StringWrapper(self._value)
        return StringWrapper(self._value[:length].rsplit(" ", 1)[0] + suffix)

    def title(self):
        """Convert to title case."""
        return StringWrapper(self._value.title())

    def upper(self):
        """Convert to uppercase."""
        return StringWrapper(self._value.upper())

    def lower(self):
        """Convert to lowercase."""
        return StringWrapper(self._value.lower())

    def capitalize(self):
        """Capitalize first letter."""
        return StringWrapper(self._value.capitalize())

    def strip(self):
        """Remove leading/trailing whitespace."""
        return StringWrapper(self._value.strip())

    def replace(self, old, new):
        """Replace occurrences of substring."""
        return StringWrapper(self._value.replace(old, new))

    def limit(self, length=100):
        """Limit string to specified length without breaking words."""
        return self.excerpt(length)

    def __str__(self):
        return self._value

    def __repr__(self):
        return f"StringWrapper('{self._value}')"
