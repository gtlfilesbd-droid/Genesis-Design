from functools import wraps

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from apps.projects.models import Project

from .services import PermissionService


def require_global_permission(permission_code):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not PermissionService.has_global_permission(request.user, permission_code):
                messages.error(request, "You don't have permission to access this page.")
                return redirect('accounts:dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_project_permission(permission_code, project_kwarg='pk'):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            project_pk = kwargs.get(project_kwarg)
            project = get_object_or_404(Project, pk=project_pk)
            if not PermissionService.has_project_permission(request.user, project, permission_code):
                messages.error(request, "You don't have permission for this project.")
                return redirect('projects:list')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
