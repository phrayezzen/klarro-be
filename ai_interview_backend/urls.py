from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve


def serve_media(request, path):
    """Serve media files in development."""
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("interviews.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, view=serve_media)
