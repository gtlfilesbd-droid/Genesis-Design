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
    path('requests/<int:pk>/send-reminder/', views.api_send_reminder, name='send_reminder'),
    path('notifications/mark-read/', views.api_mark_notification_read, name='mark_notification_read'),
    path('notifications/unread-count/', views.api_notification_unread_count, name='notification_unread_count'),
    path('notifications/badge/', views.api_notification_badge, name='notification_badge'),
    path('notifications/recent/', views.api_notification_recent, name='notification_recent'),
]
