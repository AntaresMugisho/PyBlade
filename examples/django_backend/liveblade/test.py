from pyblade import liveblade


class TestComponent(liveblade.Component):

    def render(self):
        return liveblade.view("liveblade.test", context={})
