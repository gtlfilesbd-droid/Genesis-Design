from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),
    path('projects/', include('apps.projects.urls')),
    path('designs/', include('apps.designs.urls')),
    path('requests/', include('apps.designs.request_urls')),
    path('my-tasks/', include('apps.designs.task_urls')),
    path('workflow/', include('apps.workflow.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('reports/', include('apps.reports.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('settings/', include('apps.core.settings_urls')),
    path('api/', include('apps.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
