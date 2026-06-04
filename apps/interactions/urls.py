from django.urls import path

from apps.interactions.views import (
    EventFeedbackListCreateView,
    EventFeedbackSummaryView,
    EventPublicQuestionListView,
    EventQuestionListCreateView,
    FeedbackDetailView,
    QuestionAnswerView,
    QuestionDetailView,
    QuestionHideView,
    QuestionPinView,
    QuestionReplyListCreateView,
)


urlpatterns = [
    path("feedbacks/<uuid:pk>/", FeedbackDetailView.as_view(), name="feedback-detail"),
    path("questions/<uuid:pk>/", QuestionDetailView.as_view(), name="question-detail"),
    path("events/<uuid:event_id>/feedbacks/", EventFeedbackListCreateView.as_view(), name="event-feedback-list-create"),
    path("events/<uuid:event_id>/feedbacks/summary/", EventFeedbackSummaryView.as_view(), name="event-feedback-summary"),
    path("events/<uuid:event_id>/questions/", EventQuestionListCreateView.as_view(), name="event-question-list-create"),
    path("events/<uuid:event_id>/questions/public/", EventPublicQuestionListView.as_view(), name="event-question-public-list"),
    path("questions/<uuid:question_id>/answer/", QuestionAnswerView.as_view(), name="question-answer"),
    path("questions/<uuid:question_id>/replies/", QuestionReplyListCreateView.as_view(), name="question-reply-list-create"),
    path("questions/<uuid:question_id>/pin/", QuestionPinView.as_view(), name="question-pin"),
    path("questions/<uuid:question_id>/hide/", QuestionHideView.as_view(), name="question-hide"),
]
