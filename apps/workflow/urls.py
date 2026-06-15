from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'workflow'

urlpatterns = [
    path('', views.kanban_board, name='board'),
    path('kanban/', RedirectView.as_view(pattern_name='workflow:board', permanent=True)),
    path('design/<int:pk>/<str:action>/', views.workflow_action, name='action'),
    path('design/<int:pk>/assign/', views.assign_designer_view, name='assign'),
]
