from pyblade import liveblade


class Counter(liveblade.Component):

    def __init__(self):
        super().__init__(self)
        self.count = 1

    def increase(self):
        self.count += 1

    def decrease(self):
        self.count -= 1

    def render(self):
        return liveblade.view("counter", {"count": self.count})
