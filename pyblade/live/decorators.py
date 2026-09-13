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

from functools import wraps


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


# Not implemented yet. Declared here so that the decorators of a live component
# are all in one place, and so that what is still missing is plain to see.
def lazy(fn):
    pass
