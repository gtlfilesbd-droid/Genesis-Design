from django.urls import path
from django.views.generic import RedirectView

from apps.designs import views as design_views

from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.project_list, name='list'),
    path('new/', views.project_create, name='new'),
    path('create/', RedirectView.as_view(pattern_name='projects:new', permanent=True)),
    path('<int:pk>/requests/new/', design_views.design_create, name='request_new'),
    path('<int:pk>/edit/', views.project_edit, name='edit'),
    path('<int:pk>/', views.project_detail, name='detail'),
]
