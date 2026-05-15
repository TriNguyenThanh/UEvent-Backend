from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.interactions.models import EventFeedback, EventQuestion
from apps.interactions.permissions import IsInteractionOwner
from apps.interactions.serializers import EventFeedbackSerializer, EventQuestionSerializer
from common.serializers import ApiErrorResponseSerializer


INTERACTION_ERROR_RESPONSES = {
    400: ApiErrorResponseSerializer(),
    401: ApiErrorResponseSerializer(),
    403: ApiErrorResponseSerializer(),
    404: ApiErrorResponseSerializer(),
}


class FeedbackListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EventFeedbackSerializer

    @swagger_auto_schema(
        operation_summary="List Feedbacks",
        operation_description="Lấy danh sách feedback. Có thể lọc theo event_id và mine.",
        manual_parameters=[
            openapi.Parameter("event_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("mine", openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, required=False),
        ],
        responses={200: EventFeedbackSerializer(many=True), **INTERACTION_ERROR_RESPONSES},
        tags=["Interactions"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Feedback",
        operation_description="Gửi feedback cho một sự kiện (yêu cầu đăng nhập).",
        request_body=EventFeedbackSerializer,
        responses={201: EventFeedbackSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Interactions"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):  # type: ignore[override]
        queryset = (
            EventFeedback.objects.select_related("event", "user")
            .order_by("-created_at")
        )
        event_id = self.request.query_params.get("event_id")
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        mine = self.request.query_params.get("mine")
        if mine and mine.lower() in {"1", "true", "yes"}:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FeedbackDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsInteractionOwner]
    serializer_class = EventFeedbackSerializer

    @swagger_auto_schema(
        operation_summary="Get Feedback Detail",
        operation_description="Lấy chi tiết feedback theo id.",
        responses={200: EventFeedbackSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Interactions"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Feedback",
        operation_description="Cập nhật feedback (chỉ owner).",
        request_body=EventFeedbackSerializer,
        responses={200: EventFeedbackSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Interactions"],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Replace Feedback",
        operation_description="Cập nhật toàn bộ feedback (PUT, chỉ owner).",
        request_body=EventFeedbackSerializer,
        responses={200: EventFeedbackSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Interactions"],
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete Feedback",
        operation_description="Xóa feedback (chỉ owner).",
        responses={204: openapi.Response(description="Xóa feedback thành công."), **INTERACTION_ERROR_RESPONSES},
        tags=["Interactions"],
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):  # type: ignore[override]
        return EventFeedback.objects.select_related("event", "user")


class QuestionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EventQuestionSerializer

    @swagger_auto_schema(
        operation_summary="List Questions",
        operation_description="Lấy danh sách câu hỏi. Có thể lọc theo event_id, mine và moderation_status.",
        manual_parameters=[
            openapi.Parameter("event_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("mine", openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter("moderation_status", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: EventQuestionSerializer(many=True), **INTERACTION_ERROR_RESPONSES},
        tags=["Interactions"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Question",
        operation_description="Gửi câu hỏi cho sự kiện (yêu cầu đăng nhập).",
        request_body=EventQuestionSerializer,
        responses={201: EventQuestionSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Interactions"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):  # type: ignore[override]
        queryset = (
            EventQuestion.objects.select_related("event", "user", "answered_by")
            .order_by("-asked_at", "-created_at")
        )
        event_id = self.request.query_params.get("event_id")
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        mine = self.request.query_params.get("mine")
        if mine and mine.lower() in {"1", "true", "yes"}:
            queryset = queryset.filter(user=self.request.user)
        moderation_status = self.request.query_params.get("moderation_status")
        if moderation_status:
            queryset = queryset.filter(moderation_status=moderation_status)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsInteractionOwner]
    serializer_class = EventQuestionSerializer

    @swagger_auto_schema(
        operation_summary="Get Question Detail",
        operation_description="Lấy chi tiết câu hỏi theo id.",
        responses={200: EventQuestionSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Interactions"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Question",
        operation_description="Cập nhật câu hỏi (chỉ owner).",
        request_body=EventQuestionSerializer,
        responses={200: EventQuestionSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Interactions"],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Replace Question",
        operation_description="Cập nhật toàn bộ câu hỏi (PUT, chỉ owner).",
        request_body=EventQuestionSerializer,
        responses={200: EventQuestionSerializer(), **INTERACTION_ERROR_RESPONSES},
        tags=["Interactions"],
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete Question",
        operation_description="Xóa câu hỏi (chỉ owner).",
        responses={204: openapi.Response(description="Xóa câu hỏi thành công."), **INTERACTION_ERROR_RESPONSES},
        tags=["Interactions"],
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):  # type: ignore[override]
        return EventQuestion.objects.select_related("event", "user", "answered_by")
