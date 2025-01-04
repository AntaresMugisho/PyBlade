class PyBladeException(Exception):
    """Base exception for PyBlade CLI"""

    pass


class ConfigurationError(PyBladeException):
    """Raised when there's an issue with configuration"""

    pass


class MigrationError(PyBladeException):
    """Raised when template migration fails"""

    pass
