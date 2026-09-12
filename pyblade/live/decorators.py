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


# Not implemented yet. Declared here so that the decorators of a live component
# are all in one place, and so that what is still missing is plain to see.
def validate(fn):
    pass


def lazy(fn):
    pass
