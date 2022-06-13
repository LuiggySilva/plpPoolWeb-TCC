from django.urls import path, include
from plpPool import views

app_name = 'plpPool'

urlpatterns = [
    path('', views.test, name="test"),
]
