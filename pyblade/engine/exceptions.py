"""
Custom exceptions for the PyBlade template engine.
"""


class PyBladeException(Exception):
    """Base exception for all PyBlade errors."""

    def __init__(self, message: str, template_name: str = None, line: int = None, column: int = None):
        self.message = message
        self.template_name = template_name
        self.line_number = line
        self.column = column
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format error message with location info."""
        parts = [self.message]
        if self.template_name:
            parts.append(f"in '{self.template_name}'")
        if self.line_number:
            parts.append(f"Line {self.line_number}")
        if self.column:
            parts.append(f"column {self.column}")
        return " ".join(parts)


class UndefinedVariableError(PyBladeException):
    """Raised when a template references an undefined variable."""

    def __init__(self, variable_name: str, template_name: str = None, line: int = None, available_vars: list = None):
        self.variable_name = variable_name
        self.available_vars = available_vars or []
        message = f"Undefined variable: '{variable_name}'"
        super().__init__(message, template_name, line)


class TemplateNotFoundError(PyBladeException):
    """Raised when a template file cannot be found."""

    def __init__(self, template_name: str, search_paths: list = None):
        self.search_paths = search_paths or []
        message = f"Template not found: {template_name}"
        super().__init__(message, template_name)


class DirectiveParsingError(PyBladeException):
    """Raised when there's an error parsing a template directive."""

    def __init__(self, message: str, template_name: str = None, line: int = None, column: int = None):
        super().__init__(message, template_name, line, column)


class TemplateRenderError(PyBladeException):
    """Raised when there's an error during template rendering."""

    def __init__(self, message: str, template_name: str = None, line: int = None, context: dict = None):
        self.context = context or {}
        super().__init__(message, template_name, line)


class BreakLoop(Exception):
    """Signal to break out of a loop."""
    pass


class ContinueLoop(Exception):
    """Signal to continue to next iteration of a loop."""
    pass
