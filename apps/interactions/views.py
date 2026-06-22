import hashlib
import logging

from django.db import transaction
from django.db.models import Avg, Count, Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.events.models import Event
from apps.interactions.models import (
    AIQuestionAnswerJob,
    # EventFeedback,
    EventAIQASetting,
    EventQuestion,
    EventQuestionReply,
)
from apps.interactions.permissions import IsInteractionOwner
from apps.interactions.serializers import (
    # EventFeedbackSerializer,
    EventAIAssistantToggleSerializer,
    EventQuestionSerializer,
    EventQuestionReplySerializer,
    OrganizerEventQuestionSerializer,
    QuestionAnswerSerializer,
)
from common.serializers import ApiErrorResponseSerializer

INTERACTION_ERROR_RESPONSES = {
    400: ApiErrorResponseSerializer(),
    401: ApiErrorResponseSerializer(),
    403: ApiErrorResponseSerializer(),
    404: ApiErrorResponseSerializer(),
}

logger = logging.getLogger(__name__)


def is_event_organizer(user, event):
    if not user or not user.is_authenticated:
        return False
    if event.created_by_id == user.id or user.is_superuser:
        return True
    return event.organizers.filter(user=user).exists()


def assert_event_organizer(request, event):
    if not is_event_organizer(request.user, event):
        raise PermissionDenied("You do not have organizer access to this event.")


# class EventFeedbackListCreateView(generics.ListCreateAPIView):
#     """
#     GET /api/v1/events/{event_id}/feedbacks/
#     POST /api/v1/events/{event_id}/feedbacks/

#     Organizers can list feedbacks. Registered users can submit feedback after
#     the event is finished.
#     """
#     permission_classes = [IsAuthenticated]
#     serializer_class = EventFeedbackSerializer

#     def get_event(self):
#         return get_object_or_404(Event.objects.prefetch_related("organizers"), id=self.kwargs["event_id"])

#     def get_queryset(self):  # type: ignore[override]
#         event = self.get_event()
#         if self.request.method == "GET":
#             assert_event_organizer(self.request, event)
#         return EventFeedback.objects.filter(event=event).select_related("event", "user").order_by("-created_at")

#     @swagger_auto_schema(
#         operation_summary="List Event Feedbacks",
#         operation_description="Organizer xem danh sách feedback của sự kiện.",
#         responses={200: EventFeedbackSerializer(many=True), **INTERACTION_ERROR_RESPONSES},
#         tags=["Feedbacks"],
#     )
#     def get(self, request, *args, **kwargs):
#         return super().get(request, *args, **kwargs)

#     @swagger_auto_schema(
#         operation_summary="Create Event Feedback",
#         operation_description="User gửi feedback sau sự kiện.",
#         request_body=EventFeedbackSerializer,
#         responses={201: EventFeedbackSerializer(), **INTERACTION_ERROR_RESPONSES},
#         tags=["Feedbacks"],
#     )
#     def post(self, request, *args, **kwargs):
#         return super().post(request, *args, **kwargs)

#     def get_serializer_context(self):
#         context = super().get_serializer_context()
#         context["event_id"] = self.kwargs["event_id"]
#         return context

#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user)


# class EventFeedbackSummaryView(APIView):
#     permission_classes = [IsAuthenticated]

#     @swagger_auto_schema(
#         operation_summary="Get Feedback Summary",
#         operation_description="Organizer xem thống kê rating của feedback trong sự kiện.",
#         responses={200: openapi.Response(description="Feedback summary"), **INTERACTION_ERROR_RESPONSES},
#         tags=["Feedbacks"],
#     )
#     def get(self, request, event_id):
#         event = get_object_or_404(Event.objects.prefetch_related("organizers"), id=event_id)
#         assert_event_organizer(request, event)
#         queryset = EventFeedback.objects.filter(event=event)
#         summary = queryset.aggregate(total=Count("id"), average_rating=Avg("rating"))
#         rating_counts = {
#             item["rating"]: item["count"]
#             for item in queryset.exclude(rating__isnull=True).values("rating").annotate(count=Count("id"))
#         }
#         return Response(
#             {
#                 "event_id": str(event.id),
#                 "total": summary["total"],
#                 "average_rating": summary["average_rating"],
#                 "rating_counts": {str(score): rating_counts.get(score, 0) for score in range(1, 6)},
#             },
#             status=status.HTTP_200_OK,
#         )


# class FeedbackDetailView(generics.RetrieveUpdateDestroyAPIView):
#     permission_classes = [IsAuthenticated, IsInteractionOwner]
#     serializer_class = EventFeedbackSerializer

#     @swagger_auto_schema(
#         operation_summary="Get Feedback Detail",
#         operation_description="Lấy chi tiết feedback theo id.",
#         responses={200: EventFeedbackSerializer(), **INTERACTION_ERROR_RESPONSES},
#         tags=["Feedbacks"],
#     )
#     def get(self, request, *args, **kwargs):
#         return super().get(request, *args, **kwargs)

#     @swagger_auto_schema(
#         operation_summary="Update Feedback",
#         operation_description="Cập nhật feedback (chỉ owner).",
#         request_body=EventFeedbackSerializer,
#         responses={200: EventFeedbackSerializer(), **INTERACTION_ERROR_RESPONSES},
#         tags=["Feedbacks"],
#     )
#     def patch(self, request, *args, **kwargs):
#         return super().patch(request, *args, **kwargs)

#     @swagger_auto_schema(
#         operation_summary="Replace Feedback",
#         operation_description="Cập nhật toàn bộ feedback (PUT, chỉ owner).",
#         request_body=EventFeedbackSerializer,
#         responses={200: EventFeedbackSerializer(), **INTERACTION_ERROR_RESPONSES},
#         tags=["Feedbacks"],
#     )
#     def put(self, request, *args, **kwargs):
#         return super().put(request, *args, **kwargs)

#     @swagger_auto_schema(
#         operation_summary="Delete Feedback",
#         operation_description="Xóa feedback (chỉ owner).",
#         responses={204: openapi.Response(description="Xóa feedback thành công."), **INTERACTION_ERROR_RESPONSES},
#         tags=["Feedbacks"],
#     )
#     def delete(self, request, *args, **kwargs):
#         return super().delete(request, *args, **kwargs)

#     def get_queryset(self):  # type: ignore[override]
#         return EventFeedback.objects.select_related("event", "user")


class EventQuestionListCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/events/{event_id}/questions/
    POST /api/v1/events/{event_id}/questions/

    Organizers can list all questions. Authenticated users can submit questions.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = EventQuestionSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            return OrganizerEventQuestionSerializer
        return EventQuestionSerializer

    def get_event(self):
        return get_object_or_404(Event.objects.prefetch_related("organizers"), id=self.kwargs["event_id"])

    def get_queryset(self):  # type: ignore[override]
        event = self.get_event()
        if self.request.method == "GET":
            assert_event_organizer(self.request, event)
        return (
            EventQuestion.objects.filter(event=event)
            .select_related("event", "user", "answered_by", "ai_answer_job")
            .prefetch_related(
                Prefetch(
                    "replies",
                    queryset=EventQuestionReply.objects.select_related(
                        "user"
                    ).order_by("created_at"),
                )
            )
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
        question = serializer.save(user=self.request.user)
        payload_hash = hashlib.sha256(
            f"{question.id}:{question.question_text}".encode()
        ).hexdigest()
        job, _ = AIQuestionAnswerJob.objects.get_or_create(
            question=question,
            defaults={
                "idempotency_key": f"event-question:{question.id}",
                "request_payload_hash": payload_hash,
            },
        )

        def enqueue_ai_answer():
            try:
                from apps.interactions.tasks import generate_ai_answer_for_question

                generate_ai_answer_for_question.delay(str(question.id))
                job.broker_timestamp = timezone.now()
                job.save(update_fields=["broker_timestamp", "updated_at"])
            except Exception as exc:  # The question request must remain successful.
                logger.exception("Could not enqueue AI answer job %s", job.id)
                AIQuestionAnswerJob.objects.filter(pk=job.pk).update(
                    status=AIQuestionAnswerJob.Status.FAILED,
                    error_code="enqueue_error",
                    error_message=str(exc),
                    completed_at=timezone.now(),
                    updated_at=timezone.now(),
                )

        transaction.on_commit(enqueue_ai_answer, robust=True)


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
            .prefetch_related(
                Prefetch(
                    "replies",
                    queryset=EventQuestionReply.objects.select_related(
                        "user"
                    ).order_by("created_at"),
                )
            )
            .order_by("-is_pinned", "-asked_at", "-created_at")
        )


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsInteractionOwner]
    serializer_class = EventQuestionSerializer

    def get_serializer_class(self):
        if self.request.method == "GET":
            event = Event.objects.filter(
                questions__id=self.kwargs["pk"]
            ).prefetch_related("organizers").first()
            if event and is_event_organizer(self.request.user, event):
                return OrganizerEventQuestionSerializer
        return EventQuestionSerializer

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
        return (
            EventQuestion.objects.select_related(
                "event", "user", "answered_by", "ai_answer_job"
            )
            .prefetch_related(
                Prefetch(
                    "replies",
                    queryset=EventQuestionReply.objects.select_related(
                        "user"
                    ).order_by("created_at"),
                )
            )
        )


class QuestionReplyListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EventQuestionReplySerializer

    def get_question(self):
        return get_object_or_404(
            EventQuestion.objects.select_related("event").prefetch_related(
                "event__organizers"
            ),
            id=self.kwargs["question_id"],
        )

    def get_queryset(self):  # type: ignore[override]
        question = self.get_question()
        if (
            question.moderation_status != EventQuestion.ModerationStatus.VISIBLE
            and not is_event_organizer(self.request.user, question.event)
        ):
            raise PermissionDenied("You do not have access to this question.")
        return (
            EventQuestionReply.objects.filter(question=question)
            .select_related("user")
            .order_by("created_at")
        )

    @swagger_auto_schema(
        operation_summary="List Question Replies",
        operation_description="Xem các reply trong một câu hỏi.",
        responses={200: EventQuestionReplySerializer(many=True), **INTERACTION_ERROR_RESPONSES},
        tags=["Questions"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Question Reply",
        operation_description="User hoặc organizer trả lời nối tiếp trong câu hỏi.",
        request_body=EventQuestionReplySerializer,
        responses={201: EventQuestionReplySerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Questions"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["question_id"] = self.kwargs["question_id"]
        return context

    def perform_create(self, serializer):
        question = serializer.validated_data["question"]
        if (
            question.moderation_status != EventQuestion.ModerationStatus.VISIBLE
            and not is_event_organizer(self.request.user, question.event)
        ):
            raise PermissionDenied("You do not have access to this question.")
        serializer.save(
            user=self.request.user,
            is_organizer_reply=is_event_organizer(
                self.request.user, question.event
            ),
        )


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
            EventQuestion.objects.select_related("event", "user", "answered_by")
            .prefetch_related(
                Prefetch(
                    "replies",
                    queryset=EventQuestionReply.objects.select_related(
                        "user"
                    ).order_by("created_at"),
                )
            ),
            id=question_id,
        )
        assert_event_organizer(request, question.event)
        serializer = QuestionAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question.answer_text = serializer.validated_data["answer_text"]
        question.answered_by = request.user
        question.answered_at = timezone.now()
        question.save(
            update_fields=["answer_text", "answered_by", "answered_at", "updated_at"]
        )
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


class EventAIAssistantView(APIView):
    """Read or toggle the AI assistant for an event."""

    permission_classes = [IsAuthenticated]

    def get_event(self, request, event_id):
        event = get_object_or_404(
            Event.objects.prefetch_related("organizers"),
            id=event_id,
        )
        assert_event_organizer(request, event)
        return event

    @swagger_auto_schema(
        operation_summary="Get Event AI Assistant",
        operation_description="Organizer xem trạng thái bật/tắt trợ lý AI.",
        responses={200: EventAIAssistantToggleSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["AI Assistant"],
    )
    def get(self, request, event_id):
        event = self.get_event(request, event_id)
        is_enabled = EventAIQASetting.objects.filter(
            event=event,
            is_enabled=True,
        ).exists()
        return Response(
            EventAIAssistantToggleSerializer(
                {"event_id": event.id, "is_enabled": is_enabled}
            ).data,
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary="Toggle Event AI Assistant",
        operation_description="Organizer bật hoặc tắt trợ lý AI cho sự kiện.",
        request_body=EventAIAssistantToggleSerializer,
        responses={200: EventAIAssistantToggleSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["AI Assistant"],
    )
    def patch(self, request, event_id):
        event = self.get_event(request, event_id)
        serializer = EventAIAssistantToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        setting, _ = EventAIQASetting.all_objects.update_or_create(
            event=event,
            defaults={
                "is_enabled": serializer.validated_data["is_enabled"],
                "deleted_at": None,
            },
        )
        return Response(
            EventAIAssistantToggleSerializer(
                {"event_id": event.id, "is_enabled": setting.is_enabled}
            ).data,
            status=status.HTTP_200_OK,
        )
