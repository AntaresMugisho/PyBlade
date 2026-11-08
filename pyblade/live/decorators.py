"""The decorators a live component is written with.

A component declares what it holds as properties and what it does as methods;
these say something about one of them that the method body should not have to
repeat -- that an action answers without new HTML, that a class is a page and
which layout surrounds it.

They live together here rather than beside the base class: what they decorate is
component code, not the machinery that runs it, and a component imports them
without reaching into the internals of the engine.

    from pyblade.live.decorators import layout, renderless
"""

import inspect
from functools import wraps

from .skeleton import check_skeleton


def renderless(fn):
    """Call an action without rendering the component again.

    The component still answers with its new state, so the client keeps up with
    it; it is only the HTML it does not send, leaving the page as it is.

        @renderless
        def track(self):
            self.views += 1

    Same as calling skip_render() in the body of the action, which is what this
    does and what to use when the rendering is skipped only some of the time.
    """

    @wraps(fn)
    def action(self, *args, **kwargs):
        self.skip_render()
        return fn(self, *args, **kwargs)

    return action


class computed(property):
    """A value worked out from what the component holds, and never sent to the page.

        class Posts(LiveComponent):
            search = ""

            @computed
            def posts(self):
                return Post.objects.filter(title__icontains=self.search)

    What a component holds travels to the page and back as JSON, and a queryset or
    a form cannot. So they are not held: the page is sent `search`, and `posts` is
    built again from it whenever it is needed. It is read as a property in Python
    and by its name in the template, where it is built only if something reads it.

    It is built once and kept for as long as the component lives, which is one
    request. The template is always given a value built after the action has run;
    within an action, `del self.posts` forgets it so the next read builds it again.

    It is a property, which is why the machinery already leaves it alone: it is
    not state, not an action, and not something the page may set. Nothing checks
    who is asking for it, though -- a computed value that reads records scopes them
    to the user itself.
    """

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        # Under a private name, which is how it stays out of the state
        values = instance.__dict__.setdefault("_computed_values", {})
        name = self.fget.__name__

        if name not in values:
            values[name] = self.fget(instance)

        return values[name]

    def __delete__(self, instance):
        instance.__dict__.get("_computed_values", {}).pop(self.fget.__name__, None)


def lock(*names: str):
    """Refuse the page the right to set these properties.

        @lock("post_id", "owner_id")
        class Editor(LiveComponent):
            post_id: int
            owner_id = 0

    What a snapshot holds is signed, so the page cannot rewrite it. What the page
    sends beside it, the fields it has filled in and `$set`, is not. A property
    that points at something, the post being edited or the user it belongs to, is
    not for the page to repoint: it is locked, and a request that sets it is
    refused. The component sets it freely, in mount() or in an action.

    A lock keeps the page from writing, not from reading: the property still
    travels in the snapshot. What the page must not see belongs in a private name.

    A property has to be declared on the component, by a value or by its type, so
    that a name misspelled here is an error rather than a property left open.
    """

    def decorator(cls):
        for name in names:
            declared = hasattr(cls, name) or any(name in inspect.get_annotations(klass) for klass in cls.__mro__)

            if not declared:
                raise AttributeError(
                    f"'{name}' is not a property of the {cls.__name__} component and cannot be locked. "
                    f"Declare it on the component, as in `{name}: int` or `{name} = 0`."
                )

        # Added to rather than replaced, so that stacked decorators add up
        cls._locked = frozenset(vars(cls).get("_locked", ())) | frozenset(names)

        return cls

    return decorator


def layout(layout_name: str):
    """Name the layout a component renders inside when it is a page of its own.

        @layout("layouts.admin")
        class Posts(LiveComponent):
            ...

    The same as writing `layout_name` on the class, which is what the decorator
    does. A component rendered as a tag inside another page is never surrounded
    by it: only a component reached through as_view() is a page.
    """

    def decorator(cls):
        cls.layout_name = layout_name
        return cls

    return decorator


def on(*events: str):
    """Call the method when one of the named events is emitted.

        @on("post-created")
        def update_post_list(self, title):
            ...

    Any other component on the page emitting "post-created" has this method
    called, with the data the event carries handed to it as the arguments it
    asks for by name.

    An event name may be built from what the component holds, by naming a
    property between braces:

        @on("post-updated.{post.id}")

    which is read when the component tells the client what it listens for, so
    that only the event of that very post calls the method.
    """

    def decorator(fn):
        # Added to rather than replaced, so that stacked decorators add up
        fn.pb_events = (*getattr(fn, "pb_events", ()), *events)
        return fn

    return decorator


#: What the page asks when an action was marked without a message of its own
DEFAULT_CONFIRMATION = "Are you sure?"


def confirm(message=None):
    """Ask before the action runs, and refuse it if nothing was answered.

        @confirm("Delete this post? This cannot be undone.")
        def delete(self):
            ...

    The mark is on the action rather than on the button that calls it, so that
    the same action reached by a button that forgot to ask, or by a call written
    by hand, is refused rather than carried out.

    It guards against reaching an action by accident, and nothing more: a client
    that means harm can say it confirmed as easily as it can call the action at
    all. What must not happen without the right to it belongs behind a check on
    that right, not behind this.
    """
    if callable(message):
        message.pb_confirm = DEFAULT_CONFIRMATION
        return message

    def decorator(fn):
        fn.pb_confirm = message or DEFAULT_CONFIRMATION
        return fn

    return decorator


def streamed(fn):
    """Answer in pieces, as the action goes, rather than once it has finished.

        @streamed
        def summarize(self):
            for word in answer:
                self.stream("summary", word)

    Whatever the action streams reaches the page while it is still running, so
    a long answer is read as it is written rather than waited for.

    It costs something: the action runs beside the response rather than before
    it, on a thread of its own. An action that does not say so keeps the plainer
    way -- one answer, when it is done -- and what it streams, if it streams
    anything, arrives with that answer instead.
    """
    fn.pb_streamed = True

    return fn


def validate(fn):
    """Check what the component holds first, and do not run the action if it is wrong.

        @validate
        def save(self):
            ...

    What is expected is said by the component, as the fields it declares in
    `rules` or as the form it points at with `form_class`. An action that does
    not hold up leaves what was wrong in `errors` and is not called, so the page
    renders again with the messages and nothing was saved.

    Use validate() in the body of the action instead when it is to carry on
    either way, or validate_only() to ask about a single field.
    """
    fn.pb_validate = True

    return fn


def lazy(component_class=None, *, lines=3, shape="text", visible=False):
    """Keep the page waiting for nothing: do the work after it has loaded.

        @lazy
        class Dashboard(LiveComponent):
            def mount(self):
                self.figures = a_long_query()

        @lazy(lines=6, shape="table")
        class Report(LiveComponent):
            ...

        @lazy(visible=True)
        class Comments(LiveComponent):
            ...

    A component written this way does none of its work while the page is being
    built. It writes a skeleton of itself instead, and the page asks for it
    again as soon as it has loaded -- or once it has been scrolled to, where it
    says `visible`. What mount() was to be given travels in the signed snapshot,
    so the work happens once, later, with the same arguments it would have had.

    `lines` and `shape` say what the skeleton looks like; a component that
    writes a placeholder() of its own is shown that instead.

    A component may also be made lazy where it is written, which is what to do
    when it is only in the way on one page:

        <pb-dashboard lazy />
        <pb-comments lazy="visible" />
    """
    check_skeleton(lines=lines, shape=shape)

    def decorate(cls):
        cls._lazy = {"lines": lines, "shape": shape, "visible": visible}

        return cls

    # Written @lazy rather than @lazy(...), the class itself is what arrives
    return decorate(component_class) if component_class is not None else decorate
