from django.urls import path

from . import views

app_name = 'requests'

urlpatterns = [
    path('', views.design_request_list, name='list'),
    path('<int:pk>/', views.design_detail, name='detail'),
]
