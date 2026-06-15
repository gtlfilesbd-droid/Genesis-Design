from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_index, name='index'),
    path('export/csv/<str:report_type>/', views.export_csv, name='export_csv'),
    path('export/excel/<str:report_type>/', views.export_excel, name='export_excel'),
    path('export/pdf/<str:report_type>/', views.export_pdf, name='export_pdf'),
]
