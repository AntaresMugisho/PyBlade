from django.http import JsonResponse
from django.urls import path
from django.views.generic import TemplateView


class LiveBladeView(TemplateView):
    def post(self, request, *args, **kwargs):
        return JsonResponse({"message": "Hello, Liveblade!"})


urlpatterns = [path("api/liveblade/", LiveBladeView.as_view(), name="liveblade")]
