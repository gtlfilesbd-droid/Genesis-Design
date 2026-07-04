from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.views.static import serve

from apps.accounts.models import UserRole

MANUAL_ROOT = Path(settings.BASE_DIR) / 'docs' / 'user-manual'

ROLE_MANUAL_ANCHORS = {
    UserRole.DESIGN_REQUESTER: 'requester',
    UserRole.HEAD_OF_DESIGN: 'hod',
    UserRole.DESIGNER: 'designer',
    UserRole.VERIFICATION_TEAM: 'verifier',
    UserRole.COMPLIANCE_TEAM: 'compliance',
}


def manual_anchor_for_user(user):
    if not user or not user.is_authenticated:
        return ''
    return ROLE_MANUAL_ANCHORS.get(user.role, '')


@login_required
def user_manual(request, path=''):
    """Serve the standalone visual user manual under /docs/."""
    if not MANUAL_ROOT.is_dir():
        raise Http404('User manual not found.')

    file_path = (path or 'index.html').lstrip('/')
    # Prevent path traversal outside the manual folder.
    target = (MANUAL_ROOT / file_path).resolve()
    try:
        target.relative_to(MANUAL_ROOT.resolve())
    except ValueError:
        raise Http404('User manual not found.')

    return serve(request, file_path, document_root=str(MANUAL_ROOT))
