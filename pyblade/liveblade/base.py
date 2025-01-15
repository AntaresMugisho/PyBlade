from typing import Any, Dict

from pyblade.engine.exceptions import TemplateNotFoundError  # noqa


class Component:
    instances = {}

    def __init__(self):
        Component.register(self)

    @classmethod
    def get_instance(cls, id):
        return cls.instances.get(id)

    @classmethod
    def register(cls, component):
        cls.instances[component] = component.__class__.__name__

    def render(self):
        raise NotImplementedError()

    def get_html(self):
        return self.render()

    def get_context(self):
        context = {}
        methods = {
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

    # component = Component.instances.get(template_name, None)
    # if not component:
    #     raise TemplateNotFoundError(f"No component named {template_name}")

    # template = component._template
    # context = {**context, **component.get_context()}
    return context


def bladeRedirect(route):
    return {"redirect": True, "url": route}


def bladeNavigate(route):
    return {"navigate": True, "url": route}
