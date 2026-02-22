from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("tenant/dashboard/", views.tenant_dashboard, name="tenant_dashboard"),
    path("landlord/dashboard/", views.landlord_dashboard, name="landlord_dashboard"),
    path("role-redirect/", views.role_redirect, name="role_redirect"),
    path("start-browsing/", views.start_browsing, name="start_browsing"),
]
