from django.urls import path

from . import views

app_name = "code_compiler"

urlpatterns = [
    path('api/run/manual/<int:question_id>/', views.submit_manual_run_view, name='submit_manual_run'),
    path('api/run/validation/<int:question_id>/', views.submit_validation_view, name='submit_validation'),
    path('api/status/<uuid:activity_id>/', views.check_activity_status_view, name='check_activity_status'),
]
