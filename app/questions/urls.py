from django.urls import path

from . import views

app_name = "questions"

urlpatterns = [
    path("", views.QuestionListView.as_view(), name="question_list"),
    path('create/', views.question_create, name='question_create'),
    path('<int:question_id>-<slug:slug>/', views.QuestionDetailView.as_view(), name="question_detail"),
    path('<int:question_id>/edit/', views.question_edit, name='question_edit'),
    path('<int:question_id>/delete/', views.question_delete, name='question_delete'),
    path('<int:question_id>/history/', views.question_history, name='question_history'),
    path('<int:question_id>/feedback/', views.question_feedback, name='question_feedback'),

    path("assistent-student/", views.AssistentStudentQuestionListView.as_view(), name="assistentstudent_list"),

    path('tags/create/', views.tag_create, name='tag_create'),
    path('tags/<int:tag_id>/edit/', views.tag_edit, name='tag_edit'),
    path('tags/<int:tag_id>/delete/', views.tag_delete, name='tag_delete'),
    path('tags/<int:tag_id>/restore/', views.tag_restore, name='tag_restore'),
    path('tags/<int:tag_id>/history/', views.tag_history, name='tag_history'),
    path('tags/history/deleted/', views.tag_deleted_history, name='tag_deleted_history'),

]
