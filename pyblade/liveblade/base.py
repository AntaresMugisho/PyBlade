from typing import Any, Dict

from pyblade.engine.exceptions import TemplateNotFoundError


class Component:
    instances = {}

    def __init__(self, **kwargs):
        self._id = kwargs.get("id", id(self))
        self._template = kwargs.get("template", None)
        self._state = {}
        Component.register_component(self)

    @classmethod
    def get_instance(cls, id):
        return cls.instances.get(id)

    @classmethod
    def register_component(cls, component):
        cls.instances[component._id] = component

    def render(self):
        raise NotImplementedError()

    def get_html(self):
        return self.render()

    def get_context(self):
        context = {}
        methods = {
            **self._state,
            **{
                method: getattr(self, method)
                for method in dir(self)
                if callable(getattr(self, method)) and not method.startswith("__")
            },
        }

        for attr in dir(self):
            if not callable(getattr(self, attr)) and not attr.startswith("_"):
                context[attr] = getattr(self, attr)
        return {**context, **methods}


def view(template_name: str, context: Dict[str, Any] = None):
    """Rend le template avec le contexte donné."""
    if not context:
        context = {}

    component = Component.instances.get(template_name, None)
    if not component:
        raise TemplateNotFoundError(f"No component named {template_name}")

    template = component._template
    context = {**context, **component.get_context()}
    return template.render(context)


def bladeRedirect(route):
    return {"redirect": True, "url": route}


def bladeNavigate(route):
    return {"navigate": True, "url": route}
