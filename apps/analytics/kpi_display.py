from apps.accounts.models import UserRole

INVERTED_RATE_KEYS = frozenset({'late_rate', 'correction_rate', 'overdue_percentage'})

TONE_COLORS = {
    'good': {'text': '#3B6D11', 'fill': '#639922'},
    'medium': {'text': '#854F0B', 'fill': '#EF9F27'},
    'bad': {'text': '#791F1F', 'fill': '#E24B4A'},
    'neutral': {'text': '#0F172A', 'fill': '#378ADD'},
}

ICON_MAP = {
    'assigned': {'icon': 'ti-clipboard-list', 'bg': '#EFF6FF', 'fg': '#1D4ED8'},
    'completed': {'icon': 'ti-check', 'bg': '#F0FDF4', 'fg': '#16A34A'},
    'corrections': {'icon': 'ti-rotate', 'bg': '#FFFFFF', 'fg': '#DC2626'},
    'total': {'icon': 'ti-folder', 'bg': '#EFF6FF', 'fg': '#1D4ED8'},
    'approved': {'icon': 'ti-check', 'bg': '#F0FDF4', 'fg': '#16A34A'},
    'pending': {'icon': 'ti-clock', 'bg': '#FFFBEB', 'fg': '#D97706'},
    'verified': {'icon': 'ti-shield-check', 'bg': '#EFF6FF', 'fg': '#1D4ED8'},
    'reviewed': {'icon': 'ti-list-check', 'bg': '#EFF6FF', 'fg': '#1D4ED8'},
    'managed': {'icon': 'ti-layers-linked', 'bg': '#EFF6FF', 'fg': '#1D4ED8'},
}

STAT_KEY_TO_ICON = {
    'total_assigned': 'assigned',
    'total_completed': 'completed',
    'total_corrections': 'corrections',
    'total_managed': 'managed',
    'total_requests': 'total',
    'completed_requests': 'completed',
    'pending_requests': 'pending',
    'total_verified': 'verified',
    'total_reviewed': 'reviewed',
    'approved': 'approved',
}

RING_CIRCUMFERENCE = 251.3


def _rate_tone(value, inverted=False):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 'medium'
    if inverted:
        if numeric <= 20:
            return 'good'
        if numeric <= 50:
            return 'medium'
        return 'bad'
    if numeric >= 80:
        return 'good'
    if numeric >= 50:
        return 'medium'
    return 'bad'


def _build_rate_card(label, value, inverted=False, unit='%', fill_percent=None, neutral=False):
    if neutral:
        tone = 'neutral'
    else:
        tone = _rate_tone(value, inverted=inverted)
    colors = TONE_COLORS[tone]
    return {
        'label': label,
        'value': value,
        'unit': unit,
        'value_color': colors['text'],
        'fill_color': colors['fill'],
        'fill_percent': fill_percent if fill_percent is not None else min(float(value), 100),
    }


def _build_stat_card(key, label, value, is_danger=False):
    icon_key = STAT_KEY_TO_ICON.get(key, 'total')
    icon_info = ICON_MAP.get(icon_key, {'icon': 'ti-chart-bar', 'bg': '#F1F5F9', 'fg': '#475569'})
    return {
        'label': label,
        'value': value,
        'icon': icon_info['icon'],
        'icon_bg': icon_info['bg'],
        'icon_fg': icon_info['fg'],
        'is_danger': is_danger,
    }


def _build_headline(label, value, context_text, inverted=False):
    tone = _rate_tone(value, inverted=inverted)
    colors = TONE_COLORS[tone]
    numeric = float(value)
    ring_offset = round(RING_CIRCUMFERENCE - (RING_CIRCUMFERENCE * numeric / 100), 1)
    return {
        'label': label,
        'value': value,
        'value_color': colors['text'],
        'ring_color': colors['fill'],
        'ring_offset': ring_offset,
        'ring_circumference': RING_CIRCUMFERENCE,
        'context_text': context_text,
    }


def _headline_context(role, kpis):
    if role == UserRole.DESIGNER:
        completed = kpis.get('total_completed', 0)
        assigned = kpis.get('total_assigned', 0)
        return (
            f'{completed} of {assigned} assigned designs completed and accepted this period'
        )
    if role == UserRole.HEAD_OF_DESIGN:
        approved = kpis.get('approved', 0)
        managed = kpis.get('total_managed', 0)
        return f'{approved} of {managed} designs approved across the team'
    if role == UserRole.VERIFICATION_TEAM:
        approved = kpis.get('approved', 0)
        total = kpis.get('total_verified', 0)
        return f'{approved} of {total} verified designs passed review'
    if role == UserRole.COMPLIANCE_TEAM:
        approved = kpis.get('approved', 0)
        total = kpis.get('total_reviewed', 0)
        return f'{approved} of {total} reviewed designs approved for compliance'
    if role == UserRole.DESIGN_REQUESTER:
        completed = kpis.get('completed_requests', 0)
        total = kpis.get('total_requests', 0)
        return f'{completed} of {total} submitted requests completed this period'
    return ''


def _layout_stat_card(key, label, icon, icon_bg='bg-blue-50', icon_color='text-blue-600', danger=False):
    return {
        'type': 'stat',
        'key': key,
        'label': label,
        'icon': icon,
        'icon_bg': icon_bg,
        'icon_color': icon_color,
        'danger': danger,
    }


def _layout_rate_card(key, label, danger=False):
    return {
        'type': 'rate',
        'key': key,
        'label': label,
        'danger': danger,
    }


ROLE_KPI_LAYOUT = {
    UserRole.DESIGNER: {
        'headline_key': 'completion_rate',
        'headline_label': 'Completion rate',
        'sections': [
            {
                'title': 'Volume',
                'cards': [
                    _layout_stat_card('total_assigned', 'Assigned', 'clipboard-list'),
                    _layout_stat_card(
                        'total_completed', 'Completed', 'check-circle',
                        icon_bg='bg-green-50', icon_color='text-green-600',
                    ),
                    _layout_stat_card(
                        'total_corrections', 'Corrections', 'rotate-ccw',
                        icon_bg='bg-orange-50', icon_color='text-orange-600',
                    ),
                ],
            },
            {
                'title': 'Performance and quality',
                'cards': [
                    _layout_rate_card('on_time_rate', 'On-time rate'),
                    _layout_rate_card('late_rate', 'Late rate', danger=True),
                    _layout_rate_card('first_time_approval_rate', 'First-time approval'),
                    _layout_rate_card('avg_completion_days', 'Avg. completion time'),
                ],
            },
        ],
    },
    UserRole.HEAD_OF_DESIGN: {
        'headline_key': 'overdue_percentage',
        'headline_label': 'Overdue rate',
        'sections': [
            {
                'title': 'Volume',
                'cards': [
                    _layout_stat_card('total_managed', 'Total managed', 'layers'),
                    _layout_stat_card(
                        'approved', 'Approved', 'check-circle',
                        icon_bg='bg-green-50', icon_color='text-green-600',
                    ),
                ],
            },
            {
                'title': 'Team health',
                'cards': [
                    _layout_rate_card('correction_rate', 'Correction rate'),
                    _layout_rate_card('overdue_percentage', 'Overdue rate', danger=True),
                ],
            },
        ],
    },
    UserRole.VERIFICATION_TEAM: {
        'headline_key': 'accuracy_rate',
        'headline_label': 'Accuracy rate',
        'sections': [
            {
                'title': 'Volume',
                'cards': [
                    _layout_stat_card('total_verified', 'Total verified', 'shield'),
                    _layout_stat_card(
                        'approved', 'Approved', 'check-circle',
                        icon_bg='bg-green-50', icon_color='text-green-600',
                    ),
                ],
            },
            {
                'title': 'Performance and quality',
                'cards': [
                    _layout_rate_card('accuracy_rate', 'Accuracy rate'),
                    _layout_rate_card('correction_rate', 'Correction rate', danger=True),
                ],
            },
        ],
    },
    UserRole.COMPLIANCE_TEAM: {
        'headline_key': 'accuracy_rate',
        'headline_label': 'Accuracy rate',
        'sections': [
            {
                'title': 'Volume',
                'cards': [
                    _layout_stat_card('total_reviewed', 'Total reviewed', 'scale'),
                    _layout_stat_card(
                        'approved', 'Approved', 'check-circle',
                        icon_bg='bg-green-50', icon_color='text-green-600',
                    ),
                ],
            },
            {
                'title': 'Performance and quality',
                'cards': [
                    _layout_rate_card('accuracy_rate', 'Accuracy rate'),
                    _layout_rate_card('correction_rate', 'Correction rate', danger=True),
                ],
            },
        ],
    },
    UserRole.DESIGN_REQUESTER: {
        'headline_key': 'completion_rate',
        'headline_label': 'Completion rate',
        'sections': [
            {
                'title': 'Volume',
                'cards': [
                    _layout_stat_card('total_requests', 'Total requests', 'file-plus'),
                    _layout_stat_card(
                        'completed_requests', 'Completed', 'check-circle',
                        icon_bg='bg-green-50', icon_color='text-green-600',
                    ),
                    _layout_stat_card(
                        'pending_requests', 'Pending', 'clock',
                        icon_bg='bg-amber-50', icon_color='text-amber-600',
                    ),
                ],
            },
            {
                'title': 'Performance and quality',
                'cards': [
                    _layout_rate_card('completion_rate', 'Completion rate'),
                ],
            },
        ],
    },
}


def build_kpi_page_context(role, kpis):
    if not kpis:
        return {
            'has_kpis': False,
            'headline': None,
            'sections': [],
        }

    layout = ROLE_KPI_LAYOUT.get(role)
    if not layout:
        return {
            'has_kpis': False,
            'headline': None,
            'sections': [],
        }

    headline = None
    headline_key = layout.get('headline_key')
    if headline_key and headline_key in kpis:
        headline = _build_headline(
            label=layout.get('headline_label', headline_key.replace('_', ' ').title()),
            value=kpis[headline_key],
            context_text=_headline_context(role, kpis),
            inverted=headline_key in INVERTED_RATE_KEYS,
        )

    sections = []
    for section_def in layout['sections']:
        cards = []
        section_type = None
        for card_def in section_def['cards']:
            key = card_def['key']
            if key not in kpis:
                continue
            value = kpis[key]
            if card_def['type'] == 'stat':
                section_type = 'volume'
                is_danger = key == 'total_corrections' and float(value) > 0
                cards.append(_build_stat_card(key, card_def['label'], value, is_danger=is_danger))
            else:
                section_type = 'rate'
                if key == 'avg_completion_days':
                    if value is None or not value:
                        continue
                    cards.append(_build_rate_card(
                        card_def['label'],
                        value,
                        unit='d',
                        fill_percent=min(float(value) * 10, 100),
                        neutral=True,
                    ))
                else:
                    inverted = key in INVERTED_RATE_KEYS
                    cards.append(_build_rate_card(card_def['label'], value, inverted=inverted))
        if cards:
            sections.append({
                'label': section_def['title'],
                'type': section_type or 'volume',
                'cards': cards,
            })

    return {
        'has_kpis': bool(sections),
        'headline': headline,
        'sections': sections,
    }
