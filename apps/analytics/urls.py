from django.urls import path

from . import views

app_name = 'analytics'

urlpatterns = [
    path('kpi/', views.kpi_dashboard, name='kpi'),
    path('search/', views.smart_search, name='search'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('workload/', views.workload_view, name='workload'),
    path('executive/', views.executive_dashboard, name='executive'),
]
