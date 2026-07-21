import re
from typing import Any, Dict, Pattern
from uuid import uuid4
import json

from pyblade.engine import loader
from pyblade.engine.exceptions import TemplateNotFoundError

_OPENING_TAG_PATTERN: Pattern = re.compile(r"<(?P<tag>\w+)\s*(?P<attributes>.*?)>")


class Component:
    _instances = {}

    def __init__(self):
        self._id = f"{self.get_template_name()}-{uuid4().hex[:8]}"

        # Register the instance in the intances list.
        self.__class__._instances[self._id] = self


    def get_methods(self):
        return {k: v for k, v in self.__class__.__dict__.items() if not k.startswith("_") and callable(v)}


    def view(self, context: Dict[str, Any] = None):
        """Render a component with its context"""

        if not context:
            context = {}

        # Load the component's template
        try:
            template = loader.load_template(self.get_template_name())
        except TemplateNotFoundError:
            raise TemplateNotFoundError(f"No component named {self.get_template_name()}")

        # Add liveblade_id attribute to the root node of the component
        match = re.search(_OPENING_TAG_PATTERN, template.content)
        tag = match.group("tag")
        attributes = match.group("attributes")
        updated_content = re.sub(
            rf"{tag}\s*{attributes}",
            f'{tag} {attributes} pb-id="{self._id}"',
            template.content,
            1,
        )

        template.content = updated_content
        context = {**context, **self.get_context()}
        return template.render(context)

    # LIFECYCLE HOOKS
    def mount(self, **kwargs):
        """Called at the initial component rendering. This is the equivalent of __init__() in python"""
        pass

    def boot(self):
        """Called on every request, after the component is mounted."""
        pass
        
    def hydrate(self):
        """Called on every AJAX request, just after the state is deserialized."""
        pass

    def render(self):
        """
        Called to render the component.
        """
        raise NotImplementedError()

    def rendering(self):
        """
        Called before the component is rendered.
        """
        pass

    def rendered(self):
        """
        Called after the component is rendered.
        """
        pass

    def updating(self, property: str, value):
        """
        Called before a property is updated.
        property: The name of the current property being updated
        value: The value about to be set to the property
        """
        pass

    def updated(self, property: str, value):
        """
        Called after a property is updated.
        property: The name of the current property that was updated
        value: The new value of the property
        """
        pass

    def _call_property_hook(self, phase: str, property_name: str, *args):
        """
        Allow generic property related methods (e.g: updating_email, updated_email)
        """
        # Generic hook (updated / updating)
        generic = getattr(self, phase, None)
        if callable(generic):
            generic(property_name, *args)

        # Property-specific hook (updated_username / updating_username)
        specific = getattr(self, f"{phase}_{property_name}", None)
        if callable(specific):
            specific(*args)

    
    # SYSTEM METHODS
    @classmethod
    def get_instance(cls, id: str):
        """Retrieve a component instance based on an ID"""
        return cls._instances.get(id)

    def get_template_name(self):
        """Get the HTML template name of the component"""
        return self.template_name

    def get_state(self):
        """Get public state og the component (variables the instance)"""
        return {
            k: v
            for k, v in self.__dict__.items()
            if not (k.startswith("_") and not callable(v))
        }

    def serialize(self):
        """Serialize the component state to JSON"""
        return json.dumps(self.get_sate())

    @classmethod
    def deserialize(cls, state_json: str):
        """Recreate a component's instance from a JSON state from client"""
        state = json.loads(state_json)
        instance = cls()
        for key, value in state.items():
            setattr(instance, key, value)
        return instance



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

    def stop_propagation():
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
