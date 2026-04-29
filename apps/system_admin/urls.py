from django.urls import path
from .views import user_views, auth_views

app_name = "system_admin"

urlpatterns = [
    # Auth
    path("auth/login/", auth_views.AdminLoginView.as_view(), name="admin-login"),
    path("auth/refresh/", auth_views.AdminTokenRefreshView.as_view(), name="admin-token-refresh"),
    path("auth/me/", auth_views.AdminMeView.as_view(), name="admin-me"),

    # User Management
    path("users/", user_views.AdminUserListView.as_view(), name="user-list"),
    path("users/statistics/", user_views.AdminUserStatisticsView.as_view(), name="user-statistics"),
    path("users/<uuid:pk>/", user_views.AdminUserDetailUpdateDeleteView.as_view(), name="user-detail"),
    path("users/<uuid:pk>/ban/", user_views.AdminBanUserView.as_view(), name="user-ban"),
    path("users/<uuid:pk>/unban/", user_views.AdminUnbanUserView.as_view(), name="user-unban"),
    path("users/<uuid:pk>/restore/", user_views.AdminRestoreUserView.as_view(), name="user-restore"),
    # path("users/<uuid:pk>/roles/", user_views.AdminAssignRoleView.as_view(), name="user-roles"),
    # path("users/<uuid:pk>/roles/<str:role_code>/", user_views.AdminRemoveRoleView.as_view(), name="user-role-remove"),
]
