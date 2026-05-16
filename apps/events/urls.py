from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("organizer/events/", views.OrganizerEventListCreateView.as_view(), name="organizer-event-list"),
    path("organizer/events/<uuid:pk>/", views.OrganizerEventDetailUpdateDeleteView.as_view(), name="organizer-event-detail"),
]
