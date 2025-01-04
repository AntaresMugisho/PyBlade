from pyblade import liveblade

class Submit(liveblade.Component):
    def __init__(self):
        super().__init__(2)
        self.nom = "Prince"
        self.age = 12


    def render(self):
        return liveblade.view("submit", {"name": self.nom, "items": []})
