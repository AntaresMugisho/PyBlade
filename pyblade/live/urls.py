from django.urls import path

from .views import serve_assets, update_component

urlpatterns = [
    path("pyblade/live/", update_component, name="pyblade-ajax"),
    path("pyblade/live/assets/<str:asset_type>/", serve_assets, name="pyblade-assets"),
]
