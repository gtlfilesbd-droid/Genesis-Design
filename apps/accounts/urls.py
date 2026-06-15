from django.urls import path

from . import views
from . import user_views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.GenesisLoginView.as_view(), name='login'),
    path('logout/', views.GenesisLogoutView.as_view(), name='logout'),
    path('password-reset/', views.GenesisPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.GenesisPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('', views.dashboard_redirect, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/requester/', views.requester_dashboard, name='requester_dashboard'),
    path('dashboard/hod/', views.hod_dashboard, name='hod_dashboard'),
    path('dashboard/designer/', views.designer_dashboard, name='designer_dashboard'),
    path('dashboard/verification/', views.verification_dashboard, name='verification_dashboard'),
    path('dashboard/compliance/', views.compliance_dashboard, name='compliance_dashboard'),
    path('users/', user_views.user_list, name='user_list'),
    path('users/new/', user_views.user_create, name='user_create'),
    path('users/<int:pk>/', user_views.user_detail, name='user_detail'),
    path('users/<int:pk>/edit/', user_views.user_edit, name='user_edit'),
    path('users/<int:pk>/disable/', user_views.user_disable, name='user_disable'),
]
