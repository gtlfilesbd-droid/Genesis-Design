from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import UserRole


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.is_superuser or request.user.role == UserRole.ADMIN:
                return view_func(request, *args, **kwargs)
            if request.user.role not in roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect(request.user.get_dashboard_url_name())
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
