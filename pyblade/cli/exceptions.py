class RunError(Exception):
    def __init__(self, exception) -> None:
        super().__init__(exception)

        if hasattr(exception, "__dict__"):
            self.__dict__.update(exception.__dict__)
