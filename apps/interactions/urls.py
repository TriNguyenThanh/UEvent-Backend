from django.urls import path

from apps.interactions.views import (
    FeedbackDetailView,
    FeedbackListCreateView,
    QuestionDetailView,
    QuestionListCreateView,
)


urlpatterns = [
    path("feedbacks/", FeedbackListCreateView.as_view(), name="feedback-list-create"),
    path("feedbacks/<uuid:pk>/", FeedbackDetailView.as_view(), name="feedback-detail"),
    path("questions/", QuestionListCreateView.as_view(), name="question-list-create"),
    path("questions/<uuid:pk>/", QuestionDetailView.as_view(), name="question-detail"),
]
