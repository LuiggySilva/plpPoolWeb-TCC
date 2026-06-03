from django.urls import path

from . import views

app_name = 'user'

urlpatterns = [
    path('', views.about, name='about'),
    path("professor-adminpage/", views.ProfessorAdminPageView.as_view(), name="professor_adminpage"),
    path("professor-adminpage/backup", views.bulk_import_questions, name='bulk_import_questions'),
    path("professor-adminpage/backup/download", views.download_backup, name='download_backup'),

    path('periods/create/', views.period_create, name='period_create'),
    path('periods/<str:period_id>/edit/', views.period_edit, name='period_edit'),
    path('periods/<str:period_id>/delete/', views.period_delete, name='period_delete'),
    path('periods/<str:period_id>/restore/', views.period_restore, name='period_restore'),
    path('periods/<str:period_id>/history/', views.period_history, name='period_history'),
    path('periods/history/deleted/', views.period_deleted_history, name='period_deleted_history'),

    path('assistentstudents/', views.monitor_list, name='assistentstudent_list'),
    path('assistentstudents/create/', views.monitor_create, name='assistentstudent_create'),
    path('assistentstudents/<int:monitor_id>/edit/', views.monitor_edit, name='assistentstudent_edit'),
    path('assistentstudents/<int:monitor_id>/delete/', views.monitor_delete, name='assistentstudent_delete'),
    path('assistentstudents/<int:monitor_id>/reset-password/', views.monitor_reset_password, name='assistentstudent_reset_password'),
    path('assistentstudents/<int:monitor_id>/restore/', views.monitor_restore, name='assistentstudent_restore'),
    path('assistentstudents/<int:monitor_id>/history/', views.monitor_history, name='assistentstudent_history'),
    path('assistentstudents/history/deleted/', views.monitor_deleted_history, name='assistentstudent_deleted_history'),

    path('professors/', views.professor_list, name='professor_list'),
    path('professors/create/', views.professor_create, name='professor_create'),
    path('professors/<int:professor_id>/edit/', views.professor_edit, name='professor_edit'),
    path('professors/<int:professor_id>/delete/', views.professor_delete, name='professor_delete'),
    path('professors/<int:professor_id>/reset-password/', views.professor_reset_password, name='professor_reset_password'),
    path('professors/<int:professor_id>/restore/', views.professor_restore, name='professor_restore'),
    path('professors/<int:professor_id>/history/', views.professor_history, name='professor_history'),
    path('professors/history/deleted/', views.professor_deleted_history, name='professor_deleted_history'),
]
