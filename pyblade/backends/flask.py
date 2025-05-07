from pyblade import PyBlade


class PyBladeEngine:

    def __init__(self, params):
        self.engine = PyBlade(dirs="templates")
        ...

    def render(self, request, template, context): ...
