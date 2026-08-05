import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Pattern
from uuid import uuid4
import json
import inspect
from functools import wraps
from pprint import pprint # noqa

from pyblade.engine import loader
from pyblade.engine.exceptions import TemplateNotFoundError
from pyblade.engine.template import Template
from pyblade.config import settings

from .security import generate_checksum


_OPENING_TAG_PATTERN: Pattern = re.compile(r"<(?P<tag>\w+)\s*(?P<attributes>.*?)>")

#: Values a component may share with its class without either changing under the other
_IMMUTABLE = (str, bytes, int, float, bool, complex, tuple, frozenset, type(None))


class Component:
    _rendered = ""

    #: Where the template of the component is, when it is not the one its class
    #: name points at. Reserved like everything else the base class declares, so
    #: it never travels to the client.
    template_name = None

    def __init__(self, pb_id: str = None):
        self._id = pb_id
        self._events = []
        self._skip_render = False
        self._request = None

        # A list or a dictionary declared on the class is one object, shared by
        # every component of that class. Each takes a copy of its own, so that
        # appending to one does not change what the next one starts from.
        for name, value in type(self)._declared_state().items():
            if not isinstance(value, _IMMUTABLE):
                setattr(self, name, deepcopy(value))


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

        # An inline component has no template file, so the name is only what
        # errors are reported against and never has to be resolved.
        name = self.template_name or self._locate() or type(self).__qualname__

        template = Template(
            template_name=name,
            template_path=f"{name.removesuffix('.html')}.py",
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
        """Get the HTML template name of the component.

        A component keeps its template next to its class, so the name of the
        template is where the class lives, read from the components directory.
        It is worked out again on every request rather than carried around: the
        client is never told where the code of a component is.
        """
        name = self.template_name or self._locate()

        if name is None:
            raise TemplateNotFoundError(
                f"Could not tell which template the {type(self).__name__} component renders. "
                f"Components are looked for in {Path(settings.components_dir).resolve()}."
            )

        return name

    def _locate(self):
        """Where the class of the component lives, read from the components directory."""
        try:
            # Asked of the class rather than of sys.modules, which a component
            # outliving the import of its own module would no longer be found in
            module_file = inspect.getfile(type(self))
        except TypeError:
            return None

        try:
            relative = (
                Path(module_file).resolve().with_suffix("").relative_to(Path(settings.components_dir).resolve())
            )
        except ValueError:
            return None

        return ".".join(relative.parts)

    # SYSTEM METHODS
    @classmethod
    def _is_reserved(cls, name: str) -> bool:
        """Whether a name belongs to the machinery of a component.

        Everything the base class declares drives components, it is not what a
        component is made of. Reserved names are kept out of the state sent to
        the client and out of reach of the actions coming back from it, so that
        no browser can read where a component lives or ask it to serialize
        itself, render a template of its choosing or follow a redirect.
        """
        return name.startswith("_") or name in _RESERVED_NAMES

    @classmethod
    def _declares(cls, name: str) -> bool:
        """Whether the component writes a hook of its own rather than inheriting it."""
        for klass in cls.__mro__:
            if klass is Component:
                return False
            if name in vars(klass):
                return True

        return False

    @classmethod
    def _own_attributes(cls):
        """The attributes a component declares, the ones of the base class left out."""
        attributes = {}

        for klass in reversed(cls.__mro__):
            if klass is Component or not issubclass(klass, Component):
                continue

            for name, value in vars(klass).items():
                if cls._is_reserved(name) or isinstance(value, property):
                    continue
                attributes[name] = value

        return attributes

    @classmethod
    def _declared_state(cls):
        """The properties a component declares, with the values it declares them with.

        These are the initial values of the component, the ones reset() takes it
        back to. Read from the class rather than from the instance, which by then
        holds whatever the component has been through.
        """
        return {name: value for name, value in cls._own_attributes().items() if not callable(value)}

    def _set_property(self, name: str, value):
        """Set a property of the component, running the hooks that watch it.

        Both set() and the '$set' the client sends come through here, so that a
        property changes the same way whichever side asked for it.
        """
        if self._is_reserved(name):
            raise AttributeError(
                f"'{name}' is not a property of the {type(self).__name__} component and cannot be set."
            )

        # _call_property_hook calls the generic hook as well as the one named
        # after the property, so updating() is not to be called on top of it
        self._call_property_hook("updating", name, value)

        setattr(self, name, value)

        self._call_property_hook("updated", name, value)

    def _get_state(self):
        """Get public properties of the component"""
        state = {}

        for name in self._own_attributes():
            value = getattr(self, name)
            if not callable(value):
                state[name] = value

        # Properties set while the component is alive, in mount() or in an action
        for name, value in self.__dict__.items():
            if not self._is_reserved(name) and not callable(value):
                state[name] = value

        return state

    def _get_methods(self):
        """Get public methods of the component, the ones the client may call"""
        methods = {}

        for name in self._own_attributes():
            value = getattr(self, name)
            if callable(value):
                methods[name] = value

        return methods


    def _get_events(self):
        """Get server-to-client events"""
        return list(self._events)

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
        instance = cls(state.get("_id"))

        for key, value in state.items():
            # The state comes from the client. Whatever it holds beyond the
            # properties of the component is not for it to decide.
            if cls._is_reserved(key):
                continue

            # A copy, as the component is free to change what it holds and the
            # state it was handed belongs to whoever handed it over
            setattr(instance, key, value if isinstance(value, _IMMUTABLE) else deepcopy(value))

        return instance


    # LIFECYCLE CALLERS (SSR and AJAX HANDLING)
    @staticmethod
    def _mount_arguments(mount, properties):
        """The properties mount() asks for, among the ones the component was given.

        A component declares what it expects as the parameters of its mount(),
        so only those are passed to it. One that takes **kwargs is handed
        everything, and one that takes nothing is called with nothing.
        """
        parameters = inspect.signature(mount).parameters

        if any(parameter.kind is parameter.VAR_KEYWORD for parameter in parameters.values()):
            return dict(properties)

        return {name: properties[name] for name in parameters if name in properties}

    @classmethod
    def render_initial(cls, attributes=None, request=None):
        """
        Manage the FIRST lifecycle of Server-Side Rendering.

        A live component declares what it holds as the attributes of its class,
        which is where the defaults come from. What is left to be given is the
        attributes of the call, and they override those defaults.
        """
        # 1. What the component was given, be it as a dictionary or as tag attributes
        properties = dict(attributes or {})

        # The key names the component, it is not one of its properties
        pb_id = properties.pop("key", None) or f"pb-{uuid4().hex[:8]}"

        # 2. Initial instanciation with component_id
        instance = cls(pb_id)
        instance._request = request

        # 3. Résolution of mount() arguments, among the properties given.
        # A component that does not write its own mount() takes none of them:
        # the mount() of the base class accepts anything and would swallow them all.
        arguments = cls._mount_arguments(instance.mount, properties) if cls._declares("mount") else {}

        # 4. The properties override the defaults declared on the class, which
        # are read from there and do not have to be copied over. The ones mount()
        # asks for are its own; the state they lead to is for it to decide.
        for key, value in properties.items():
            if cls._is_reserved(key) or key in arguments:
                continue
            setattr(instance, key, value)

        # 5. Call hooks
        instance.mount(**arguments)
        instance.boot()
        instance.rendering()
        instance.render()
        instance.rendered(instance._rendered)

        snapshot = instance.serialize()

        initial_scripts = f"""
<script pb:_snapshots_ >
    window.__PB_SNAPSHOTS__ = window.__PB_SNAPSHOTS__ || {{}};
    window.__PB_SNAPSHOTS__['{pb_id}'] = {json.dumps(snapshot)};
</script>
"""

        return instance._rendered + initial_scripts

    @classmethod
    def update_component(cls, state, action_name, action_args = [], request=None):
        """
        Manage the livfecycle on every AJAX request.
        """
        # 1. Recréer l'instance
        instance = cls.deserialize(state)
        instance._request = request

        # 2. Hook : hydrate()
        instance.hydrate()

        outcome = None

        # 3. A refresh asks for nothing but a new rendering
        if action_name == "$refresh":
            pass

        # 4. If the action consists on updating a property (e.g., pb:model)
        elif action_name == "$set":
            instance._set_property(action_args[0], action_args[1])

        # 5. If it's a method calling
        else:
            # Only the methods the component itself declares are within reach of
            # the client, never the ones it inherits, which drive it.
            methods = instance._get_methods()

            if action_name not in methods:
                if instance._is_reserved(action_name) or hasattr(instance, action_name):
                    raise AttributeError(
                        f"'{action_name}' is not an action of the {cls.__name__} component "
                        "and cannot be called from the client."
                    )
                raise NameError(f"Method '{action_name}' is not defined")

            outcome = methods[action_name](*action_args)

        # 6. Hooks. An action that asked not to render answers with its new
        # state alone, and the page is left as it is.
        if instance._skip_render:
            instance._rendered = None
        else:
            instance.rendering()
            instance.render()
            instance.rendered(instance._rendered)

        # 7. Return the new HTML and the new serialized state for the frontend
        response = {
            "html": instance._rendered,
            "snapshot": instance.serialize(),
            "events": instance._get_events(),
        }

        # What the action returned, when it asked the client to go somewhere
        if isinstance(outcome, dict) and "redirect" in outcome:
            response["redirect"] = outcome["redirect"]

        return response

    # MAGIC ACTIONS
    def reset(self, *properties: str):
        """Reset properties to their initial values.

        A live component declares what it holds on its class, so that is where
        the initial values are read from. Called with no name at all, it takes
        the component back to the state it was declared with.
        """
        declared = type(self)._declared_state()
        names = properties or tuple(declared)

        for name in names:
            if name not in declared:
                raise AttributeError(
                    f"'{name}' is not a property the {type(self).__name__} component declares "
                    "and cannot be reset."
                )

            # A copy, so that a list or a dictionary declared on the class is
            # never handed out twice and changed from under the other holder
            setattr(self, name, deepcopy(declared[name]))

    def pull(self, property: str):
        """Retrieve the value of a property then reset it to the initial value"""
        value = getattr(self, property)
        self.reset(property)
        return value

    def refresh(self):
        """Make a server-roundtrip and re-render the component without calling any methods.

        There is nothing to do on this side: every action is followed by a
        rendering, so asking for one and for nothing else is asking for nothing.
        The client sends it as the '$refresh' action.
        """

    def toggle(self, property: str):
        """Toggle boolean properties"""
        self.set(property, not getattr(self, property))

    def set(self, prop: str, value: Any):
        """Update a property value"""
        self._set_property(prop, value)

    def dispatch(self, event: str, **data):
        """Dispatch an event. Same as emit()"""
        self.emit(event, **data)

    def emit(self, event: str, **data):
        """Emit an event. Same as dispatch()

        The events an action emits are handed to the client with the new HTML,
        which raises each of them on the window as 'pb:<name>', the data they
        carry as the detail of the event.
        """
        self._events.append({"name": event, "data": data})

    def js(self, fn: str):
        """Call js functions from python"""
        pass


    # MAGIC PROPERTIES
    @property
    def request(self):
        """The request the component is answering, on the first rendering and on every action."""
        return self._request

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

    @classmethod
    def as_view(cls, **properties):
        """Render the component as a page of its own.

            path("posts/<int:post_id>/", Posts.as_view())

        The arguments captured by the route are handed to the component the way
        the attributes of a tag would be, so mount() receives the ones it asks
        for. What surrounds the component on the page is what its template
        extends: a component that is a page writes @extends("layouts.app") and
        its content fills the layout in, as any template does.
        """
        from django.http import HttpResponse

        def view(request, *args, **kwargs):
            return HttpResponse(cls.render_initial({**properties, **kwargs}, request=request))

        # So that a project can tell which component a route renders
        view.component = cls

        return view

    def skip_render(self):
        """Call an action without calling the render method.

        The component still answers with its new state, so the client keeps up
        with it; it is only the HTML it does not send, leaving the page as it is.
        """
        self._skip_render = True


    # Navigation
    def redirect(self, href):
        """Leave for another page, loading it anew."""
        return {"redirect": {"href": href, "navigate": False}}

    def navigate(self, href):
        """Leave for another page without reloading the one that is there."""
        return {"redirect": {"href": href, "navigate": True}}


#: Every name the base class declares. What a component adds to it is its own,
#: and is the only thing the client ever sees or reaches. Read once the class is
#: built, so that a method added to Component is covered without being listed.
_RESERVED_NAMES = frozenset(vars(Component))


# Decorators
def renderless(fn):
    """Call an action without calling the render method"""

    @wraps(fn)
    def action(self, *args, **kwargs):
        self.skip_render()
        return fn(self, *args, **kwargs)

    return action

def validate(fn):
    pass

def on(fn, event_name):
    pass

def lazy(fn):
    pass


