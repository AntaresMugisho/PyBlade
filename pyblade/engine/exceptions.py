class PyBladeException(Exception):
    """Base exception for all PyBlade errors."""

    def __init__(self, message: str, line: int = None, column: int = None, help: str = None):
        """
        Initialize a PyBlade exception.

        Args:
            message: The error message
            line: The line number where the error occurred
            column: The column number where the error occurred
            help: Additional help text for quick fix
        """
        self.message = message
        self.line = line
        self.column = column
        self.help = help


class TemplateNotFoundError(PyBladeException):
    """Raised when a template file cannot be found."""

    def __init__(self, message: str, line: int = None, column: int = None, help: str = None):
        super().__init__(message, line, column, help)


class DirectiveParsingError(PyBladeException):
    """Raised when there's an error parsing a template directive."""

    def __init__(self, message: str, line: int = None, column: int = None, help: str = None):
        super().__init__(message, line=line, column=column, help=help)


class TemplateRenderError(PyBladeException):
    """Raised when there's an error during template rendering."""

    def __init__(self, message: str, line: int = None, column: int = None, help: str = None):
        super().__init__(message, line, column, help)
