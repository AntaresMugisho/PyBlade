class LoopContext:
    """Holds context information for loops."""

    def __init__(self, items):
        self._total_items = len(items)
        self._current_index = 0

    @property
    def index(self):
        return self._current_index

    @index.setter
    def index(self, value):
        self._current_index = value

    @property
    def iteration(self):
        return self._current_index + 1

    @property
    def remaining(self):
        return self._total_items - self.iteration

    @property
    def count(self):
        return self._total_items

    @property
    def first(self):
        return self.index == 0

    @property
    def last(self):
        return self.iteration == self.count

    @property
    def even(self):
        return self.iteration % 2 == 0

    @property
    def odd(self):
        return self.iteration % 2 != 0

    def _depth(self):
        """Should return the nesting level of the current loop."""
        pass

    def _parent(self):
        """Should return the parent's loop variable, when in a nested loop."""
        pass
