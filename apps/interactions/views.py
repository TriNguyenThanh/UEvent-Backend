from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.events.models import Event
from apps.interactions.models import EventFeedback, EventQuestion
from apps.interactions.permissions import IsInteractionOwner
from apps.interactions.serializers import (
    EventFeedbackSerializer,
    EventQuestionSerializer,
    QuestionAnswerSerializer,
)
from common.serializers import ApiErrorResponseSerializer


INTERACTION_ERROR_RESPONSES = {
    400: ApiErrorResponseSerializer(),
    401: ApiErrorResponseSerializer(),
    403: ApiErrorResponseSerializer(),
    404: ApiErrorResponseSerializer(),
}


def is_event_organizer(user, event):
    if not user or not user.is_authenticated:
        return False
    if event.created_by_id == user.id or user.is_superuser:
        return True
    return event.organizers.filter(user=user).exists()


def assert_event_organizer(request, event):
    if not is_event_organizer(request.user, event):
        raise PermissionDenied("You do not have organizer access to this event.")


class EventFeedbackListCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/events/{event_id}/feedbacks/
    POST /api/v1/events/{event_id}/feedbacks/

    Organizers can list feedbacks. Registered users can submit feedback after
    the event is finished.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = EventFeedbackSerializer

    def get_event(self):
        return get_object_or_404(Event.objects.prefetch_related("organizers"), id=self.kwargs["event_id"])

    def get_queryset(self):  # type: ignore[override]
        event = self.get_event()
        if self.request.method == "GET":
            assert_event_organizer(self.request, event)
        return EventFeedback.objects.filter(event=event).select_related("event", "user").order_by("-created_at")

    @swagger_auto_schema(
        operation_summary="List Event Feedbacks",
        operation_description="Organizer xem danh sách feedback của sự kiện.",
        responses={200: EventFeedbackSerializer(many=True), **INTERACTION_ERROR_RESPONSES},
        tags=["Feedbacks"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Event Feedback",
        operation_description="User gửi feedback sau sự kiện.",
        request_body=EventFeedbackSerializer,
        responses={201: EventFeedbackSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Feedbacks"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["event_id"] = self.kwargs["event_id"]
        return context

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class EventFeedbackSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get Feedback Summary",
        operation_description="Organizer xem thống kê rating của feedback trong sự kiện.",
        responses={200: openapi.Response(description="Feedback summary"), **INTERACTION_ERROR_RESPONSES},
        tags=["Feedbacks"],
    )
    def get(self, request, event_id):
        event = get_object_or_404(Event.objects.prefetch_related("organizers"), id=event_id)
        assert_event_organizer(request, event)
        queryset = EventFeedback.objects.filter(event=event)
        summary = queryset.aggregate(total=Count("id"), average_rating=Avg("rating"))
        rating_counts = {
            item["rating"]: item["count"]
            for item in queryset.exclude(rating__isnull=True).values("rating").annotate(count=Count("id"))
        }
        return Response(
            {
                "event_id": str(event.id),
                "total": summary["total"],
                "average_rating": summary["average_rating"],
                "rating_counts": {str(score): rating_counts.get(score, 0) for score in range(1, 6)},
            },
            status=status.HTTP_200_OK,
        )


class FeedbackDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsInteractionOwner]
    serializer_class = EventFeedbackSerializer

    @swagger_auto_schema(
        operation_summary="Get Feedback Detail",
        operation_description="Lấy chi tiết feedback theo id.",
        responses={200: EventFeedbackSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Feedbacks"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Feedback",
        operation_description="Cập nhật feedback (chỉ owner).",
        request_body=EventFeedbackSerializer,
        responses={200: EventFeedbackSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Feedbacks"],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Replace Feedback",
        operation_description="Cập nhật toàn bộ feedback (PUT, chỉ owner).",
        request_body=EventFeedbackSerializer,
        responses={200: EventFeedbackSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Feedbacks"],
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete Feedback",
        operation_description="Xóa feedback (chỉ owner).",
        responses={204: openapi.Response(description="Xóa feedback thành công."), **INTERACTION_ERROR_RESPONSES},
        tags=["Feedbacks"],
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):  # type: ignore[override]
        return EventFeedback.objects.select_related("event", "user")


class EventQuestionListCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/events/{event_id}/questions/
    POST /api/v1/events/{event_id}/questions/

    Organizers can list all questions. Authenticated users can submit questions.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = EventQuestionSerializer

    def get_event(self):
        return get_object_or_404(Event.objects.prefetch_related("organizers"), id=self.kwargs["event_id"])

    def get_queryset(self):  # type: ignore[override]
        event = self.get_event()
        if self.request.method == "GET":
            assert_event_organizer(self.request, event)
        return (
            EventQuestion.objects.filter(event=event)
            .select_related("event", "user", "answered_by")
            .order_by("-is_pinned", "-asked_at", "-created_at")
        )

    @swagger_auto_schema(
        operation_summary="List Event Questions",
        operation_description="Organizer xem danh sách câu hỏi của sự kiện.",
        responses={200: EventQuestionSerializer(many=True), **INTERACTION_ERROR_RESPONSES},
        tags=["Questions"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Event Question",
        operation_description="User gửi câu hỏi cho BTC.",
        request_body=EventQuestionSerializer,
        responses={201: EventQuestionSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Questions"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["event_id"] = self.kwargs["event_id"]
        return context

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class EventPublicQuestionListView(generics.ListAPIView):
    """
    GET /api/v1/events/{event_id}/questions/public/

    Lists visible public questions for authenticated users.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = EventQuestionSerializer

    @swagger_auto_schema(
        operation_summary="List Public Event Questions",
        operation_description="User xem danh sách câu hỏi đang hiển thị công khai.",
        responses={200: EventQuestionSerializer(many=True), **INTERACTION_ERROR_RESPONSES},
        tags=["Questions"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):  # type: ignore[override]
        return (
            EventQuestion.objects.filter(
                event_id=self.kwargs["event_id"],
                moderation_status=EventQuestion.ModerationStatus.VISIBLE,
            )
            .select_related("event", "user", "answered_by")
            .order_by("-is_pinned", "-asked_at", "-created_at")
        )


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsInteractionOwner]
    serializer_class = EventQuestionSerializer

    @swagger_auto_schema(
        operation_summary="Get Question Detail",
        operation_description="Lấy chi tiết câu hỏi theo id.",
        responses={200: EventQuestionSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Questions"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Question",
        operation_description="Cập nhật câu hỏi (chỉ owner).",
        request_body=EventQuestionSerializer,
        responses={200: EventQuestionSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Questions"],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Replace Question",
        operation_description="Cập nhật toàn bộ câu hỏi (PUT, chỉ owner).",
        request_body=EventQuestionSerializer,
        responses={200: EventQuestionSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Questions"],
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete Question",
        operation_description="Xóa câu hỏi (chỉ owner).",
        responses={204: openapi.Response(description="Xóa câu hỏi thành công."), **INTERACTION_ERROR_RESPONSES},
        tags=["Questions"],
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):  # type: ignore[override]
        return EventQuestion.objects.select_related("event", "user", "answered_by")


class QuestionAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Answer Question",
        operation_description="Organizer trả lời câu hỏi.",
        request_body=QuestionAnswerSerializer,
        responses={200: EventQuestionSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Questions"],
    )
    def patch(self, request, question_id):
        question = get_object_or_404(
            EventQuestion.objects.select_related("event", "user", "answered_by"),
            id=question_id,
        )
        assert_event_organizer(request, question.event)
        serializer = QuestionAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question.answer_text = serializer.validated_data["answer_text"]
        question.answered_by = request.user
        question.answered_at = timezone.now()
        question.save(update_fields=["answer_text", "answered_by", "answered_at", "updated_at"])
        return Response(EventQuestionSerializer(question).data, status=status.HTTP_200_OK)


class QuestionPinView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Pin Question",
        operation_description="Organizer ghim câu hỏi.",
        responses={200: EventQuestionSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Questions"],
    )
    def patch(self, request, question_id):
        question = get_object_or_404(EventQuestion.objects.select_related("event", "user"), id=question_id)
        assert_event_organizer(request, question.event)
        question.is_pinned = True
        question.save(update_fields=["is_pinned", "updated_at"])
        return Response(EventQuestionSerializer(question).data, status=status.HTTP_200_OK)


class QuestionHideView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Hide Question",
        operation_description="Organizer ẩn câu hỏi khỏi danh sách public.",
        responses={200: EventQuestionSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Questions"],
    )
    def patch(self, request, question_id):
        question = get_object_or_404(EventQuestion.objects.select_related("event", "user"), id=question_id)
        assert_event_organizer(request, question.event)
        question.moderation_status = EventQuestion.ModerationStatus.HIDDEN
        question.save(update_fields=["moderation_status", "updated_at"])
        return Response(EventQuestionSerializer(question).data, status=status.HTTP_200_OK)
