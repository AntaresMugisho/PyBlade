import json
import logging
import queue
import threading
from pathlib import Path
from pprint import pprint # noqa

from django.http import (HttpRequest, HttpResponse, JsonResponse, FileResponse, Http404,
                         StreamingHttpResponse)
from django.views.decorators.http import require_POST
from django.conf import settings as dj_settings
from django.urls import path

from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError

from pyblade.engine.renderer import error_page

from .security import verify_snapshot
from .throttle import stream_slots, throttled
from .uploads import (MultipleFileField, REFERENCE_PREFIX, TemporaryUpload, store_temporarily,
                      sweep_if_due)
from .registry import ComponentNotFound, registry

logger = logging.getLogger("pyblade.live")

#: What the page is told about an error in production, where what went wrong
#: is for the server's logs and not for whoever is looking at the page
GENERIC_ERROR = "Something went wrong on the server."

#: The types a preview is shown as rather than downloaded: pictures a browser
#: draws and does nothing else with. SVG is not one of them: it can hold scripts.
SHOWN_INLINE = frozenset({
    "image/png", "image/jpeg", "image/gif", "image/webp", "image/avif", "image/bmp",
    "image/x-icon", "image/vnd.microsoft.icon",
})


def serve_assets(request: HttpRequest, asset_type: str):
    assets_dir = Path(__file__).resolve().parent / "static"

    if asset_type == "js":
        js_file_path = assets_dir / "pyblade.min.js"
        with open(js_file_path, "rb") as f:
            content = f.read()
        
        return HttpResponse(content, content_type="text/javascript")

    elif asset_type == "css":
        css_file_path = assets_dir / "pyblade.css"
        with open(css_file_path, "rb") as f:
            content = f.read()

        return HttpResponse(content, content_type="text/css")

    return Http404(f"Pyblade {asset_type} assets not found.")


@require_POST
# A file's size is the component's to decide, with MaxFileSize, so only the
# rate is counted here
@throttled("uploads", check_size=False)
def upload_file(request: HttpRequest) -> JsonResponse:
    """Take a file for a property of a component, before any action runs.

    A file arrives on a request of its own so that it can be watched while it
    goes and stopped part way, which is not something a request carrying the
    whole answer could offer.

    What arrives is checked against the very field the component declares for
    that property -- so an ImageField refuses what is not an image, and
    MaxFileSize refuses what is too big -- and it is refused before its bytes
    are kept rather than after.
    """
    # Taking a file is also when the ones nobody came back for are thrown
    # away: a project that takes uploads tidies up after itself, with nothing
    # to schedule and nothing to install. It happens at most once an hour.
    sweep_if_due()

    uploaded = request.FILES.getlist("file")
    if not uploaded:
        return JsonResponse({"error": "No file was sent."}, status=400)

    try:
        snapshot = json.loads(request.POST.get("snapshot") or "")
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"error": "Invalid PyBlade snapshot."}, status=400)

    # A file is taken for a page PyBlade rendered, and for no other: without
    # this the endpoint would be somewhere for anyone to keep their files
    try:
        verify_snapshot(snapshot)
    except (ValueError, AttributeError) as err:
        return JsonResponse({"error": str(err)}, status=400)

    try:
        ComponentClass = registry.get(snapshot.get("class"))
    except ValueError as err:
        return JsonResponse({"error": str(err)}, status=404)

    property_name = request.POST.get("property") or ""
    field = _upload_field(ComponentClass, property_name)

    if field is None:
        return JsonResponse(
            {"errors": [
                f"The {ComponentClass.__name__} component does not take a file "
                f"for '{property_name}'."
            ]},
            status=422,
        )

    # A field asking for one file is given the file rather than the list, so
    # that what it is handed here is what a form would hand it
    if not isinstance(field, MultipleFileField):
        if len(uploaded) > 1:
            return JsonResponse(
                {"errors": [
                    f"The {ComponentClass.__name__} component takes one file for "
                    f"'{property_name}', not several."
                ]},
                status=422,
            )

        uploaded = uploaded[0]

    try:
        field.clean(uploaded, None)
    except DjangoValidationError as err:
        return JsonResponse({"errors": [str(message) for message in err.messages]}, status=422)

    # Answered as a list however many were sent: what the property is to hold --
    # one file or several -- is the page's to decide, from the input it read
    # them off.
    files = uploaded if isinstance(uploaded, list) else [uploaded]
    kept = [store_temporarily(one) for one in files]

    return JsonResponse({"files": [
        {
            "reference": upload.reference,
            "name": upload.name,
            "size": upload.size,
            "content_type": upload.content_type,
        }
        for upload in kept
    ]})


def in_development():
    """Whether the project is being run by whoever is writing it."""
    return bool(dj_settings.DEBUG)


def gone_wrong(error):
    """What the page is told about an error nobody caught.

    The error page comes back with the message, so the browser can show it over
    the page the developer is working on. It is built here and not in
    production: what it holds -- paths on the machine that is serving, the code
    around the line, the frames it came through -- is for whoever is writing the
    code and for nobody else.
    """
    template = getattr(error, "template", None)

    return {
        "error": str(error),
        "page": error_page(
            error,
            template_source=getattr(template, "content", None),
            template_path=getattr(template, "path", None),
        ),
    }


def preview_upload(request: HttpRequest, reference: str):
    """Hand over a file that has been sent but not kept, so it can be shown.

    A preview has to read the bytes from somewhere, and the temporary directory
    is the one place they are. Serving it from here rather than from the media
    path means a file nobody has kept yet is reachable only by the note the
    page was given -- signed, and no older than the note is allowed to be.
    """
    upload = TemporaryUpload.from_reference(REFERENCE_PREFIX + reference)

    if upload is None:
        raise Http404("That file is not one PyBlade is holding.")

    try:
        handle = upload.open()
    except (FileNotFoundError, OSError):
        raise Http404("That file is no longer here.")

    # The type is what the browser that sent the file said it was, which is
    # anybody's to say. It is shown on this site only when it is a picture a
    # browser draws and nothing more; anything else -- a page, an SVG, a PDF --
    # could run a script here, on the site's own address, so it is handed over
    # to be downloaded instead.
    if upload.content_type in SHOWN_INLINE:
        response = FileResponse(handle, content_type=upload.content_type)
    else:
        response = FileResponse(
            handle, content_type="application/octet-stream", as_attachment=True, filename=upload.name,
        )

    # And the browser is told to take the type at its word rather than guess
    # it from the bytes, and to run nothing that is in it whatever it is
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; img-src 'self'; sandbox"

    # A file on its way belongs to the reader who sent it and to nobody else,
    # least of all to a cache between them
    response["Cache-Control"] = "private, max-age=0, no-store"

    return response


def _upload_field(ComponentClass, property_name):
    """The field a component declares for a property, when it takes a file.

    The name comes from the page, so it is only ever looked up among the fields
    the component declares: nothing else is a property a file may be sent for,
    least of all the machinery a component runs on.
    """
    if not property_name or ComponentClass._is_reserved(property_name):
        return None

    form_class = ComponentClass._validation_form()
    if form_class is None:
        return None

    field = form_class.base_fields.get(property_name)

    return field if isinstance(field, forms.FileField) else None


class _HoldingASlot:
    """A streamed answer, which gives its slot back even if it never starts.

    The thread a streamed action runs on gives the slot back when it ends. But
    that thread is only started once the answer starts being written, and a
    client that has gone before then leaves nothing to start it -- so the slot
    would be held for ever, and enough of those would leave no slot for anyone.
    Django closes every answer once it is done with it; this is what makes
    closing one that never started give the slot back.
    """

    def __init__(self, answer):
        self._answer = answer
        self._started = False
        self._closed = False

    def __iter__(self):
        return self

    def __next__(self):
        # From the first piece on, the thread holds the slot and gives it back
        self._started = True
        return next(self._answer)

    def close(self):
        if self._closed:
            return
        self._closed = True

        if not self._started:
            stream_slots.give_back()

        self._answer.close()


def streamed_response(ComponentClass, state, action, params=None, **kwargs):
    """The answer of an action written @streamed, a line of JSON at a time.

    An ordinary function cannot hand anything over in the middle of itself, so
    the action is run beside this rather than before it: it pushes what it
    streams onto a queue, and what is taken off the queue is written out as it
    arrives. The answer -- the new markup and the new state -- is the last line.

    Every line is one JSON object and ends in a newline, so that a client
    reading the response in pieces can tell where each one ends however the
    pieces happen to fall.
    """
    chunks = queue.Queue()
    outcome = {}

    #: Put on the queue once the action is done, there being nothing more to come
    DONE = object()

    def run():
        try:
            outcome["response"] = ComponentClass.update_component(
                state, action, params or [], sink=chunks.put, **kwargs
            )
        except Exception as error:  # noqa: BLE001 - reported to the client below
            outcome["error"] = error
        finally:
            # The thread has a database connection of its own, and the server
            # keeps it open for a thread that never asks for it to be closed
            try:
                from django.db import close_old_connections

                close_old_connections()
            except Exception:  # noqa: BLE001 - a project without a database
                pass

            stream_slots.give_back()
            chunks.put(DONE)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()

    while True:
        chunk = chunks.get()
        if chunk is DONE:
            break

        yield json.dumps({"stream": chunk}) + "\n"

    worker.join()

    if "error" in outcome:
        # A stream has already begun answering, so an error cannot be a status
        # code any more: it is the last line, with the page where there is one
        error = outcome["error"]

        if in_development():
            answer = gone_wrong(error)
        elif isinstance(error, PermissionError):
            # A refusal is said out loud, as the 403 of an ordinary action is
            answer = {"error": str(error)}
        else:
            # An ordinary action that fails ends in Django's own 500, which
            # tells the page nothing and logs the rest. A stream has already
            # begun answering, so it does the same by hand.
            logger.error("A streamed action failed.", exc_info=error)
            answer = {"error": GENERIC_ERROR}

        yield json.dumps(answer) + "\n"
    else:
        yield json.dumps(outcome["response"]) + "\n"


@require_POST
@throttled("actions")
def update_component(request: HttpRequest) -> JsonResponse:
    """
    HTTP endpoint handling AJAX actions for PyBlade components.
    Re-hydrates component state from client snapshot, invokes custom methods,
    and returns updated HTML for Idiomorph DOM morphing.
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)


    snapshot = payload.get("snapshot", {})
    action = payload.get("action")
    params = payload.get("params", [])

    # The components the page says it holds. Only ever used to leave one where
    # it is, so a client saying anything else only shortchanges itself.
    known = payload.get("known", [])
    if not isinstance(known, list):
        known = []

    # What the page holds and has not sent yet: the fields written pb:model
    updates = payload.get("updates")

    # The page saying the reader was asked before a @confirm action was called
    confirmed = payload.get("confirmed") is True

    # Verify if snapshot was not tempared
    try:
        verify_snapshot(snapshot)
    except ValueError as err:
        return JsonResponse({"error": str(err)}, status=400)

    # Resolve the actual custom component class from the registry
    class_path = snapshot.get("class")
    component_id = snapshot.get("id")
    state = snapshot.get("state", {}) | {"_id": component_id}

    # What was wrong when the component was last checked, signed with the rest
    errors = snapshot.get("errors")

    # What a lazy component is to be mounted with, signed with the rest. Its
    # presence is the component saying it has not done its work yet.
    mount = snapshot.get("mount")

    try:
        ComponentClass = registry.get(class_path)
    except ValueError as err:
        return JsonResponse({"error": str(err)}, status=404)

    # An action that answers as it goes is written out as it goes, rather than
    # built whole and handed over at the end
    if ComponentClass._streams_from(action):
        # Each one is a thread for as long as it runs, so only so many at once:
        # enough requests for them would otherwise run the server out of threads
        if not stream_slots.take():
            response = JsonResponse(
                {"error": "The server is busy answering others. Try again in a moment."}, status=429
            )
            response["Retry-After"] = "5"
            return response

        return StreamingHttpResponse(
            _HoldingASlot(streamed_response(
                ComponentClass, state, action, params,
                request=request, known=known, updates=updates, confirmed=confirmed,
                errors=errors, mount=mount,
            )),
            content_type="application/x-ndjson",
        )

    try:
        response_data = ComponentClass.update_component(
            state, action, params, request=request, known=known, updates=updates,
            confirmed=confirmed, errors=errors, mount=mount,
        )
    except PermissionError as err:
        return JsonResponse({"error": str(err)}, status=403)
    except Exception as err:
        # While developing, anything nobody caught comes back as the error page
        # rather than as the framework's own: it is the page for what went
        # wrong here, and the browser shows it over the page being worked on.
        if in_development():
            return JsonResponse(gone_wrong(err), status=500)

        # A component the registry does not know is not a server error. Only
        # that: a ValueError the component raises itself is an error like any
        # other, and its message is for the logs, not for the page.
        if isinstance(err, ComponentNotFound):
            return JsonResponse({"error": "That component could not be found."}, status=404)

        raise

    return JsonResponse(response_data)