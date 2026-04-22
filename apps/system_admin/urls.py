from django.urls import path
from .views import user_views as views

app_name = "system_admin"

urlpatterns = [
    path("users/", views.AdminUserListView.as_view(), name="user-list"),
    path("users/<uuid:pk>/", views.AdminUserDetailUpdateDeleteView.as_view(), name="user-detail"),
    path("users/<uuid:pk>/ban/", views.AdminBanUserView.as_view(), name="user-ban"),
    path("users/<uuid:pk>/unban/", views.AdminUnbanUserView.as_view(), name="user-unban"),
    path("users/<uuid:pk>/restore/", views.AdminRestoreUserView.as_view(), name="user-restore"),
    path("users/<uuid:pk>/roles/", views.AdminAssignRoleView.as_view(), name="user-roles"),
    path("users/<uuid:pk>/roles/<str:role_code>/", views.AdminRemoveRoleView.as_view(), name="user-role-remove"),
]
