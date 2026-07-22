import json

from django.http import JsonResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from pyblade.live import Component

# from pyblade.live import Live

from pathlib import Path
from django.http import HttpResponse, Http404

def serve_assets(request):
    current_dir = Path(__file__).resolve().parent
    js_file_path = current_dir / "static" / "pyblade.min.js"

    if not js_file_path.exists():
        raise Http404("Fichier pyblade.min.js introuvable")

    with open(js_file_path, "rb") as f:
        content = f.read()

    return HttpResponse(content, content_type="application/javascript")


def update_component(request):
    data = json.loads(request.body)

    from pprint import pprint

    component_id = data.get('id')
    snapshot = data.get('state')
    action = data.get('action')

    if snapshot is None:
        snapshot = {}

    print("DATA \n")
    pprint(data)

    new_data = Component.handle_ajax_action(component_id, snapshot, action)

    return JsonResponse(dict(new_data))


urlpatterns = [
    path("pyblade/live/", update_component, name="pyblade-ajax"),
    path("pyblade/live/assets/pyblade.js", serve_assets, name="pyblade-assets"),
]
