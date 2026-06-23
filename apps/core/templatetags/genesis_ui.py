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

DEADLINE_BADGE = {
    'green': ('On Track', 'bg-green-100 text-green-700'),
    'yellow': ('Deadline Warning', 'bg-amber-100 text-amber-700'),
    'red': ('Deadline Missed', 'bg-red-100 text-red-700'),
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
def deadline_badge(status):
    label, css = DEADLINE_BADGE.get(status, ('Unknown', 'bg-slate-100 text-slate-600'))
    return {'label': label, 'css': css}


@register.filter
def proper_title(value):
    """Title-case labels; keep short leading tokens like RSC uppercase."""
    if not value:
        return ''
    words = str(value).split()
    result = []
    for i, word in enumerate(words):
        clean = ''.join(c for c in word if c.isalnum())
        if not clean:
            result.append(word)
            continue
        if len(clean) <= 4 and clean.isalpha() and (clean.upper() == clean or i == 0):
            result.append(clean.upper())
        else:
            result.append(word.capitalize())
    return ' '.join(result)


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
def datetime_with_hint(value):
    """Full date+time with optional relative hint."""
    if not value:
        return '—'
    absolute = timezone.localtime(value).strftime('%d %b %Y, %I:%M %p')
    hint = timesince_short(value)
    if hint == 'just now':
        return absolute
    return f'{absolute} · {hint}'


ACTIVITY_DOT_COLORS = {
    'submit_request': '#2E75B6',
    'design_requested': '#2E75B6',
    'submit_work': '#2E75B6',
    'resubmit': '#2E75B6',
    'assign': '#2E75B6',
    'send_to_verification': '#2E75B6',
    'send_to_compliance': '#2E75B6',
    'accept_assignment': '#2E75B6',
    'acknowledge': '#64748B',
    'accept_verification': '#64748B',
    'accept_compliance': '#64748B',
    'start_review': '#64748B',
    'request_correction': '#D97706',
    'verification_correction': '#D97706',
    'compliance_correction': '#D97706',
    'forward_to_designer': '#D97706',
    'cancel': '#D97706',
    'cancelled': '#D97706',
    'accept_design': '#16A34A',
    'verify_approved': '#16A34A',
    'compliance_approved': '#16A34A',
    'complete': '#1A3C6E',
    'hod_fast_complete': '#1A3C6E',
}


@register.filter
def activity_title(action):
    from apps.core.activity_messages import activity_title as _activity_title
    return _activity_title(action)


@register.filter
def activity_dot_color(action):
    return ACTIVITY_DOT_COLORS.get(action, '#2E75B6')


@register.filter
def activity_dot_size(action):
    if action in ('complete', 'hod_fast_complete'):
        return '14px'
    return '10px'


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
