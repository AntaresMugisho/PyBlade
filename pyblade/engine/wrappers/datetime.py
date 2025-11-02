from .number import NumberWrapper
from .string import StringWrapper


class DateTimeWrapper:
    """Wrapper for date/datetime objects that adds template-specific methods."""

    def __init__(self, value):
        self._value = value

    def format(self, fmt="%Y-%m-%d"):
        """Format date with specified format string."""
        return StringWrapper(self._value.strftime(fmt))

    def humanize(self) -> str:
        """Human-readable relative time"""
        from datetime import datetime, timedelta

        if not isinstance(self._value, datetime):
            return StringWrapper(self._value)

        now = datetime.now()
        diff = now - self._value

        if diff < timedelta(minutes=1):
            return StringWrapper("just now")
        elif diff < timedelta(hours=1):
            mins = NumberWrapper(diff.total_seconds() / 60)
            return f"{mins} minute{'s' if mins > 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = NumberWrapper(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff < timedelta(days=7):
            days = diff.days
            return StringWrapper(f"{days} day{'s' if days > 1 else ''} ago")
        elif diff < timedelta(days=30):
            weeks = diff.days // 7
            return StringWrapper(f"{weeks} week{'s' if weeks > 1 else ''} ago")
        elif diff < timedelta(days=365):
            months = diff.days // 30
            return StringWrapper(f"{months} month{'s' if months > 1 else ''} ago")
        else:
            years = diff.days // 365
            return StringWrapper(f"{years} year{'s' if years > 1 else ''} ago")

    def short(self):
        """Format date in short format."""
        return StringWrapper(self._value.strftime("%m/%d/%Y"))

    def iso(self):
        """Format date in ISO format."""
        return StringWrapper(self._value.isoformat())

    def year(self):
        """Get year."""
        return NumberWrapper(self._value.year)

    def month(self):
        """Get month."""
        return NumberWrapper(self._value.month)

    def day(self):
        """Get day."""
        return NumberWrapper(self._value.day)

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return f"DateWrapper({self._value})"
