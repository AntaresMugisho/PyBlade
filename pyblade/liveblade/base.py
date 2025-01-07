from django.template import loader
from django.http import HttpResponseRedirect
import re
from functools import wraps
import uuid

class Component:
    instances = {}

    def __init__(self, name):
        self.id = f"{name}_{str(uuid.uuid4())}"
        self._reactive_properties = {}
        self._computed_properties = {}
        self._watchers = {}
        
        # Initialiser les propriétés réactives à partir des annotations de classe
        for name, value in self.__class__.__dict__.items():
            if not name.startswith('_'):
                if isinstance(value, property):
                    # C'est une propriété calculée
                    self._computed_properties[name] = value
                elif not callable(value):
                    # C'est une propriété réactive
                    self._reactive_properties[name] = value

        Component.instances[self.id] = self
        print(Component.instances.keys())

    def __getattribute__(self, name):
        try:
            # D'abord, essayons d'obtenir l'attribut normalement
            return super().__getattribute__(name)
        except AttributeError:
            # Si l'attribut n'existe pas, vérifions les propriétés réactives
            reactive_props = super().__getattribute__('_reactive_properties')
            if name in reactive_props:
                return reactive_props[name]
            raise

    def __setattr__(self, name, value):
        if name in ('id', '_reactive_properties', '_computed_properties', '_watchers'):
            super().__setattr__(name, value)
            return

        if name in self._reactive_properties:
            old_value = self._reactive_properties[name]
            if old_value != value:
                self._reactive_properties[name] = value
                self._trigger_watchers(name, old_value, value)
        else:
            super().__setattr__(name, value)

    def _trigger_watchers(self, name, old_value, new_value):
        if name in self._watchers:
            for watcher in self._watchers[name]:
                watcher(new_value, old_value)

    def watch(self, property_name, callback):
        """Ajouter un watcher pour une propriété"""
        if property_name not in self._watchers:
            self._watchers[property_name] = []
        self._watchers[property_name].append(callback)

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
        return {**self._reactive_properties, **{method: getattr(self, method) for method in dir(self) if callable(getattr(self, method)) and not method.startswith("__")}}

def computed(func):
    """Décorateur pour les propriétés calculées"""
    return property(func)

def view(template: str, context: dict | None = None):
    if context is None:
        context = {}
    
    template_ = loader.get_template(f"liveblade.{template}")
    rendered_template = template_.render(context)
    
    tag_pattern = re.compile(
        r"<(?P<tag>\w+)\s*(?P<attributes>[^>]*)>(.*?)</(?P=tag)>", 
        re.DOTALL
    )
    
    match = re.search(tag_pattern, rendered_template)
    if match:
        tag = match.group("tag")
        attributes = match.group("attributes")
        
        modified_attributes = f'{attributes} liveblade_id="{template.split('.')[0]}"'
        component_content = re.sub(attributes, modified_attributes, rendered_template)
        
        return component_content
    
    return rendered_template     

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
