from django.urls import path

from apps.accounts.views import (
    AdminUserListView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    MeView,
    RegisterView,
)

urlpatterns = [
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("login/refresh/", CustomTokenRefreshView.as_view(), name="login-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("register/", RegisterView.as_view(), name="register"),
    path("users/", AdminUserListView.as_view(), name="admin-user-list"),
]
