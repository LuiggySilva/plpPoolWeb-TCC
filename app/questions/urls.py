from django.urls import path

from .views import (
    QuestionListView,
    QuestionDetailView,
    AssistentStudentQuestionListView,
    # QuestionCreateView,
    # QuestionUpdateView,
    # QuestionDeleteView,
)

app_name = "questions"

urlpatterns = [
    path("", QuestionListView.as_view(), name="list"),
    path("<int:pk>-<slug:slug>/", QuestionDetailView.as_view(), name="detail"),
    path("assistent-student/", AssistentStudentQuestionListView.as_view(), name="assistentstudent_list"),
]   