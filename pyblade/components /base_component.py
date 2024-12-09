class BaseComponent:
    """
    Main class that will be inherited by all generated components by liveblade
    """

    def __init__(self, context: dict | None = None):
        self.context = context or {}

    def render(self):
        """Render the component with the provided context."""
        pass
