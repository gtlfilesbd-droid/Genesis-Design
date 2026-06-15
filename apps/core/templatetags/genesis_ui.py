from django import template
from django.utils import timezone

register = template.Library()

STATUS_BADGE = {
    'draft': ('Draft', 'bg-slate-100 text-slate-600'),
    'new_request': ('New Request', 'bg-blue-100 text-blue-700'),
    'acknowledged': ('Acknowledged', 'bg-sky-100 text-sky-700'),
    'assigned': ('Assigned', 'bg-indigo-100 text-indigo-700'),
    'in_progress': ('In Progress', 'bg-amber-100 text-amber-700'),
    'submitted': ('Submitted', 'bg-cyan-100 text-cyan-700'),
    'under_review': ('Under Review', 'bg-orange-100 text-orange-700'),
    'correction_required': ('Correction Required', 'bg-red-100 text-red-700'),
    'resubmitted': ('Re-Submitted', 'bg-purple-100 text-purple-700'),
    'verification_pending': ('Verification Pending', 'bg-blue-100 text-blue-700'),
    'verification_correction': ('Verification Correction', 'bg-red-100 text-red-700'),
    'final_approval_pending': ('Final Approval', 'bg-violet-100 text-violet-700'),
    'approved': ('Approved', 'bg-purple-100 text-purple-700'),
    'completed': ('Completed', 'bg-green-100 text-green-700'),
    'cancelled': ('Cancelled', 'bg-slate-100 text-slate-600'),
    'active': ('Active', 'bg-green-100 text-green-700'),
    'on_hold': ('On Hold', 'bg-amber-100 text-amber-700'),
}

PRIORITY_BADGE = {
    'critical': ('Critical', 'bg-red-100 text-red-700', 'border-l-red-500'),
    'high': ('High', 'bg-amber-100 text-amber-700', 'border-l-amber-500'),
    'medium': ('Medium', 'bg-blue-100 text-blue-700', 'border-l-blue-500'),
    'low': ('Low', 'bg-green-100 text-green-700', 'border-l-green-500'),
}

SLA_BADGE = {
    'green': ('On Track', 'bg-green-100 text-green-700'),
    'yellow': ('Warning', 'bg-amber-100 text-amber-700'),
    'red': ('Breached', 'bg-red-100 text-red-700'),
}


@register.simple_tag
def status_badge(status):
    label, css = STATUS_BADGE.get(status, (status.replace('_', ' ').title(), 'bg-slate-100 text-slate-600'))
    return {'label': label, 'css': css}


@register.simple_tag
def priority_badge(priority):
    label, css, border = PRIORITY_BADGE.get(
        priority, (priority.title(), 'bg-slate-100 text-slate-600', 'border-l-slate-400')
    )
    return {'label': label, 'css': css, 'border': border}


@register.simple_tag
def sla_badge(status):
    label, css = SLA_BADGE.get(status, ('Unknown', 'bg-slate-100 text-slate-600'))
    return {'label': label, 'css': css}


@register.filter
def initials(user):
    if not user:
        return '?'
    name = user.get_full_name() or user.username
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


@register.filter
def timesince_short(value):
    if not value:
        return '—'
    delta = timezone.now() - value
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return 'just now'
    if seconds < 3600:
        return f'{seconds // 60} min ago'
    if seconds < 86400:
        return f'{seconds // 3600} hr ago'
    return f'{seconds // 86400} days ago'


@register.filter
def progress_pct(completed, total):
    if not total:
        return 0
    return min(100, round((completed / total) * 100))


@register.inclusion_tag('components/status_badge.html')
def render_status_badge(status):
    label, css = STATUS_BADGE.get(status, (status.replace('_', ' ').title(), 'bg-slate-100 text-slate-600'))
    return {'label': label, 'css': css}


@register.filter
def highlight_mentions(text):
    from apps.designs.utils import highlight_mentions as _highlight
    from django.utils.safestring import mark_safe
    return mark_safe(_highlight(text))


@register.inclusion_tag('components/user_avatar.html')
def render_user_avatar(user, size_class='w-9 h-9', extra_class='', fallback_class=''):
    return {
        'user': user,
        'size_class': size_class,
        'extra_class': extra_class,
        'fallback_class': fallback_class,
    }


@register.inclusion_tag('components/priority_badge.html')
def render_priority_badge(priority):
    label, css, _ = PRIORITY_BADGE.get(
        priority, (priority.title(), 'bg-slate-100 text-slate-600', 'border-l-slate-400')
    )
    return {'label': label, 'css': css}
