from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_urls")),
    path("portal/", include("apps.portal.urls")),
    path("", include("apps.website.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns.append(path("__debug__/", include(debug_toolbar.urls)))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
