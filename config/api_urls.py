from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    path("academics/", include("apps.academics.urls")),
    path("admissions/", include("apps.admissions.urls")),
    path("finance/", include("apps.finance.urls")),
    path("content/", include("apps.content.urls")),
    path("assistant/", include("apps.assistant.urls")),
]
