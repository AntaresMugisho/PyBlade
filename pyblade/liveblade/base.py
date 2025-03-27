import re
from typing import Any, Dict, Pattern
from uuid import uuid4

from pyblade.engine import loader
from pyblade.engine.exceptions import TemplateNotFoundError

_OPENING_TAG_PATTERN: Pattern = re.compile(r"<(?P<tag>\w+)\s*(?P<attributes>.*?)>")


class Component:
    instances = {}

    def __init__(self, name: str):
        self._name = name
        self._id = uuid4().hex

        # Register the instance in the intances list.
        self.__class__.instances[self.id] = self

    @property
    def id(self):
        return f"{self._name}-{self._id}"

    @classmethod
    def get_instance(cls, id: str):
        return cls.instances.get(id)

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

    def view(self, context: Dict[str, Any] = None):
        """Render a component with its context"""

        if not context:
            context = {}

        # Load the component's template
        try:
            template = loader.load_template(self._name)
        except TemplateNotFoundError:
            raise TemplateNotFoundError(f"No component named {self._name}")

        # Add liveblade_id attribute to the root node of the component
        match = re.search(_OPENING_TAG_PATTERN, template.content)
        tag = match.group("tag")
        attributes = match.group("attributes")
        updated_content = re.sub(
            rf"{tag}\s*{attributes}",
            f'{tag} {attributes} liveblade_id="{self.id}"',
            template.content,
            1,
        )

        template.content = updated_content
        context = {**context, **self.get_context()}
        return template.render(context)

    def update_form_data(self, form_data):
        for key, value in form_data.items():
            setattr(self, key, value)

    # Lifecycle hooks
    def mount(self, *args, **kwargs):
        """The equivalent of __init__()"""
        pass

    def boot(self):
        pass

    def render(self):
        raise NotImplementedError()

    def rendering(self):
        pass

    def rendered(self):
        pass

    def update(self):
        pass

    def updating(self):
        pass

    def updated(self):
        pass

    def serialize(self):
        pass

    def deserialize(self):
        pass

    # Actions
    def reset(self, *args):
        """Reset properties to their initial values"""
        pass

    def pull(self, property: str):
        """Retrieve the value of a property then reset it to the initial value"""
        pass

    def refresh(self):
        """Make a server-roundtrip and re-render the component without calling any methods"""
        pass

    def toggle(self, property: bool):
        """Toggle boolean properties"""
        pass

    def set(self, prop: str, value: Any):
        """Update a property value"""
        pass

    def dispatch(self, event: str):
        """Dispatch an event. Same as emit()"""
        pass

    def emit(self, event: str):
        """Emit an event. Same as dispatch()"""
        pass

    def js(self, fn: str):
        """Call js functions from python"""
        pass

    # Properties
    @property
    def event(self):
        pass

    @property
    def parent(self):
        pass

    @staticmethod
    def exception(exc, stopPropagation):
        pass

    @staticmethod
    def as_view():
        """Render the component as a Django Template View"""
        pass

    def skip_render(self):
        """Call an action without calling the render method"""
        pass


# Navigation
def bladeRedirect(route):
    return {"redirect": True, "url": route}


def bladeNavigate(route):
    return {"navigate": True, "url": route}


# Decorators
def renderless(fn):
    """Call an action without calling the render method"""
    pass
