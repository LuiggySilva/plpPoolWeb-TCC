from django.urls import path, include
from plpPool import views

app_name = 'plpPool'

urlpatterns = [
    path('', views.todas_questoes, name="pagina_inicial"),
    path('questao/<int:pk>/', views.questao, name="questao_detail"),
    #path('monitor', views.monitor, name="monitor_questoes"),
    path('monitor', views.MonitorView.as_view(), name="monitor_questoes"),
]
