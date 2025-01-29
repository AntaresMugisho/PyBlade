import re
from typing import Any, Dict, Pattern

from pyblade.engine import loader
from pyblade.engine.exceptions import TemplateNotFoundError

_OPENING_TAG_PATTERN: Pattern = re.compile(r"<(?P<tag>\w+)\s*(?P<attributes>.*?)>")


class Component:
    instances = {}

    def __init__(self, name: str):
        Component.register(name, self)

    @classmethod
    def register(cls, name: str, instance):
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


def view(template_name: str, context: Dict[str, Any] = None):
    """Render a component with its context"""
    if not context:
        context = {}

    # Load the component's template
    try:
        template = loader.load_template(template_name)
    except TemplateNotFoundError:
        raise TemplateNotFoundError(f"No component named {template_name}")

    # Add liveblade_id attribute to the root node tag of the component
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
    if not component:
        # Reregister component in case the path was changed
        Component.register(template_name, Component(template_name))
        component = Component.instances.get(template_name, None)

    # template = component._template
    context = {**context, **component.get_context()}
    return template.render(context)


def bladeRedirect(route):
    return {"redirect": True, "url": route}


def bladeNavigate(route):
    return {"navigate": True, "url": route}
