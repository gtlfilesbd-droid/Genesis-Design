from django.urls import path

from . import manual_views

app_name = 'manual'

urlpatterns = [
    path('', manual_views.user_manual, name='index'),
    path('<path:path>', manual_views.user_manual, name='file'),
]
