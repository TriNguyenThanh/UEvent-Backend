from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.registrations.models import EventRegistration
from apps.registrations.permissions import IsRegistrationOwner
from apps.registrations.serializers import (
    RegistrationCreateSerializer,
    RegistrationListSerializer,
    RegistrationQrSerializer,
)
from apps.registrations.services import create_event_registration, issue_registration_qr

class RegistrationListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RegistrationListSerializer

    def get_queryset(self): # type: ignore
        return (
            EventRegistration.objects.filter(user=self.request.user)
            .select_related("event", "ticket")
            .order_by("-registered_at", "-created_at")
        )

    def create(self, request, *args, **kwargs):
        serializer = RegistrationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration = create_event_registration(
            user=request.user,
            event_id=serializer.validated_data["event_id"],
        )
        response_serializer = RegistrationListSerializer(registration)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class RegistrationQrAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRegistrationOwner]

    def get(self, request, id):
        registration = get_object_or_404(
            EventRegistration.objects.select_related("event", "ticket"),
            id=id,
        )
        self.check_object_permissions(request, registration)

        qr_data = issue_registration_qr(registration=registration)
        serializer = RegistrationQrSerializer(qr_data)
        return Response(serializer.data, status=status.HTTP_200_OK)