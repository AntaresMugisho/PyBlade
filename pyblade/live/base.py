import re
from typing import Any, Dict, Pattern
from uuid import uuid4
import json
import inspect
from pprint import pprint # noqa

from pyblade.engine import loader
from pyblade.engine.exceptions import TemplateNotFoundError
from pyblade.engine.template import Template
from pyblade.config import settings

from .security import generate_checksum


_OPENING_TAG_PATTERN: Pattern = re.compile(r"<(?P<tag>\w+)\s*(?P<attributes>.*?)>")


class Component:
    _rendered = ""

    def __init__(self, pb_id: str = None):
        self._id = pb_id


    def render_template(self, context: Dict[str, Any] = None):
        """Render a component with its context"""

        if not context:
            context = {}

        # Load the component's template
        try:
            template = loader.load_template(self.get_template_name(), [settings.components_dir])
        except TemplateNotFoundError:
            raise TemplateNotFoundError(f"No component named {self.get_template_name()}")
       
        # Add pb-id to the root node of the template
        if self._id is not None:
            template.content = self._inject_component_id(template.content)

        # Update the context
        context |= self._get_state()

        self._rendered = template.render(context)

        return self._rendered

    def render_inline(self, template_string: str, context: Dict[str, Any] = None):
        """Render an inline live component (not attached to an HTML template file)"""

        if not context:
            context = {}

        template = Template(
            template_name=self.get_template_name(),
            template_path=f"{self.get_template_name().removesuffix('.html')}.py",
            template_string=template_string,
        )

        # Add pb-id to the root node of the template
        if self._id is not None:
            template.content = self._inject_component_id(template.content)

        # Update context
        context |= self._get_state()

        self._rendered = template.render(context)

        return self._rendered

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

        This method intentionally delegates to `self.render_template()` instead of
        `self.render_inline()`.

        Inline components are expected to override this method and explicitly call
        `self.render_inline()`, since rendering inline requires the component to
        provide its template string.

        If a component does not implement `render()`, we assume it is a template-
        based component and fall back to `self.render_template()`. This behavior
        also allows `render()` to be intentionally omitted from component
        class.
        """
        return self.render_template()

    def rendering(self):
        """
        Called before the component is rendered.
        """
        pass

    def rendered(self, rendered_content: str):
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

    def _call_property_hook(self, phase: str, property_name: str, value):
        """
        Allow generic property related methods (e.g: updating_email, updated_email)
        """
        # Generic hook (updated / updating)
        generic = getattr(self, phase, None)
        if callable(generic):
            generic(property_name, value)

        # Property-specific hook (updated_username / updating_username)
        specific = getattr(self, f"{phase}_{property_name}", None)
        if callable(specific):
            specific(value)

    def get_template_name(self):
        """Get the HTML template name of the component"""
        return self.template_name

    # SYSTEM METHODS
    def _get_state(self):
        """Get public properties of the component"""
        return {
            k: v
            for k, v in self.__dict__.items()
            if not (k.startswith("_") and not callable(v))
        }
    
    def _get_methods(self):
        """Get public methods of the component"""
        return {
            k: v
            for k, v in self.__dict__.items()
            if not (k.startswith("_") and callable(v))
        }
    
    def _get_events(self):
        """Get server-to-client events"""
        return []

    def _inject_component_id(self, template_string: str):
        """Inject the component id into the root element of the template.

        The opening tag is rebuilt from what was matched and spliced back where
        it was found. Building a pattern out of the attributes it holds would
        make any regex character they contain, a '(' or a '.', part of the
        pattern being searched for.
        """

        match = _OPENING_TAG_PATTERN.search(template_string)
        if match is None:
            return template_string

        attributes = match.group("attributes").strip()

        # A self-closing tag keeps its slash after the attribute is added
        void = ""
        if attributes.endswith("/"):
            attributes, void = attributes[:-1].rstrip(), "/"

        opening = f"<{match.group('tag')}"
        if attributes:
            opening += f" {attributes}"
        opening += f' pb:id="{self._id}"{void}>'

        return f"{template_string[:match.start()]}{opening}{template_string[match.end():]}"



    def serialize(self):
        """Serialize the component state to JSON"""
        class_path = f"{self.__class__.__module__}.{self.__class__.__qualname__}"

        payload = {
            "id": self._id,
            "class": class_path,
            "state": self._get_state()
        }

        # Attach signature
        payload["checksum"] = generate_checksum(payload)
        
        return payload

    @classmethod
    def deserialize(cls, state):
        """Recreate a component's instance from a JSON state from client"""
        instance = cls()
        for key, value in state.items():
            setattr(instance, key, value)
        return instance


    # LIFECYCLE CALLERS (SSR and AJAX HANDLING)
    @classmethod
    def render_initial(cls, props, attributes, slots, template_html, render_engine):
        """
        Gère le cycle de vie du PREMIER rendu (Server-Side Rendering).
        """
        # 1. Préparation de l'état initial par défaut
        initial_state = dict(props)
        class_defaults = {k: v for k, v in cls.__dict__.items() if not k.startswith('_') and not callable(v)}
        initial_state.update(class_defaults)

        # Get Component ID from attributes
        pb_id = attributes.get("key", f"pb-{uuid4().hex[:8]}")

        # 2. Initial instanciation with coponent_id
        instance = cls(pb_id)
        for key, value in initial_state.items():
            setattr(instance, key, value)

        # 3. Résolution et appel de mount()
        mount = getattr(instance, "mount", None)

        sig = inspect.signature(mount)
        params = sig.parameters

        if len(params) == 0:
            mount()
        else:
            mount(**params)

        # 4. Supercharge with HTML attributes
        for key, value in attributes.items():
            setattr(instance, key, value)
        
        # Hook: boot()
        instance.boot()

        # 5. Hook : rendering()
        instance.rendering()

        # 6. Hook: render()
        instance.render()

        # 7. Hook : rendered()
        instance.rendered(instance._rendered)

        # 8. State serialization for JS
        snapshot = instance.serialize()

        initial_scripts = f"""
<script pb:_snapshots_ >
    window.__PB_SNAPSHOTS__ = window.__PB_SNAPSHOTS__ || {{}};
    window.__PB_SNAPSHOTS__['{pb_id}'] = {json.dumps(snapshot)};
</script>
"""

        return instance._rendered + initial_scripts

    @classmethod
    def update_component(cls, state, action_name, action_args = []):
        """
        Gère le cycle de vie lors d'une mise à jour dynamique (Requête AJAX).
        """
        # 1. Recréer l'instance
        instance = cls.deserialize(state)

        # 2. Hook : hydrate()
        instance.hydrate()

        # 3. If the action consists on updating a property (e.g., pb:model)
        if action_name == "$set":
            prop_name, new_value = action_args[0], action_args[1]
            if prop_name.startswith("_"):
                raise AttributeError("Mutating private properties on PyBlade Live components is prohibited")

            
            # Hooks : updating() and updated() 
            instance.updating(prop_name, new_value)
            instance._call_property_hook('updating', prop_name, new_value)
            
            setattr(instance, prop_name, new_value)

            instance.updated(prop_name, new_value)
            instance._call_property_hook('updated', prop_name, new_value)

        # 4. If it's a method calling
        else:
            if action_name.startswith("_"):
                raise AttributeError("Calling private methods on PyBlade Live components is prohibited")

            method = getattr(instance, action_name, None)
            if method and callable(method):
                method(*action_args)
            else:
                raise NameError(f"Method '{action_name}' is not defined")

        # 5. Hook : rendering()
        instance.rendering()

        # 6. Hook: render()
        instance.render()

        # # 7. Hook : rendered()
        instance.rendered(instance._rendered)

        # 8. Renvoie le nouveau HTML et le nouvel état sérialisé pour le frontend
        return {
            "html": instance._rendered,
            "snapshot": instance.serialize(),
            "events": instance._get_events()
        }

    # MAGIC ACTIONS
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
        self.emit(event)

    def emit(self, event: str):
        """Emit an event. Same as dispatch()"""
        pass

    def js(self, fn: str):
        """Call js functions from python"""
        pass


    # MAGIC PROPERTIES
    @property
    def event(self):
        pass

    @property
    def parent(self):
        pass

    @staticmethod
    def exception(exc, stopPropagation):
        pass

    def stop_propagation(self):
        pass

    @staticmethod
    def as_view():
        """Render the component as a Django Template View"""
        pass

    def skip_render(self):
        """Call an action without calling the render method"""
        pass


    # Navigation
    def redirect(self, href):
        return {"redirect": True, "href": href}


    def navigate(self, href):
        return {"navigate": True, "href": href}


# Decorators
def renderless(fn):
    """Call an action without calling the render method"""
    pass
