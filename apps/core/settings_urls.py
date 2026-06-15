from django.urls import path

from . import settings_views

app_name = 'settings'

urlpatterns = [
    path('', settings_views.settings_index, name='index'),
]
