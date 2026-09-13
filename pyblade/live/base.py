import re
from copy import deepcopy
from pathlib import Path
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
from django.utils.datastructures import MultiValueDict

from .uploads import TemporaryUpload, is_upload_reference


#: The opening tag of the root element of a component. A slot the component
#: declares is not one: it is markup for the layout to render, not the element
#: the component is put back into, hence the pb- tags left out.
_OPENING_TAG_PATTERN: Pattern = re.compile(r"<(?P<tag>(?!pb-)[a-zA-Z][\w.-]*)\s*(?P<attributes>.*?)>")

#: Values a component may share with its class without either changing under the other
_IMMUTABLE = (str, bytes, int, float, bool, complex, tuple, frozenset, type(None))

#: The layout a page component renders inside when it names none. A project that
#: has no such template renders its page components on their own.
DEFAULT_LAYOUT = "layouts.app"

#: What an event name reads from the component it is declared on, as in
#: @on("post-updated.{post.id}")
_PLACEHOLDER_PATTERN: Pattern = re.compile(r"\{([^{}]+)\}")


class EmittedEvent:
    """An event on its way out, and who it is meant for.

    Handed back by emit() so that the component may say who is to receive it,
    and nothing more: the event is already on its way, the modifiers only narrow
    who the client hands it to.

        self.emit("post-created").to("Dashboard")
        self.emit("post-created").self()
    """

    def __init__(self, event: Dict[str, Any]):
        self._event = event

    def to(self, component: str):
        """Hand the event to components of that class alone."""
        self._event["to"] = component
        return self

    def self(self):
        """Keep the event for the component that emitted it."""
        self._event["self"] = True
        return self


class LiveRender:
    """What the live components written in a template need to know about the
    rendering they are part of.

    A live component written in the template of another is not rendered afresh
    every time its parent is: it is a component of its own, with a state of its
    own, and the page already holds it. What it needs from the rendering around
    it is an identity that does not change under it, and whether the parent is
    being rendered for the first time or over again.
    """

    def __init__(self, parent_id: str, rerendering: bool = False, known=()):
        self.parent_id = parent_id
        self.rerendering = rerendering

        #: The components the client says it already holds, so that one already
        #: on the page is left where it is rather than rendered over again
        self.known = set(known)

        self._counts = {}

    def child_id(self, name: str, key=None):
        """The id of a live component written in the template being rendered.

        The same component gets the same id every time its parent renders, so
        that the page keeps the one it holds instead of starting a new one. A
        key names it outright; without one it is told apart by its name and by
        how many of that name came before it, which is stable as long as what
        the template renders is.
        """
        if key is not None:
            return str(key)

        index = self._counts.get(name, 0)
        self._counts[name] = index + 1

        return f"{self.parent_id}-{name.replace('.', '-')}-{index}"


class LiveComponent:
    _rendered = ""

    #: Where the template of the component is, when it is not the one its class
    #: name points at. Reserved like everything else the base class declares, so
    #: it never travels to the client.
    template_name = None

    #: The layout the component renders inside when it is a page of its own,
    #: written here or set by the @layout decorator. Reserved likewise.
    layout_name = None

    #: What the properties of the component are expected to look like, as Django
    #: form fields against the names they check: {"email": forms.EmailField()}.
    rules = None

    #: A form of its own to check against, instead of declaring the fields here.
    form_class = None

    #: What was wrong the last time it was checked, by property name. Reserved,
    #: so no browser can put words of its own into the page.
    errors = {}

    def __init__(self, pb_id: str = None):
        self._id = pb_id
        self._events = []
        self._skip_render = False
        self._request = None

        # Whether the layout the template extends is rendered around it. It is
        # on the first rendering, which is a whole page; it is not when an action
        # answers with the component to be put back where it already is.
        self._inherit = True

        # The layout rendered around the component, when it is a page of its own.
        # Only a component reached through as_view() is a page: one rendered as a
        # tag is already inside one, and nothing is put around it.
        self._layout = None

        # Whether this is a rendering of a component the page already holds,
        # which an action asks for and the first rendering is not
        self._rerendering = False

        # The components the client says it holds, as it says so with every
        # action it sends
        self._known_components = ()

        # What was wrong the last time this component was checked. A copy, the
        # one on the class being shared by every component of that class.
        self.errors = {}

        # What the action has streamed, when there is nowhere to stream it to
        self._streams = []

        # Where to stream to, when the response is being written as the action
        # runs rather than after it
        self._stream_sink = None

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
        context |= self._context()

        self._rendered = template.render(context, inherit=self._inherit, layout=self._page_layout())

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
        context |= self._context()

        self._rendered = template.render(context, inherit=self._inherit, layout=self._page_layout())

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

    @classmethod
    def get_layout_name(cls):
        """The layout a component rendered as a page of its own renders inside.

        A page component is not a whole document, it is the content of one, and
        the layout is what surrounds it. It is named on the class, by the
        @layout decorator or by writing layout_name, rather than in the template:
        the same component renders as a page under one route and inside another
        page as a tag, and only the first of the two is surrounded by anything.

        Left unsaid, it is DEFAULT_LAYOUT, which a project is free not to have:
        a component with no layout to render inside renders on its own.
        """
        return cls.layout_name or DEFAULT_LAYOUT

    def _page_layout(self):
        """The layout to render around this particular rendering, if any.

        There is one only when the component is a page of its own and the layout
        is rendered around it, which the first rendering of a page is and an
        action answering with the component alone is not.
        """
        if self._layout is None or not self._inherit:
            return None

        # A project is free to have no layouts/app.html. A component that never
        # named a layout renders on its own rather than failing on a template it
        # did not ask for; one that named its own is told when it is missing.
        if self._layout == DEFAULT_LAYOUT and type(self).layout_name is None:
            try:
                loader.load_template(self._layout)
            except TemplateNotFoundError:
                return None

        return self._layout

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
            if klass is LiveComponent:
                return False
            if name in vars(klass):
                return True

        return False

    @classmethod
    def _own_attributes(cls):
        """The attributes a component declares, the ones of the base class left out."""
        attributes = {}

        for klass in reversed(cls.__mro__):
            if klass is LiveComponent or not issubclass(klass, LiveComponent):
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

    @classmethod
    def _listeners(cls):
        """The events the component listens for, mapped to the method that handles each.

        A method says so with the @on decorator, which only marks it: what the
        marks add up to is read here, from the methods the component declares,
        so that a listener is a component method like any other.
        """
        listeners = {}

        for name, value in cls._own_attributes().items():
            for event in getattr(value, "pb_events", ()):
                listeners[event] = name

        return listeners

    @classmethod
    def _validation_form(cls):
        """The form the component is checked against, if it is checked at all.

        A component either points at a form of its own or declares the fields
        where its properties are; either way what does the checking is a Django
        form, so every field, validator and message Django ships works here.
        """
        if cls.form_class is not None:
            return cls.form_class

        if not cls.rules:
            return None

        # Assembled once per class rather than per request. Read from the class
        # itself rather than inherited, so a component declaring rules of its
        # own does not use the form its parent assembled.
        assembled = cls.__dict__.get("_assembled_form")
        if assembled is not None:
            return assembled

        from django import forms

        assembled = type(f"{cls.__name__}Rules", (forms.Form,), dict(cls.rules))
        cls._assembled_form = assembled

        return assembled

    @classmethod
    def _streams_from(cls, action_name):
        """Whether an action answers in pieces, as it goes.

        Only an action of the component's own: the names the client may send
        that are not one -- a refresh, a property being set -- are answered the
        plain way, and so is a name that is nothing at all.
        """
        action = cls._own_attributes().get(action_name)

        return callable(action) and getattr(action, "pb_streamed", False) is True

    @classmethod
    def _confirmations(cls):
        """The actions that must be confirmed, mapped to what the page is to ask.

        Read from the methods the component declares, the way its listeners are:
        an action says so with @confirm, which only marks it.
        """
        confirmations = {}

        for name, value in cls._own_attributes().items():
            message = getattr(value, "pb_confirm", None)
            if message is not None:
                confirmations[name] = message

        return confirmations

    def _confirm_action(self, method_name, confirmed):
        """Refuse an action that had to be confirmed and was not."""
        if method_name not in self._confirmations() or confirmed:
            return

        raise PermissionError(
            f"The '{method_name}' action of the {type(self).__name__} component "
            "must be confirmed before it is called."
        )

    def _resolved_listeners(self):
        """The listeners of the component, with the event names it builds resolved.

        An event name may name a property between braces, and it is what the
        property holds that the event is called. Resolved against the component
        as it stands, on every request: the post a component is looking at may
        well have changed since the page was rendered.

        A name that cannot be resolved is left out rather than advertised as it
        was written: an event nothing can emit is an event nobody listens for.
        """
        resolved = {}

        for event, method in self._listeners().items():
            name = self._resolve_event_name(event)
            if name is not None:
                resolved[name] = method

        return resolved

    def _resolve_event_name(self, event: str):
        """Read the placeholders of an event name, or None if one cannot be read."""
        if "{" not in event:
            return event

        try:
            return _PLACEHOLDER_PATTERN.sub(lambda match: str(self._read_path(match.group(1).strip())), event)
        except (AttributeError, KeyError, IndexError, TypeError):
            return None

    def _read_path(self, path: str):
        """Follow a dotted path into what the component holds.

        It starts at a property of the component, never at its machinery: an
        event name is written by the developer but travels to the client, and
        what it is built from is what the client is told.
        """
        parts = path.split(".")

        if not parts[0] or self._is_reserved(parts[0]):
            raise AttributeError(f"'{path}' is not a property of the {type(self).__name__} component.")

        value = self
        for part in parts:
            value = value[part] if isinstance(value, dict) else getattr(value, part)

        return value

    @staticmethod
    def _from_state(value):
        """A value the client sent, as the property is to hold it.

        The other half of _as_state: a note saying which file a property holds
        is handed back as the file, one note or a list of them. A note that was
        written over, or kept too long, is worth nothing and leaves the property
        empty rather than raising -- a page left open overnight is not a server
        error.
        """
        if is_upload_reference(value):
            return TemporaryUpload.from_reference(value)

        if isinstance(value, list) and any(is_upload_reference(item) for item in value):
            uploads = [TemporaryUpload.from_reference(item) for item in value]
            return [upload for upload in uploads if upload is not None]

        return value

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

    def _context(self):
        """What the template of the component is rendered with.

        Its state, and what belongs to the request it is answering: a page
        rendered by as_view() never goes through the template backend of the
        framework, so nothing else would put them there, and a form with no
        token in it is a form whose every submission is refused.
        """
        context = self._get_state()

        # A property holding a file renders as the file rather than as the note
        # that travels in its place, so that a template may write
        # {{ photo.url }} to show what is on its way
        context |= self._uploads()

        # What was wrong when the component was last checked, which @error reads
        context["errors"] = self.errors

        # The live components written in the template are rendered from here,
        # and this is what tells them which rendering they belong to.
        context["__live"] = LiveRender(
            parent_id=self._id,
            rerendering=self._rerendering,
            known=self._known_components,
        )

        if self._request is None:
            return context

        context.setdefault("request", self._request)

        try:
            from django.middleware.csrf import get_token
        except ImportError:
            return context

        context.setdefault("csrf_token", get_token(self._request))

        return context

    def _get_state(self):
        """Get public properties of the component"""
        state = {}

        for name in self._own_attributes():
            value = getattr(self, name)
            if not callable(value):
                state[name] = self._as_state(value)

        # Properties set while the component is alive, in mount() or in an action
        for name, value in self.__dict__.items():
            if not self._is_reserved(name) and not callable(value):
                state[name] = self._as_state(value)

        return state

    @staticmethod
    def _as_state(value):
        """A property as it travels: what is written as JSON, and signed.

        A file cannot travel, so what travels is the note saying which file it
        is -- one note, or a list of them where the property holds several.
        Everything else goes as it is.
        """
        if isinstance(value, TemporaryUpload):
            return value.reference

        if isinstance(value, list) and any(isinstance(item, TemporaryUpload) for item in value):
            return [LiveComponent._as_state(item) for item in value]

        return value

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
            "state": self._get_state(),
            # So the client knows which components to wake when an event is
            # emitted. Signed with the rest: what a component listens for is
            # not the browser's to decide.
            "listeners": self._resolved_listeners(),
            # What the page is to ask before calling an action, signed with the
            # rest: what a component asks is not the browser's to rewrite
            "confirmations": self._confirmations(),
            # What was wrong when it was last checked. Signed with the rest and
            # kept out of the state, so no browser writes its own messages into
            # the page, and so one field being put right does not forget another.
            "errors": self.errors,
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

            # A note saying which file a property holds is handed back as the
            # file, one note or a list of them
            held = cls._from_state(value)
            if held is not value:
                setattr(instance, key, held)
                continue

            # A copy, as the component is free to change what it holds and the
            # state it was handed belongs to whoever handed it over
            setattr(instance, key, value if isinstance(value, _IMMUTABLE) else deepcopy(value))

        return instance


    # LIFECYCLE CALLERS (SSR and AJAX HANDLING)
    @staticmethod
    def _accepted_arguments(callable_, properties):
        """The properties a callable asks for, among the ones on offer.

        A component declares what it expects as the parameters of its mount(),
        and a listener as the parameters of the method @on marks, so only those
        are passed. One that takes **kwargs is handed everything, and one that
        takes nothing is called with nothing.
        """
        parameters = inspect.signature(callable_).parameters

        if any(parameter.kind is parameter.VAR_KEYWORD for parameter in parameters.values()):
            return dict(properties)

        return {name: properties[name] for name in parameters if name in properties}

    def _handle_event(self, event_name, data, confirmed=False):
        """Call the method that listens for the given event, with what it carries.

        The client names the event, never the method: which one handles it is
        read here, from what the component declares with @on. An event nothing
        listens for is refused, so that no name coming from a browser can reach
        a method that was never offered to it.
        """
        method_name = self._resolved_listeners().get(event_name)

        if method_name is None:
            raise NameError(
                f"The {type(self).__name__} component does not listen for the '{event_name}' event."
            )

        self._confirm_action(method_name, confirmed)

        method = getattr(self, method_name)

        # The data of an event is a dictionary, and a listener is handed the
        # entries it asks for by name, the way mount() is handed its properties.
        return method(**self._accepted_arguments(method, data))

    @classmethod
    def render_initial(cls, attributes=None, request=None, layout=None):
        """
        Manage the FIRST lifecycle of Server-Side Rendering.

        A live component declares what it holds as the attributes of its class,
        which is where the defaults come from. What is left to be given is the
        attributes of the call, and they override those defaults.

        A layout is given when the component is a page of its own, and is
        rendered around it the way a layout is rendered around the template that
        extends it: the markup of the component fills its slot and the slots the
        component declares are read from the layout by name.
        """
        # 1. What the component was given, be it as a dictionary or as tag attributes
        properties = dict(attributes or {})

        # The key names the component, it is not one of its properties
        pb_id = properties.pop("key", None) or f"pb-{uuid4().hex[:8]}"

        # 2. Initial instanciation with component_id
        instance = cls(pb_id)
        instance._request = request
        instance._layout = layout

        # 3. Résolution of mount() arguments, among the properties given.
        # A component that does not write its own mount() takes none of them:
        # the mount() of the base class accepts anything and would swallow them all.
        arguments = cls._accepted_arguments(instance.mount, properties) if cls._declares("mount") else {}

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

        return instance._with_snapshot(instance._rendered)

    def _with_snapshot(self, rendered):
        """Write what the component boots from on its own root element.

        On the element rather than in a script beside it: the two belong
        together. Morphing keeps an element or replaces it whole, so a snapshot
        written on one is never left behind by the markup it describes, and a
        page brought in by navigating carries the state of its components with
        its markup rather than as loose tags to be gathered afterwards.

        The snapshot is what travels back to the server on every request, and is
        signed. The events the component emitted while mounting are only on
        their way out, and are written apart from it.
        """
        attributes = f"pb:snapshot='{self._as_attribute(self.serialize())}'"

        events = self._get_events()
        if events:
            attributes += f" pb:events='{self._as_attribute(events)}'"

        # The id is on the root element and nowhere else, so there is one place
        # for this to land and no tag to look for.
        return rendered.replace(f'pb:id="{self._id}"', f'pb:id="{self._id}" {attributes}', 1)

    @staticmethod
    def _as_attribute(payload):
        """Write a payload as the value of a single-quoted HTML attribute.

        Only what would end the attribute or open a tag is escaped, which leaves
        the double quotes of the JSON as they are: escaping those instead would
        be six characters for every name and every string it holds.
        """
        return (
            json.dumps(payload)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace("'", "&#39;")
        )

    @classmethod
    def update_component(
        cls, state, action_name, action_args=[], request=None, known=(), updates=None,
        confirmed=False, sink=None, errors=None,
    ):
        """
        Manage the livfecycle on every AJAX request.

        `known` is what the client says it already holds: the live components
        written in this one's template that are on the page are left where they
        are rather than started over.

        `updates` is what the page holds and the server has not seen: a field
        written pb:model keeps what is typed into it until the component next
        has something to ask, and then sends it along. It is applied before the
        action runs, so that the action sees the form as the reader left it.

        `confirmed` is the page saying the reader was asked and answered, which
        an action written @confirm will not run without.

        `sink` is where an action writing @streamed sends what it streams, as it
        streams it. Without one, what it streams is kept and sent with the answer.

        `errors` is what was wrong when the component was last checked, come
        back with the snapshot: a field put right is no reason to forget what
        was said about another.
        """
        # 1. Recréer l'instance
        instance = cls.deserialize(state)
        instance._request = request
        instance._inherit = False
        instance._rerendering = True
        instance._known_components = known
        instance._stream_sink = sink
        instance.errors = dict(errors) if isinstance(errors, dict) else {}

        # 2. Hook : hydrate()
        instance.hydrate()

        # 3. What was typed into the form and not sent until now. Set the way
        # any property is, so that the hooks watching one run for it too.
        if isinstance(updates, dict):
            for name, value in updates.items():
                instance._set_property(name, cls._from_state(value))

        outcome = None

        # 4. A refresh asks for nothing but a new rendering
        if action_name == "$refresh":
            pass

        # 5. If the action consists on updating a property (e.g., pb:model)
        elif action_name == "$set":
            instance._set_property(action_args[0], cls._from_state(action_args[1]))

        # 6. An event another component emitted, come back to be handled here
        elif action_name == "$event":
            event_name = action_args[0] if action_args else None
            data = action_args[1] if len(action_args) > 1 else {}
            outcome = instance._handle_event(
                event_name, data if isinstance(data, dict) else {}, confirmed=confirmed
            )

        # 7. If it's a method calling
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

            instance._confirm_action(action_name, confirmed)

            action = methods[action_name]

            # An action written @validate is not called when what the component
            # holds is not what it expects: the page is rendered again instead,
            # with what was wrong on it, and nothing was done.
            if getattr(action, "pb_validate", False) and not instance.validate():
                action = None

            outcome = action(*action_args) if action is not None else None

        # 8. Hooks. An action that asked not to render answers with its new
        # state alone, and the page is left as it is.
        if instance._skip_render:
            instance._rendered = None
        else:
            instance.rendering()
            instance.render()
            instance.rendered(instance._rendered)

        # 9. Return the new HTML and the new serialized state for the frontend
        response = {
            "html": instance._rendered,
            "snapshot": instance.serialize(),
            "events": instance._get_events(),
        }

        # What was wrong when it was checked, so the page can say so
        if instance.errors:
            response["errors"] = instance.errors

        # What the action streamed with nowhere to stream it to, which reaches
        # the page with the answer rather than as it was written
        if instance._streams:
            response["streams"] = instance._streams

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
        return self.emit(event, **data)

    def emit(self, event: str, **data):
        """Emit an event. Same as dispatch()

        The events an action emits are handed to the client with the new HTML.
        The client calls every component listening for one of them, and raises
        each on the window as 'pb:<name>' for whatever plain JavaScript is
        listening, the data it carries as the detail of the event.

        An event goes to every component that listens for it. What comes back
        says who else it is for:

            self.emit("post-created").to("Dashboard")
            self.emit("post-created").self()
        """
        emitted = {"name": event, "data": data}
        self._events.append(emitted)

        return EmittedEvent(emitted)


    def validate(self, only=None):
        """Check the properties against what the component expects of them.

            if not self.validate():
                return

        Answers whether they hold up, and leaves what was wrong in `errors`,
        which the template reads with @error. What the form made of the values
        -- a number where the page sent text -- is written back to the
        properties, so an action works with what it should rather than with
        whatever a form field happened to give.

        A component expecting nothing of its properties is always right.
        """
        form_class = self._validation_form()
        if form_class is None:
            return True

        names = list(form_class.base_fields)

        # A field asked about on its own that nothing is expected of is right:
        # there is nothing for it to fail
        if only is not None and only not in names:
            return True

        files = self._files()
        data = {name: getattr(self, name, None) for name in names if name not in files}

        form = form_class(data=data, files=files)
        form.is_valid()

        wrong = {name: [str(message) for message in messages] for name, messages in form.errors.items()}

        if only is None:
            self.errors = wrong
        else:
            # What was said about another field is not forgotten because this
            # one was asked about
            errors = dict(self.errors)
            errors.pop(only, None)
            if only in wrong:
                errors[only] = wrong[only]
            self.errors = errors

        # Only what came through cleanly is written back, and only over a
        # property the component actually holds. A property holding a file is
        # left alone: what a form gives back for one is an open file with
        # nowhere to be kept, where the property holds the upload itself --
        # which is what an action keeps for good, and what travels to the page
        # as its signed note.
        for name, value in getattr(form, "cleaned_data", {}).items():
            if name in files:
                continue

            if (only is None or name == only) and not self._is_reserved(name):
                setattr(self, name, value)

        return only not in wrong if only is not None else not wrong

    def validate_only(self, name: str):
        """Check a single property, leaving what was said about the others alone.

        What a field being left behind asks for: the reader has finished with
        this one and not yet reached the next, so only this one is answered for.
        """
        return self.validate(only=name)

    def _uploads(self):
        """The properties holding a file that has been sent but not kept.

        A property holding several is answered as the list it holds, so that
        what reads this sees the property as the component does.
        """
        uploads = {}

        def held(value):
            if isinstance(value, TemporaryUpload):
                return value

            if isinstance(value, list) and value and all(
                isinstance(item, TemporaryUpload) for item in value
            ):
                return value

            return None

        for name in self._own_attributes():
            value = held(getattr(self, name, None))
            if value is not None:
                uploads[name] = value

        for name, value in self.__dict__.items():
            if self._is_reserved(name):
                continue

            value = held(value)
            if value is not None:
                uploads[name] = value

        return uploads

    def _files(self):
        """The properties holding a file, as Django hands files to a form.

        A form takes what was typed and what was uploaded in two bags, and a
        file field looks in the second one. A property holding an upload belongs
        there rather than among the values.

        The bag is the one Django's own is: a field asking for several files
        reads them with getlist, which only a MultiValueDict answers.
        """
        files = MultiValueDict()

        for name, upload in self._uploads().items():
            if isinstance(upload, list):
                files.setlist(name, [one.as_file() for one in upload])
            else:
                files[name] = upload.as_file()

        return files

    def stream(self, to: str, content, replace: bool = False):
        """Send content to an element on the page, without waiting to be done.

            self.stream("summary", word)
            self.stream("summary", everything, replace=True)

        `to` names the element, which says so with pb:stream. What is sent is
        added to what is there, unless it is to replace it.

        An action written @streamed sends it as it goes; one that is not keeps
        it and sends it with its answer, so what is written still arrives -- all
        at once rather than as it was written.
        """
        chunk = {"to": to, "content": str(content), "replace": bool(replace)}

        if self._stream_sink is not None:
            self._stream_sink(chunk)
        else:
            self._streams.append(chunk)

    def skip_render(self):
        """Call an action without calling the render method.

        The component still answers with its new state, so the client keeps up
        with it; it is only the HTML it does not send, leaving the page as it is.
        Same as the @renderless decorator but can be useful for conditionnaly skiping re-render.
        """
        self._skip_render = True


    # MAGIC PROPERTIES
    @property
    def request(self):
        """The request the component is answering, on the first rendering and on every action."""
        return self._request


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
        for. What surrounds the component on the page is the layout it names on
        its class, with the @layout decorator or by writing layout_name; the
        markup of the component fills the slot of that layout and the slots the
        component declares are read from it by name, as for any template that
        extends another.
        """
        from django.http import HttpResponse

        def view(request, *args, **kwargs):
            page = cls.render_initial(
                {**properties, **kwargs},
                request=request,
                layout=cls.get_layout_name(),
            )
            return HttpResponse(page)

        # So that a project can tell which component a route renders
        view.component = cls

        return view


    # Navigation
    def redirect(self, href):
        """Leave for another page, loading it anew."""
        return {"redirect": {"href": href, "navigate": False}}

    def navigate(self, href):
        """Leave for another page without reloading the one that is there."""
        return {"redirect": {"href": href, "navigate": True}}


#: Every name the base class declares. What a component adds to it is its own,
#: and is the only thing the client ever sees or reaches. Read once the class is
#: built, so that a method added to LiveComponent is covered without being listed.
_RESERVED_NAMES = frozenset(vars(LiveComponent))

