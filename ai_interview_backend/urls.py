from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve


def debug_serve(request, path, document_root=None, show_indexes=False):
    print("=== Media File Debug ===")
    print(f"Request path: {path}")
    print(f"Document root: {document_root}")
    print(f"Request headers: {dict(request.headers)}")
    print("=====================")
    return serve(request, path, document_root, show_indexes)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("interviews.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, view=debug_serve)
