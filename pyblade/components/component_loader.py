class ComponentLoader:
    def __init__(self):
        self.components = {}

    def register_component(self, name, component_class):
        self.components[name] = component_class

    def get_component(self, name):
        return self.components.get(name)
