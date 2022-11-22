from django.urls import path, include
from plpPool import views

app_name = 'plpPool'

urlpatterns = [
    path('', views.todas_questoes, name="pagina_inicial"),
    path('questao/<int:pk>/', views.questao, name="questao_detail"),
    path('questao/remover/<int:pk>/', views.remover_questao_monitor, name="questao_remove"),
    path('questao/editar/<int:pk>/', views.editar_questao_monitor, name="questao_edit"),
    path('monitor', views.MonitorView.as_view(), name="monitor_questoes"),
    path('feedback', views.feedback, name="feedback"),
    
    path('teste', views.teste, name="teste"),
]
