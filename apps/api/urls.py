from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    path('requests/<int:pk>/acknowledge/', views.api_workflow_action, {'action': 'acknowledge'}, name='acknowledge'),
    path('requests/<int:pk>/assign/', views.api_workflow_action, {'action': 'assign'}, name='assign'),
    path('requests/<int:pk>/submit/', views.api_workflow_action, {'action': 'submit_work'}, name='submit'),
    path('requests/<int:pk>/review/', views.api_workflow_action, {'action': 'accept_design'}, name='review'),
    path('requests/<int:pk>/verify/', views.api_workflow_action, {'action': 'verify_approved'}, name='verify'),
    path('requests/<int:pk>/approve/', views.api_workflow_action, {'action': 'accept_design'}, name='approve'),
    path('requests/<int:pk>/complete/', views.api_workflow_action, {'action': 'complete'}, name='complete'),
    path('requests/<int:pk>/cancel/', views.api_workflow_action, {'action': 'cancel'}, name='cancel'),
    path('notifications/mark-read/', views.api_mark_notification_read, name='mark_notification_read'),
]
