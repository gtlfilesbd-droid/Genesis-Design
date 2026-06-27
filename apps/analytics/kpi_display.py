from apps.accounts.models import UserRole

INVERTED_RATE_KEYS = frozenset({'late_rate', 'correction_rate', 'overdue_percentage'})


def _rate_tone(key, value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 'amber'
    if key in INVERTED_RATE_KEYS:
        if numeric >= 30:
            return 'red'
        if numeric >= 10:
            return 'amber'
        return 'green'
    if numeric >= 80:
        return 'green'
    if numeric >= 50:
        return 'amber'
    return 'red'


def _stat_card(key, label, icon, icon_bg='bg-blue-50', icon_color='text-blue-600', danger=False):
    return {
        'type': 'stat',
        'key': key,
        'label': label,
        'icon': icon,
        'icon_bg': icon_bg,
        'icon_color': icon_color,
        'danger': danger,
    }


def _rate_card(key, label, danger=False):
    return {
        'type': 'rate',
        'key': key,
        'label': label,
        'danger': danger,
    }


ROLE_KPI_LAYOUT = {
    UserRole.DESIGNER: {
        'headline_key': 'completion_rate',
        'headline_label': 'Completion Rate',
        'sections': [
            {
                'title': 'Volume',
                'cards': [
                    _stat_card('total_assigned', 'Total Assigned', 'clipboard-list'),
                    _stat_card(
                        'total_completed', 'Completed', 'check-circle',
                        icon_bg='bg-green-50', icon_color='text-green-600',
                    ),
                    _stat_card(
                        'total_corrections', 'Corrections', 'rotate-ccw',
                        icon_bg='bg-orange-50', icon_color='text-orange-600',
                    ),
                ],
            },
            {
                'title': 'Performance',
                'cards': [
                    _rate_card('on_time_rate', 'On-Time Rate'),
                    _rate_card('late_rate', 'Late Rate', danger=True),
                    _rate_card('first_time_approval_rate', 'First-Time Approval'),
                    _rate_card('completion_rate', 'Completion Rate'),
                ],
            },
        ],
    },
    UserRole.HEAD_OF_DESIGN: {
        'headline_key': 'overdue_percentage',
        'headline_label': 'Overdue Rate',
        'sections': [
            {
                'title': 'Overview',
                'cards': [
                    _stat_card('total_managed', 'Total Managed', 'layers'),
                    _stat_card(
                        'approved', 'Approved', 'check-circle',
                        icon_bg='bg-green-50', icon_color='text-green-600',
                    ),
                ],
            },
            {
                'title': 'Team Health',
                'cards': [
                    _rate_card('correction_rate', 'Correction Rate'),
                    _rate_card('overdue_percentage', 'Overdue Rate', danger=True),
                ],
            },
        ],
    },
    UserRole.VERIFICATION_TEAM: {
        'headline_key': 'accuracy_rate',
        'headline_label': 'Accuracy Rate',
        'sections': [
            {
                'title': 'Volume',
                'cards': [
                    _stat_card('total_verified', 'Total Verified', 'shield', icon_bg='bg-blue-50', icon_color='text-blue-600'),
                    _stat_card(
                        'approved', 'Approved', 'check-circle',
                        icon_bg='bg-green-50', icon_color='text-green-600',
                    ),
                ],
            },
            {
                'title': 'Quality',
                'cards': [
                    _rate_card('accuracy_rate', 'Accuracy Rate'),
                    _rate_card('correction_rate', 'Correction Rate', danger=True),
                ],
            },
        ],
    },
    UserRole.COMPLIANCE_TEAM: {
        'headline_key': 'accuracy_rate',
        'headline_label': 'Accuracy Rate',
        'sections': [
            {
                'title': 'Volume',
                'cards': [
                    _stat_card('total_reviewed', 'Total Reviewed', 'scale', icon_bg='bg-blue-50', icon_color='text-blue-600'),
                    _stat_card(
                        'approved', 'Approved', 'check-circle',
                        icon_bg='bg-green-50', icon_color='text-green-600',
                    ),
                ],
            },
            {
                'title': 'Quality',
                'cards': [
                    _rate_card('accuracy_rate', 'Accuracy Rate'),
                    _rate_card('correction_rate', 'Correction Rate', danger=True),
                ],
            },
        ],
    },
    UserRole.DESIGN_REQUESTER: {
        'headline_key': 'completion_rate',
        'headline_label': 'Completion Rate',
        'sections': [
            {
                'title': 'Requests',
                'cards': [
                    _stat_card('total_requests', 'Total Requests', 'file-plus'),
                    _stat_card(
                        'completed_requests', 'Completed', 'check-circle',
                        icon_bg='bg-green-50', icon_color='text-green-600',
                    ),
                    _stat_card(
                        'pending_requests', 'Pending', 'clock',
                        icon_bg='bg-amber-50', icon_color='text-amber-600',
                    ),
                ],
            },
            {
                'title': 'Performance',
                'cards': [
                    _rate_card('completion_rate', 'Completion Rate'),
                ],
            },
        ],
    },
}

TONE_TEXT = {
    'green': 'text-green-600',
    'amber': 'text-amber-600',
    'red': 'text-red-600',
}

TONE_PROGRESS = {
    'green': '#16A34A',
    'amber': '#D97706',
    'red': '#DC2626',
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
        value = kpis[headline_key]
        tone = _rate_tone(headline_key, value)
        headline = {
            'label': layout.get('headline_label', headline_key.replace('_', ' ').title()),
            'value': value,
            'suffix': '%',
            'tone': tone,
            'tone_class': TONE_TEXT[tone],
            'progress_color': TONE_PROGRESS[tone],
            'danger': headline_key in INVERTED_RATE_KEYS and float(value) >= 10,
        }

    sections = []
    for section_def in layout['sections']:
        cards = []
        for card_def in section_def['cards']:
            key = card_def['key']
            if key not in kpis:
                continue
            value = kpis[key]
            card = {
                'type': card_def['type'],
                'label': card_def['label'],
                'value': value,
            }
            if card_def['type'] == 'stat':
                card.update({
                    'icon': card_def['icon'],
                    'icon_bg': card_def.get('icon_bg', 'bg-blue-50'),
                    'icon_color': card_def.get('icon_color', 'text-blue-600'),
                    'danger': card_def.get('danger', False) and bool(value),
                })
            else:
                tone = _rate_tone(key, value)
                card.update({
                    'tone': tone,
                    'tone_class': TONE_TEXT[tone],
                    'progress_color': TONE_PROGRESS[tone],
                    'danger': card_def.get('danger', False) or (
                        key in INVERTED_RATE_KEYS and float(value) >= 10
                    ),
                })
            cards.append(card)
        if cards:
            sections.append({
                'title': section_def['title'],
                'cards': cards,
                'has_rates': any(c['type'] == 'rate' for c in cards),
            })

    return {
        'has_kpis': bool(sections),
        'headline': headline,
        'sections': sections,
    }
