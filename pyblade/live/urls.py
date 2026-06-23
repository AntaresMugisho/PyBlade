from django.http import JsonResponse
from django.urls import path
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from  pyblade.live import liveBlade


def LiveBladeView(request):
    if request.method == "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    return liveBlade.Live(request)


urlpatterns = [
    path('live/', csrf_exempt(liveBlade.Live), name='live'),
]
