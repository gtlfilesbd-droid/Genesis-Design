from django.urls import path

from . import views

app_name = 'my_tasks'

urlpatterns = [
    path('', views.my_tasks, name='list'),
]
