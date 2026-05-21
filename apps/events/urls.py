from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("event-categories/", views.PublicEventCategoryListView.as_view(), name="public-event-category-list"),
    path("events/search/", views.PublicEventSearchView.as_view(), name="public-event-search"),
    path("events/me/highlights/", views.MyEventHighlightsView.as_view(), name="my-event-highlights"),
    path("organizer/events/", views.OrganizerEventListCreateView.as_view(), name="organizer-event-list"),
    path(
        "organizer/events/presigned-url/",
        views.OrganizerEventPresignedUrlView.as_view(),
        name="organizer-event-presigned-url",
    ),
    path("organizer/events/<uuid:pk>/", views.OrganizerEventDetailUpdateDeleteView.as_view(), name="organizer-event-detail"),
]
