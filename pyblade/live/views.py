import json
from pathlib import Path
from pprint import pprint

from django.http import HttpRequest, HttpResponse, JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.conf import settings as dj_settings
from django.urls import path

from .security import verify_snapshot
from .registry import registry


def serve_assets(request, asset_type: str):
    current_dir = Path(__file__).resolve().parent
    assets_dir = current_dir / "static"

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
        response_data = ComponentClass.update_component(state, action, params, request=request)
    except ValueError as err:
        return JsonResponse({"error": str(err)}, status=404)

    return JsonResponse(response_data)