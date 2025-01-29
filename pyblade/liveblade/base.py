import re
from typing import Any, Dict, Pattern

from pyblade.engine import loader
from pyblade.engine.exceptions import TemplateNotFoundError

_OPENING_TAG_PATTERN: Pattern = re.compile(r"<(?P<tag>\w+)\s*(?P<attributes>.*?)>")


def model(field_name=None):
    """Décorateur pour marquer une propriété comme un modèle de formulaire"""
    def decorator(func):
        func._is_model = True
        func._field_name = field_name or func.__name__
        return func
    return decorator


class Component:
    instances = {}

    def __init__(self, name: str):
        print(f"Initializing component {name}")
        self._form_data = {}
        Component.register(name, self)

    @classmethod
    def register(cls, name: str, instance):
        print(f"Registering component {name}")
        cls.instances[name] = instance

    @classmethod
    def get_instance(cls, id):
        return cls.instances.get(id)

    def render(self):
        raise NotImplementedError()

    def get_html(self):
        return self.render()

    def get_methods(self):
        return {k: v for k, v in self.__class__.__dict__.items() if not k.startswith("__") and callable(v)}

    def get_context(self):
        """Get all variables of the class and the instance"""
        return {
            k: v
            for k, v in {**self.__class__.__dict__, **self.__dict__}.items()
            if not (k.startswith("_") or callable(v))
        }

    def update_form_data(self, form_data):
        """
        Met à jour les attributs du composant avec les données du formulaire
        
        Args:
            form_data: Dictionnaire contenant les données du formulaire
        """
        print(f"Updating form data: {form_data}")
        for key, value in form_data.items():
            setattr(self, key, value)
        print(f"Updated attributes: {vars(self)}")


def view(template_name: str, context: Dict[str, Any] = None):
    """Render a component with its context"""
    if not context:
        context = {}

    # Load the component's template
    try:
        template = loader.load_template(template_name)
    except TemplateNotFoundError:
        raise TemplateNotFoundError(f"No component named {template_name}")

    # Add liveblade_id attribute to the root node of the component
    match = re.search(_OPENING_TAG_PATTERN, template.content)
    tag = match.group("tag")
    attributes = match.group("attributes")
    updated_content = re.sub(
        rf"{tag}\s*{attributes}",
        f'{tag} {attributes} liveblade_id="{template_name}"',
        template.content,
        1,
    )

    template.content = updated_content

    component = Component.instances.get(template_name, None)
    # if not component:
    #     # Reregister component in case the path was changed
    #     Component.register(template_name, Component(template_name))
    #     component = Component.instances.get(template_name, None)

    context = {**context, **component.get_context()}
    return template.render(context)


def bladeRedirect(route):
    return {"redirect": True, "url": route}


def bladeNavigate(route):
    return {"navigate": True, "url": route}
    return template.render(context)


def bladeRedirect(route):
    return {"redirect": True, "url": route}


def bladeNavigate(route):
    return {"navigate": True, "url": route}
