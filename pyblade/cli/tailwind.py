"""Tailwind CSS in a PyBlade project.

Tailwind is the one CSS framework PyBlade sets up, and unlike a stylesheet you
link it cannot simply be dropped into a project: it reads the templates to find
out which classes are actually used, and writes a stylesheet holding only those.
So a project that uses it has three things rather than one -- a stylesheet it
writes, the templates Tailwind reads, and the stylesheet Tailwind builds -- and
something has to run the build. `pyblade dev` does it while you work.

This is the one place that knows any of it. `pyblade init` and
`pyblade tailwind:config` both come here, so there is no second copy to drift.
"""

from pathlib import Path

from pyblade.cli import packages

#: What has to be installed for a stylesheet to be built at all.
PACKAGES = ["tailwindcss", "@tailwindcss/cli"]

#: The stylesheet the project writes, and the one Tailwind builds from it.
INPUT = Path("static/css/tailwind.css")
OUTPUT = Path("static/css/app.css")

#: What a project's own stylesheet starts life as. The @source lines say where
#: the classes are used: Tailwind can work that out for itself, but only from
#: the directory it is run in, and a project is not always built from its root.
STYLESHEET = """@import "tailwindcss";

/* Where Tailwind looks for the classes you use. */
{sources}
"""


def stylesheet(*directories: Path | str) -> str:
    """The text of a project's input.css, pointed at the given directories."""
    # The paths are written relative to the stylesheet, which is where Tailwind
    # reads them from, not relative to the project root
    up = "/".join([".."] * len(INPUT.parent.parts))
    sources = "\n".join(f'@source "{up}/{Path(directory).as_posix()}";' for directory in directories)

    return STYLESHEET.format(sources=sources)


def is_configured(root: Path | str) -> bool:
    """Whether this project has a Tailwind stylesheet to build."""
    return (Path(root) / INPUT).exists()


def build_command(manager: str, watch: bool = False) -> list[str] | None:
    """How to ask the project's own Tailwind to build its stylesheet.

    Run through the JavaScript package manager so that it is the Tailwind in
    this project's node_modules, at the version this project installed, rather
    than whichever one happens to be on the machine.
    """
    arguments = ["@tailwindcss/cli", "-i", INPUT.as_posix(), "-o", OUTPUT.as_posix()]

    if watch:
        arguments.append("--watch")

    return packages.js_run_command(manager, arguments)


def configure(root: Path | str, stubs: Path, sources: list[Path | str]) -> list[str]:
    """Set a project up to build a Tailwind stylesheet.

    Gives back what it did, in words, so that the command doing the asking can
    say so. Nothing already written is overwritten: a project that already has
    a layout keeps the layout it has.
    """
    root = Path(root)
    done = []

    written = root / INPUT
    written.parent.mkdir(parents=True, exist_ok=True)
    written.write_text(stylesheet(*sources))
    done.append(f"wrote {INPUT}")

    layout = root / "templates" / "layout.html"
    if not layout.exists():
        layout.parent.mkdir(parents=True, exist_ok=True)
        layout.write_text((stubs / "templates" / "tailwind_layout.html.stub").read_text())
        done.append("wrote templates/layout.html")

    if ignore_node_modules(root):
        done.append("added node_modules/ to .gitignore")

    return done


def ignore_node_modules(root: Path | str) -> bool:
    """Keep the installed packages out of the repository. True if anything changed."""
    path = Path(root) / ".gitignore"
    current = path.read_text() if path.exists() else ""

    if "node_modules" in current:
        return False

    addition = "\n# JavaScript packages, installed rather than committed\nnode_modules/\n"
    path.write_text(current.rstrip("\n") + addition if current.strip() else addition.lstrip("\n"))

    return True
