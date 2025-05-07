from pyblade import PyBlade


class PyBladeTemplates:

    def __init__(self, params):
        self.engine = PyBlade(dirs="templates")
        ...

    def render(self, request, template, context): ...
