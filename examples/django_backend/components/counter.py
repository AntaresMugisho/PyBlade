from pyblade import liveblade


class Counter(liveblade.Component):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.count = 1

    def increase(self):
        self.count += 1

    def decrease(self):
        self.count -= 1

    def render(self):
        return liveblade.view("counter")
