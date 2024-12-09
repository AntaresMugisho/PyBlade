from django.template import loader
from django.http import HttpResponseRedirect

class Component:
    instances = {}

    def __init__(self, id):
        self.id = id
        self.state = {}
        Component.instances[id] = self

    @classmethod
    def get_instance(cls, id):
        return cls.instances.get(id)

    @classmethod
    def register_component(cls, component):
        cls.instances[component.id] = component

    def render(self):
        raise NotImplementedError()

    def get_html(self):
        return self.render()

    def get_context(self):
        return {**self.state, **{method: getattr(self, method) for method in dir(self) if callable(getattr(self, method)) and not method.startswith("__")}}

def view(template, context):
    """Rend le template avec le contexte donné."""
    template_ = loader.get_template(f"liveblade.{template}")
    return template_.render(context)  

def bladeRedirect(route):
         return {
              'redirect':True,
              'url':route
         }
def bladeNavigate(route):
         return {
              'navigate':True,
              'url':route
         }



