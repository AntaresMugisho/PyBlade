from pprint import pprint

from pyblade import liveblade


class TestComponent(liveblade.Component):
    name = "Antares"
    online = False

    def render(self):
        return liveblade.view("liveblade.test", context={"overlay": True})


inst = TestComponent()

pprint(inst.get_context())
