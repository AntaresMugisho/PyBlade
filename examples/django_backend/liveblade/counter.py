from pyblade import liveblade


class CounterComponent(liveblade.Component):
    count = 0

    def increase(self):
        self.count += 1

    def decrease(self):
        self.count -= 1

    def render(self):
        return liveblade.view("liveblade.counter", context={})
