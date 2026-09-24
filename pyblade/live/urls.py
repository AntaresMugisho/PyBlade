from django.urls import path

from .views import preview_upload, serve_assets, update_component, upload_file

urlpatterns = [
    path("pyblade/live/", update_component, name="pyblade-ajax"),
    path("pyblade/live/upload/", upload_file, name="pyblade-upload"),
    path("pyblade/live/preview/<str:reference>/", preview_upload, name="pyblade-preview"),
    path("pyblade/live/assets/<str:asset_type>/", serve_assets, name="pyblade-assets"),
]
