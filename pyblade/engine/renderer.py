import traceback
from pathlib import Path

from pyblade.config import config
from pyblade.engine.exceptions import PyBladeException

from . import loader
from .processor import TemplateProcessor


class PyBlade:
    """Main template rendering engine class."""

    def __init__(
        self,
        dirs: list[str] | None = None,
        cache_size: int = 1000,
        cache_ttl: int = 3600,
    ):
        """
        Initialize the PyBlade template engine.

        Args:
            dirs: List of template directories
            cache_size: Maximum number of templates to cache
            cache_ttl: Cache time-to-live in seconds
        """
        self._template_dirs = dirs or []
        self._processor = TemplateProcessor(cache_size=cache_size, cache_ttl=cache_ttl)

    def _handle_error(
        self,
        error: PyBladeException,
        template_source: str = None,
        template_path: Path = None,
    ) -> str:
        """Handle rendering errors and return error page."""
        return error_page(error, template_source=template_source, template_path=template_path)

    def render(
        self,
        template: str,
        context: dict | None = None,
        template_path: Path | None = None,
        inherit: bool = True,
        layout: str | None = None,
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template: The template string to render
            context: The context dictionary
            template_path: The full path to teh template file
            layout: Optional layout to render the template inside, for a template
                that names one elsewhere than in its own source

        Returns:
            The rendered template string
        """

        if context is None:
            context = {}

        try:
            template = self._processor.render(template, context, inherit=inherit, layout=layout)
        except PyBladeException as exc:
            if config.DEBUG:
                if exc.template:
                    template = exc.template.content
                    template_path = exc.template.path
                return self._handle_error(error=exc, template_source=template, template_path=template_path)

            raise exc

        except Exception as exc:
            raise exc

        return template

    def render_file(self, template_name: str, context: dict | None = None) -> str:
        """
        Load and render a template file.

        Args:
            template_name: Name of the template file
            context: The context dictionary

        Returns:
            The rendered template

        Raises:
            TemplateNotFoundError: If the template file cannot be found
        """
        template = self.get_template(template_name)
        return self.render(template.content, context)

    def get_template(self, template_name: str) -> str:
        """
        Load a template file by name.

        Args:
            template_name: Name of the template file

        Returns:
            The template content

        Raises:
            TemplateNotFoundError: If the template file cannot be found
        """

        template = loader.load_template(template_name, self._template_dirs, self)
        return template

    def from_string(self, template_code, context):
        pass

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._processor.clear_cache()

    def invalidate_template(self, template: str, context: dict | None = None) -> None:
        """
        Invalidate a specific template in the cache.

        Args:
            template: The template string
            context: The context dictionary used with the template
        """
        if context is None:
            context = {}
        self._processor.invalidate_template(template, context)


def error_page(error: Exception, template_source: str = None, template_path: Path = None) -> str:
    """The page a developer is shown when something has gone wrong.

    Built from any exception, wherever it was raised. One raised while a
    template was being rendered knows the file and the line, and the lines
    around it are shown; an ordinary one raised by a component's own code knows
    neither, and brings a traceback instead.

    Only ever shown while developing: what it holds -- a path on the machine
    that is serving, the code around the line, the frames it came through -- is
    for whoever is writing the code and for nobody else.
    """
    line = getattr(error, "line", None)
    code_lines = []

    if template_source and line:
        lines = template_source.split("\n")

        start = max(0, line - 4)
        end = min(len(lines), line + 3)

        for i in range(start, end):
            code_lines.append(
                {
                    "number": i + 1,
                    "content": lines[i] if i < len(lines) else "",
                    "is_error": (i + 1) == line,
                }
            )

    context = {
        "error_type": type(error).__name__,
        "error_message": getattr(error, "message", None) or str(error),
        "template_path": template_path,
        "line": line,
        "code_lines": code_lines,
        # Where it came through, for an error that points at no template of its
        # own: an action raising is a Python error like any other, and the
        # frames are the only thing that says where it happened.
        "traceback": "" if code_lines else _traceback_of(error),
        "help": getattr(error, "help", None)
        or "An unexpected error occurred during template rendering. Check the full stack trace to identify the origin.",
    }

    template = loader.load_template("error", [Path(__file__).parent / "templates"])

    return template.render(context)


def _traceback_of(error: Exception) -> str:
    """The frames an error came through, as they are usually written out."""
    if error.__traceback__ is None:
        return ""

    return "".join(traceback.format_exception(type(error), error, error.__traceback__)).rstrip()
