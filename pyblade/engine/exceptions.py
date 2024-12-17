"""
Custom exceptions for the PyBlade template engine.
"""


class UndefinedVariableError(Exception):
    """Raised when a template references an undefined variable."""
    def __init__(self, message: str):
        super().__init__(message)


class TemplateNotFoundError(Exception):
    """Raised when a template file cannot be found."""
    def __init__(self, template_name: str):
        super().__init__(f"Template not found: {template_name}")


class DirectiveParsingError(Exception):
    """Raised when there's an error parsing a template directive."""
    def __init__(self, message: str):
        super().__init__(message)


class TemplateRenderingError(Exception):
    """Raised when there's an error during template rendering."""
    def __init__(self, message: str):
        super().__init__(message)


class ContextValidationError(Exception):
    """Raised when there's an error validating the template context."""
    def __init__(self, message: str):
        super().__init__(message)
