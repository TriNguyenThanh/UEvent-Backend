# apps/registrations/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.registrations.views import (
	CheckinScanAPIView,
	EventCohostCollectionAPIView,
	EventCohostDetailAPIView,
	TicketViewSet,
)

router = DefaultRouter()
router.register("tickets", TicketViewSet, basename="tickets")

urlpatterns = [
	path("", include(router.urls)),
	path("checkin/scan/", CheckinScanAPIView.as_view(), name="checkin-scan"),
	path(
		"events/<uuid:event_id>/cohosts/",
		EventCohostCollectionAPIView.as_view(),
		name="event-cohosts",
	),
	path(
		"events/<uuid:event_id>/cohosts/<uuid:user_id>/",
		EventCohostDetailAPIView.as_view(),
		name="event-cohost-detail",
	),
]
