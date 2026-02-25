class FilterRegistry:
    def __init__(self):
        self._filters = {}

    def register(self, name=None):
        def decorator(func):
            filter_name = name or func.__name__
            self._filters[filter_name] = func
            return func

        return decorator

    def get(self, name):
        return self._filters.get(name)

    def has(self, name):
        return name in self._filters

    def all(self):
        return self._filters.copy()
