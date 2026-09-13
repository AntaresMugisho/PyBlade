"""Driving a live component in a test, without a browser and without a server.

    from pyblade.live.testing import live

    def test_a_counter_counts():
        counter = live(Counter, start=5)

        counter.call("increment")

        assert counter.state["count"] == 6
        counter.assert_sees("6")

What a page does to a component is set a property, call an action and hand it an
event; this does the same, through the same seam the endpoint uses. So what a
test exercises is what a request does: hydrate(), the updates, the validation an
action asks for, the hooks and the rendering, in that order.

Between every step the state is written out as JSON and read back, exactly as a
snapshot travels. A property that could never make that journey fails in the
test rather than in somebody's browser.

It is called `live` rather than `test_component` on purpose: pytest collects
anything named test_* that it finds in a test module, imports included, and
would report a helper as a broken test.
"""

import json

from .uploads import store_temporarily


def live(component_class, load=True, request=None, **properties):
    """A component, mounted and rendered, ready to be driven.

        live(Counter, start=5)
        live(Dashboard, load=False)     # a lazy one, left as its skeleton

    Everything else given here is what the component is written with, as a tag
    would write it: `live(Counter, start=5)` is `<pb-counter start="5" />`.
    A component holding a property of its own called `load` or `request` sets
    it with .set() instead.
    """
    return LiveTest(component_class, load=load, request=request, **properties)


class LiveTest:
    """A component under test, and what has become of it."""

    def __init__(self, component_class, load=True, request=None, **properties):
        self.component_class = component_class
        self.request = request

        component, markup = component_class._first_pass(properties, request=request)

        self.html = markup
        self.snapshot = self._travelled(component.serialize())
        self.emitted = list(component._get_events())
        self.redirected_to = None

        # A lazy component is loaded unless the test means to look at what it
        # shows before it has been: a test of a lazy dashboard is nearly always
        # a test of the dashboard.
        if load and self.waiting:
            self.load()

    def __repr__(self):
        return f"<LiveTest {self.component_class.__name__} {self.state}>"

    # WHAT IT HOLDS
    @property
    def state(self):
        """What the component holds, as it travels."""
        return self.snapshot["state"]

    @property
    def errors(self):
        """What was wrong when it was last checked."""
        return self.snapshot.get("errors") or {}

    @property
    def waiting(self):
        """Whether it is a lazy component that has not been loaded yet."""
        return "mount" in self.snapshot

    @property
    def component(self):
        """The component itself, holding what it holds now.

        Built afresh from the state, the way a request builds it -- so a
        property holding a file is the file here too, not the note it travels
        as.
        """
        return self.component_class.deserialize(
            dict(self.state) | {"_id": self.snapshot["id"]}
        )

    # DRIVING IT
    def set(self, name, value):
        """Set a property, as a field written pb:model does."""
        return self._step("$set", [name, value])

    def call(self, action, *params, confirmed=False):
        """Call an action, as pb:click does.

        `confirmed` is the page saying the reader was asked and answered, which
        an action written @confirm will not run without.
        """
        return self._step(action, list(params), confirmed=confirmed)

    def emit(self, event, **data):
        """Hand it an event, as another component emitting one would."""
        return self._step("$event", [event, data])

    def refresh(self):
        """Ask for nothing but a new rendering."""
        return self._step("$refresh")

    def load(self):
        """Load a lazy component, as the page does once it is ready."""
        return self._step("$lazy")

    def upload(self, name, files):
        """Put a file on a property, as choosing one in a file input does.

            live(Gallery).upload("photo", SimpleUploadedFile("holiday.png", b"..."))
            live(Gallery).upload("photos", [one, another])

        The file is kept where an upload is kept and the property is left
        holding the note for it, which is what the page would have sent.
        """
        many = isinstance(files, (list, tuple))
        kept = [store_temporarily(file) for file in (files if many else [files])]

        return self.set(name, [upload.reference for upload in kept] if many else kept[0].reference)

    # ASKING ABOUT IT
    def sees(self, text):
        """Whether the markup it rendered holds the given text."""
        return text in self.html

    def assert_sees(self, text):
        if not self.sees(text):
            raise AssertionError(
                f"The {self._name} component does not show {text!r}.\n\n{self.html}"
            )

        return self

    def assert_does_not_see(self, text):
        if self.sees(text):
            raise AssertionError(
                f"The {self._name} component shows {text!r} and should not.\n\n{self.html}"
            )

        return self

    def assert_valid(self):
        if self.errors:
            raise AssertionError(
                f"The {self._name} component was not expected to be wrong about anything, "
                f"and was wrong about {', '.join(self.errors)}: {self.errors}"
            )

        return self

    def assert_invalid(self, *names):
        """It was wrong about the properties named -- or about anything at all."""
        if not self.errors:
            raise AssertionError(
                f"The {self._name} component was expected to be wrong about "
                f"{', '.join(names) or 'something'}, and was right about everything."
            )

        missing = [name for name in names if name not in self.errors]
        if missing:
            raise AssertionError(
                f"The {self._name} component was expected to be wrong about "
                f"{', '.join(missing)}, and was only wrong about {', '.join(self.errors)}."
            )

        return self

    def assert_redirected_to(self, href):
        if self.redirected_to != href:
            raise AssertionError(
                f"The {self._name} component sent the reader to "
                f"{self.redirected_to or 'nowhere'}, not to {href}."
            )

        return self

    def assert_emitted(self, event):
        if not any(emitted["name"] == event for emitted in self.emitted):
            emitted = ", ".join(one["name"] for one in self.emitted) or "nothing"
            raise AssertionError(
                f"The {self._name} component emitted {emitted}, not {event!r}."
            )

        return self

    # THE STEP ITSELF
    def _step(self, action, params=None, **extra):
        """One request, as the endpoint makes it."""
        answer = self.component_class.update_component(
            dict(self.state) | {"_id": self.snapshot["id"]},
            action,
            params or [],
            request=self.request,
            errors=self.snapshot.get("errors"),
            mount=self.snapshot.get("mount"),
            **extra,
        )

        self.snapshot = self._travelled(answer["snapshot"])

        # An action that asked not to render answers with its new state alone,
        # and what the page shows is what it was already showing
        if answer.get("html") is not None:
            self.html = answer["html"]

        self.emitted += answer.get("events") or []

        # A redirect answers with where to go and whether to navigate there;
        # what a test almost always wants to know is where.
        redirect = answer.get("redirect")
        self.redirected_to = redirect["href"] if isinstance(redirect, dict) else redirect

        return self

    def _travelled(self, snapshot):
        """The snapshot as the page would hand it back: written out, and read.

        Nothing else in a test would notice a property that cannot be written
        as JSON, and a component holding one works perfectly until the day it
        meets a browser.
        """
        try:
            return json.loads(json.dumps(snapshot))
        except TypeError as error:
            raise TypeError(
                f"The {self._name} component holds {self._untravellable(snapshot)}, which "
                f"cannot travel to the page and back: {error}"
            ) from None

    def _untravellable(self, snapshot):
        """Which properties are the ones that cannot be written as JSON."""
        offenders = []

        for name, value in (snapshot.get("state") or {}).items():
            try:
                json.dumps(value)
            except TypeError:
                offenders.append(name)

        return ", ".join(offenders) or "something"

    @property
    def _name(self):
        return self.component_class.__name__
