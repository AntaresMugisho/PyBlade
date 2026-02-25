import re
from datetime import datetime, timedelta

from .registry import FilterRegistry

filters = FilterRegistry()


# STRING FILTERS
# --------------------------------------------


@filters.register()
def upper(value):
    return str(value).upper()


@filters.register()
def lower(value):
    return str(value).lower()


@filters.register()
def title(value):
    return str(value).title()


@filters.register()
def capitalize(value):
    return str(value).capitalize()


@filters.register()
def strip(value):
    return str(value).strip()


@filters.register()
def truncate(value, length):
    return str(value)[: int(length)]


@filters.register()
def excerpt(value, length, suffix: str = "..."):
    if len(str(value)) <= int(length):
        return str(value)
    return str(value)[: int(length)].rsplit(" ", 1)[0] + suffix


@filters.register()
def limit(value, length):
    return str(value)[: int(length)]


@filters.register()
def slugify(value):
    value = str(value).lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[-\s]+", "-", value)
    return value.strip("-")


# NUMERIC FILTERS
# --------------------------------------------


@filters.register()
def add(value, amount):
    return value + amount


@filters.register()
def subtract(value, amount):
    return value - amount


@filters.register()
def multiply(value, amount):
    return value * amount


@filters.register()
def divide(value, amount):
    return value / amount


@filters.register()
def currency(value, symbol="$", decimals=2):
    """Format as currency."""
    return f"{symbol} {value:,.{decimals}f}"


@filters.register()
def percentage(value, decimals=1):
    """Format as percentage."""
    return f"{value:.{decimals}f} %"


# COLLECTION FILTERS
# --------------------------------------------
@filters.register()
def length(value):
    return len(value)


@filters.register()
def count(value):
    return length(value)


@filters.register()
def first(value):
    return value[0] if value else None


@filters.register()
def last(value):
    return value[-1] if value else None


@filters.register()
def join(value, sep=","):
    return sep.join(map(str, value))


# DATE AND TIME FILTERS
# --------------------------------------------


@filters.register()
def format(value, format="%Y-%m-%d"):
    """Format date with specified format string."""
    if not isinstance(value, datetime):
        return value
    return value.strftime(format)


@filters.register()
def humanize(value) -> str:
    """Human-readable relative time"""

    if not isinstance(value, datetime):
        return value

    now = datetime.now()
    diff = now - value

    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        mins = diff.total_seconds() / 60
        return f"{mins} minute{'s' if mins > 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = diff.total_seconds() / 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif diff < timedelta(days=30):
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif diff < timedelta(days=365):
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
