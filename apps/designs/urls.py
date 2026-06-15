from django.shortcuts import redirect
from django.urls import path

from . import views


def redirect_design_detail(request, pk):
    return redirect('requests:detail', pk=pk)


def redirect_design_create(request, project_pk):
    return redirect('projects:request_new', pk=project_pk)


app_name = 'designs'

urlpatterns = [
    path('library/', views.design_library, name='library'),
    path('<int:pk>/', redirect_design_detail),
    path('project/<int:project_pk>/create/', redirect_design_create),
]
