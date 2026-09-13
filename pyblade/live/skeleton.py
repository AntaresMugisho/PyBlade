"""What stands in for a component that is not ready yet.

A lazy component does none of its work while the page is being built, so there
is nothing of it to show and something has to hold its place. That something is
drawn from a shape and a number of lines rather than written by hand: making a
component lazy should be a decorator and nothing else.

What is drawn is deliberately plain -- bars of a flat colour that shimmer -- and
every colour and measurement of it is a custom property, so a project restyles
it the way it restyles the progress bar, by setting the properties rather than
by overriding the rules.
"""

#: How wide each line is, in turn. Text does not come in equal lengths, and a
#: stack of identical bars reads as a table rather than as something being read.
_WIDTHS = (96, 88, 92, 76, 84)

#: How short the last line is, whatever it would otherwise have been
_LAST_WIDTH = 62

#: How many cells a row of a table is drawn with
_CELLS = 3

SHAPES = ("text", "card", "table")


def check_skeleton(lines=3, shape="text"):
    """Refuse a skeleton that cannot be drawn, where it was asked for.

    Called by @lazy as the component is written, so a shape with a typo in it is
    a error at import rather than a blank rectangle discovered on a page.
    """
    if shape not in SHAPES:
        raise ValueError(
            f"'{shape}' is not a skeleton PyBlade can draw. It draws {', '.join(SHAPES)}."
        )

    if not isinstance(lines, int) or isinstance(lines, bool) or lines < 1:
        raise ValueError(f"A skeleton is drawn with at least one line, not {lines!r}.")


def skeleton_markup(lines=3, shape="text"):
    """The markup a component shows while it is still being got ready.

        skeleton_markup(lines=5, shape="table")

    Markup and nothing else: it is rendered as the component's own template
    would be, which is what puts the component's id on the root and the layout
    around the page. The root says it is busy, because something that is waiting
    should say so to whoever cannot see it shimmer.
    """
    check_skeleton(lines=lines, shape=shape)

    if shape == "table":
        body = "".join(_row() for _ in range(lines))
    else:
        block = '<div class="pb-skeleton-block"></div>' if shape == "card" else ""
        body = block + "".join(_line(index, lines) for index in range(lines))

    return (
        f'<div class="pb-skeleton pb-skeleton-{shape}" aria-busy="true">'
        f"{body}"
        "</div>"
    )


def _line(index, count):
    """One bar, as wide as a line in that place tends to be."""
    width = _LAST_WIDTH if index == count - 1 and count > 1 else _WIDTHS[index % len(_WIDTHS)]

    return f'<div class="pb-skeleton-line" style="width: {width}%"></div>'


def _row():
    """One row of a table, as a handful of cells side by side."""
    cells = "".join('<div class="pb-skeleton-cell"></div>' for _ in range(_CELLS))

    return f'<div class="pb-skeleton-row">{cells}</div>'
