import json
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

from .security import verify_snapshot
from .uploads import (MultipleFileField, REFERENCE_PREFIX, TemporaryUpload, store_temporarily,
                      sweep_if_due)
from .registry import registry


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

    response = FileResponse(handle, content_type=upload.content_type)

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
        yield json.dumps({"error": str(outcome["error"])}) + "\n"
    else:
        yield json.dumps(outcome["response"]) + "\n"


@require_POST
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
        return StreamingHttpResponse(
            streamed_response(
                ComponentClass, state, action, params,
                request=request, known=known, updates=updates, confirmed=confirmed,
                errors=errors, mount=mount,
            ),
            content_type="application/x-ndjson",
        )

    try:
        response_data = ComponentClass.update_component(
            state, action, params, request=request, known=known, updates=updates,
            confirmed=confirmed, errors=errors, mount=mount,
        )
    except PermissionError as err:
        return JsonResponse({"error": str(err)}, status=403)
    except ValueError as err:
        return JsonResponse({"error": str(err)}, status=404)

    return JsonResponse(response_data)