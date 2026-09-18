"""Walking through a long list of things, a page at a time.

Django paginates by asking for another URL: page two is a new request for a new
page, and everything on it is built again. A live component can do better --
only the list needs to change -- so what is written here keeps the page number
in the state of the component, and moving to the next one is an action like any
other.

What does the counting and the slicing is Django's own paginator. Nothing here
reimplements that; what it adds is the part Django has no opinion about: which
page a live component is on, how that survives a round trip, what the links look
like, and what the address bar says about it.
"""

from pyblade.config import settings
from pyblade.engine import loader
from pyblade.engine.contexts import SafeContent
from pyblade.engine.template import Template

from .mixins import ComponentMixin

#: What the page is called in the state and in the address bar, unless a
#: paginator is given a name of its own
DEFAULT_PAGE_NAME = "page"

#: How many pages either side of the current one the links show
DEFAULT_ON_EACH_SIDE = 3

#: The look of the links, when the project has said nothing about it
DEFAULT_TEMPLATE = "tailwind"


def _default_template_source():
    """The links template PyBlade ships, read from where the stubs live.

    The same file the `live:stubs --pagination` command copies into a project,
    so what a project starts from is exactly what it was getting already.
    """
    path = settings.stubs_dir / "pagination" / f"{DEFAULT_TEMPLATE}.html.stub"

    return path.read_text(encoding="utf-8"), path


class Links(SafeContent):
    """The links to the other pages, as markup.

    Written either way round, because both read well and the difference is not
    worth remembering:

        {{ posts.links }}
        {{ posts.links(on_each_side=5, scroll_to="#posts") }}

    The first renders it as it stands; the second is the same thing asked for
    differently. It is markup, so it is never escaped.
    """

    def __init__(self, page, template=None, data=None, on_each_side=DEFAULT_ON_EACH_SIDE, scroll_to=True):
        self.page = page
        self.template = template
        self.data = data or {}
        self.on_each_side = on_each_side
        self.scroll_to = scroll_to

    def __call__(self, template=None, data=None, on_each_side=None, scroll_to=None):
        """The same links, asked for with something said about them."""
        return Links(
            self.page,
            template=template if template is not None else self.template,
            data=data if data is not None else self.data,
            on_each_side=self.on_each_side if on_each_side is None else on_each_side,
            scroll_to=self.scroll_to if scroll_to is None else scroll_to,
        )

    def __str__(self):
        return self.render({})

    def render(self, context=None):
        """The markup, rendered from whichever template is to draw it."""
        self.page.scroll_to = self.scroll_to

        template = self._template()
        page_context = {
            "paginator": self.page,
            "page": self.page,
            "on_each_side": self.on_each_side,
            **self.data,
        }

        return template.render(page_context)

    def _template(self):
        """Which template draws the links.

        The one asked for, or the one the project keeps, or the one PyBlade
        ships. A project that has exported the stub is using its own copy from
        then on without having to say so anywhere.
        """
        name = self.template or self.page.template

        if name:
            return loader.load_template(name)

        exported = f"stubs.pagination.{DEFAULT_TEMPLATE}"
        try:
            return loader.load_template(exported)
        except Exception:
            pass

        source, path = _default_template_source()

        return Template(template_name=exported, template_path=path, template_string=source)


class Page:
    """One page of a list, and what a template needs to know about it.

    What Django's paginator answers, under the names the templates use, plus the
    few things it has no opinion about: which query string parameter holds the
    page, and what the links are to do about the address bar.
    """

    #: What a template may call on a page. Everything here only reads: nothing
    #: a template can reach changes the page, the list, or where the links go.
    pb_safe_methods = frozenset({
        "items", "count", "total", "per_page", "first_item", "last_item",
        "current_page", "last_page", "has_pages", "has_more_pages",
        "on_first_page", "on_last_page", "previous_page_number", "next_page_number",
        "window", "url", "get_url_range", "get_page_name", "get_options", "links",
    })

    def __init__(self, django_page, page_name=DEFAULT_PAGE_NAME, path=None, appended=None,
                 query_string=True, template=None):
        self._page = django_page
        self.page_name = page_name
        self.path = path
        self.appended = dict(appended or {})
        self.query_string = query_string
        self.template = template
        self.scroll_to = True

    # What the page holds
    # ------------------------------------------------------------------

    def __iter__(self):
        return iter(self._page.object_list)

    def __len__(self):
        return len(self._page.object_list)

    def __bool__(self):
        return True

    def items(self):
        """The things on this page."""
        return list(self._page.object_list)

    def count(self):
        """How many things are on this page."""
        return len(self._page.object_list)

    def total(self):
        """How many things there are in all."""
        return self._page.paginator.count

    def per_page(self):
        return self._page.paginator.per_page

    def first_item(self):
        """Which number the first thing on this page is, counting from one."""
        return self._page.start_index() or None

    def last_item(self):
        return self._page.end_index() or None

    # Which page this is
    # ------------------------------------------------------------------

    def current_page(self):
        return self._page.number

    def last_page(self):
        return self._page.paginator.num_pages

    def has_pages(self):
        """Whether there is more than one page to walk through at all."""
        return self._page.paginator.num_pages > 1

    def has_more_pages(self):
        return self._page.has_next()

    def on_first_page(self):
        return not self._page.has_previous()

    def on_last_page(self):
        return not self._page.has_next()

    def previous_page_number(self):
        return self._page.previous_page_number() if self._page.has_previous() else None

    def next_page_number(self):
        return self._page.next_page_number() if self._page.has_next() else None

    # The links
    # ------------------------------------------------------------------

    @property
    def links(self):
        return Links(self)

    def window(self, on_each_side=DEFAULT_ON_EACH_SIDE):
        """The page numbers to show: the ones nearest this page.

        The first and last are always among them, with a gap written as None
        where the numbers skip, so a list of four hundred pages is a handful of
        links rather than four hundred.
        """
        last = self.last_page()
        current = self.current_page()

        if last <= (on_each_side * 2) + 5:
            return list(range(1, last + 1))

        nearby = range(max(2, current - on_each_side), min(last - 1, current + on_each_side) + 1)

        numbers = [1]
        if nearby.start > 2:
            numbers.append(None)

        numbers.extend(nearby)

        if nearby.stop - 1 < last - 1:
            numbers.append(None)

        numbers.append(last)

        return numbers

    def url(self, page):
        """Where this page is, for a reader who opens the link in a new tab."""
        query = {**self.appended, self.page_name: page}
        pairs = "&".join(f"{name}={value}" for name, value in query.items())

        return f"{self.path or ''}?{pairs}"

    def get_url_range(self, start, end):
        return {number: self.url(number) for number in range(start, end + 1)}

    # What a component says about the links after it has them
    # ------------------------------------------------------------------

    def with_path(self, path):
        self.path = path
        return self

    def appends(self, **values):
        """Carry something else along in the address bar beside the page."""
        self.appended.update(values)
        return self

    def without_query_string(self):
        """Walk the pages without the address bar saying which one."""
        self.query_string = False
        return self

    def get_page_name(self):
        return self.page_name

    def set_page_name(self, name):
        self.page_name = name
        return self

    def get_options(self):
        return {
            "page_name": self.page_name,
            "path": self.path,
            "appends": dict(self.appended),
            "query_string": self.query_string,
            "template": self.template,
        }


class Paginator(ComponentMixin):
    """Walk a long list a page at a time, from inside a live component.

        class PostList(LiveComponent, Paginator):
            def render(self):
                posts = self.paginate(Post.objects.all(), 25)
                return self.view("post-list", {"posts": posts})

    The page is part of the state of the component, so it survives every round
    trip, and the buttons the links draw call next_page() and the rest as
    ordinary actions.
    """

    #: Which page each paginator is on, by name. Part of the state, so it
    #: travels with everything else the component holds.
    paginators = {DEFAULT_PAGE_NAME: 1}

    def paginate(self, object_list, per_page=10, page_name=DEFAULT_PAGE_NAME, template=None):
        """Take the page of the list the component is on.

        The counting and the slicing are Django's; a queryset is sliced rather
        than read, so a page of twenty-five out of a million is a query for
        twenty-five rows.
        """
        from django.core.paginator import EmptyPage, Paginator as DjangoPaginator

        paginator = DjangoPaginator(object_list, per_page)
        number = self.page_of(page_name)

        # On the first rendering it is the address bar that says which page to
        # show: a link someone was sent, or a page reloaded, comes back to where
        # it was rather than to the beginning. Afterwards the component knows.
        if not getattr(self, "_rerendering", False):
            asked_for = self._page_from_request(page_name)

            if asked_for is not None:
                number = asked_for
                self.paginators = {**self.paginators, page_name: number}

        try:
            django_page = paginator.page(number)
        except EmptyPage:
            # A page that is no longer there -- the list has grown shorter since
            # -- is the last one that is, rather than an error on the screen
            number = max(1, paginator.num_pages)
            self.paginators = {**self.paginators, page_name: number}
            django_page = paginator.page(number)

        page = Page(
            django_page,
            page_name=page_name,
            path=self._pagination_path(),
            template=template,
        )

        # Kept so that the answer can tell the page what the address bar is to
        # say. It is worked out as the component renders, which is the only
        # moment anything knows which paginators there are at all; keyed by
        # name, so a component rendered twice says the same thing once.
        self._paginated = {**getattr(self, "_paginated", {}), page_name: page}

        return page

    def pagination_query(self):
        """What the address bar is to say about the pages being looked at.

        Only the paginators that asked to be in it, and only once the component
        has rendered: until then nothing knows they exist.
        """
        query = {}

        for page in getattr(self, "_paginated", {}).values():
            if not page.query_string:
                continue

            query[page.page_name] = page.current_page()
            query.update({name: str(value) for name, value in page.appended.items()})

        return query

    def pagination_scroll(self):
        """Where to scroll to once another page has been drawn."""
        for page in getattr(self, "_paginated", {}).values():
            if page.scroll_to is not True:
                return page.scroll_to

        return True

    def _page_from_request(self, page_name):
        """Which page the address bar asks for, if it asks for one."""
        request = getattr(self, "request", None)
        asked_for = getattr(request, "GET", {}).get(page_name) if request is not None else None

        try:
            return max(1, int(asked_for))
        except (TypeError, ValueError):
            return None

    def _pagination_path(self):
        """Where the reader is, so a link may be opened in a tab of its own."""
        request = getattr(self, "request", None)

        return getattr(request, "path", None)

    # Which page the component is on
    # ------------------------------------------------------------------

    def page_of(self, page_name=DEFAULT_PAGE_NAME):
        """Which page this paginator is on."""
        try:
            return max(1, int(self.paginators.get(page_name, 1)))
        except (TypeError, ValueError):
            return 1

    def set_page(self, page, page_name=DEFAULT_PAGE_NAME):
        """Go to a page, running whatever watches this paginator."""
        try:
            page = max(1, int(page))
        except (TypeError, ValueError):
            return

        self._call_page_hook("updating", page, page_name)

        # Replaced rather than changed in place: what a component declares is
        # shared by every component of that class until it is
        self.paginators = {**self.paginators, page_name: page}

        self._call_page_hook("updated", page, page_name)

    def reset_page(self, page_name=DEFAULT_PAGE_NAME):
        """Back to the first page, as a new search or a new sort wants."""
        self.set_page(1, page_name)

    def next_page(self, page_name=DEFAULT_PAGE_NAME):
        self.set_page(self.page_of(page_name) + 1, page_name)

    def previous_page(self, page_name=DEFAULT_PAGE_NAME):
        self.set_page(self.page_of(page_name) - 1, page_name)

    def _call_page_hook(self, phase, page, page_name):
        """Run whatever the component wrote to watch a page being changed.

        Three ways of writing it, so a component may say as much or as little
        as it means: about this paginator by name, about the default one, or
        about any of them.
        """
        # Named after the paginator, which for the default one is the
        # updating_page() the docs show
        named = getattr(self, f"{phase}_{page_name}", None)
        if callable(named):
            named(page)

        # Or about any of them, taking the name as its second argument
        every = getattr(self, f"{phase}_paginators", None)
        if callable(every):
            every(page, page_name)
