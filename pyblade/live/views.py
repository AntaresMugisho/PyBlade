import json
import queue
import threading
from pathlib import Path
from pprint import pprint # noqa

from django.http import HttpRequest, HttpResponse, JsonResponse, Http404, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.conf import settings as dj_settings
from django.urls import path

from .security import verify_snapshot
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
            ),
            content_type="application/x-ndjson",
        )

    try:
        response_data = ComponentClass.update_component(
            state, action, params, request=request, known=known, updates=updates, confirmed=confirmed
        )
    except PermissionError as err:
        return JsonResponse({"error": str(err)}, status=403)
    except ValueError as err:
        return JsonResponse({"error": str(err)}, status=404)

    return JsonResponse(response_data)