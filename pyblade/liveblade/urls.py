from django.http import JsonResponse
from django.urls import path
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from  pyblade.liveblade import liveBlade


def LiveBladeView(request):
    if request.method == "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    return liveBlade.LiveBlade(request)


urlpatterns = [
    path('liveblade/', csrf_exempt(liveBlade.LiveBlade), name='liveblade'),
]
