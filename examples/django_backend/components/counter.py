from pyblade import liveblade


class Counter(liveblade.Component):

    def __init__(self):
        super().__init__(self)

    def render(self):
        return liveblade.view("counter", {})
