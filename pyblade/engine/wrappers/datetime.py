from .number import TNumber
from .string import TString


class TDateTime:
    """Wrapper for date/datetime objects that adds template-specific methods."""

    def __init__(self, value):
        self._value = value

    def format(self, fmt="%Y-%m-%d"):
        """Format date with specified format string."""
        return TString(self._value.strftime(fmt))

    def humanize(self) -> str:
        """Human-readable relative time"""
        from datetime import datetime, timedelta

        if not isinstance(self._value, datetime):
            return TString(self._value)

        now = datetime.now()
        diff = now - self._value

        if diff < timedelta(minutes=1):
            return TString("just now")
        elif diff < timedelta(hours=1):
            mins = TNumber(diff.total_seconds() / 60)
            return f"{mins} minute{'s' if mins > 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = TNumber(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff < timedelta(days=7):
            days = diff.days
            return TString(f"{days} day{'s' if days > 1 else ''} ago")
        elif diff < timedelta(days=30):
            weeks = diff.days // 7
            return TString(f"{weeks} week{'s' if weeks > 1 else ''} ago")
        elif diff < timedelta(days=365):
            months = diff.days // 30
            return TString(f"{months} month{'s' if months > 1 else ''} ago")
        else:
            years = diff.days // 365
            return TString(f"{years} year{'s' if years > 1 else ''} ago")

    def short(self):
        """Format date in short format."""
        return TString(self._value.strftime("%m/%d/%Y"))

    def iso(self):
        """Format date in ISO format."""
        return TString(self._value.isoformat())

    def year(self):
        """Get year."""
        return TNumber(self._value.year)

    def month(self):
        """Get month."""
        return TNumber(self._value.month)

    def day(self):
        """Get day."""
        return TNumber(self._value.day)

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return f"TDateTime({self._value})"
