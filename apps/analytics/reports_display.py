TONE_COLORS = {
    'good': {'text': '#3B6D11', 'fill': '#639922', 'bg': '#F0FDF4'},
    'medium': {'text': '#854F0B', 'fill': '#EF9F27', 'bg': '#FFFBEB'},
    'bad': {'text': '#791F1F', 'fill': '#E24B4A', 'bg': '#FEF2F2'},
    'neutral': {'text': '#0F172A', 'fill': '#378ADD', 'bg': '#EFF6FF'},
}


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


def _capacity_status(workload):
    if workload > 5:
        return 'overloaded', 'bad'
    if workload > 2:
        return 'busy', 'medium'
    return 'available', 'good'


def build_workload_context(designers):
    designer_list = list(designers)
    workloads = [getattr(d, 'workload', 0) or 0 for d in designer_list]
    max_workload = max(workloads) if workloads else 1
    if max_workload == 0:
        max_workload = 1

    overloaded_count = sum(1 for w in workloads if w > 5)
    available_count = sum(1 for w in workloads if w <= 2)
    total_active = sum(workloads)
    suggested_id = designer_list[0].pk if designer_list else None

    summary = [
        {
            'label': 'Designers',
            'value': len(designer_list),
            'icon': 'ti-users',
            'icon_bg': '#EFF6FF',
            'icon_fg': '#1D4ED8',
        },
        {
            'label': 'Active tasks',
            'value': total_active,
            'icon': 'ti-clipboard-list',
            'icon_bg': '#EFF6FF',
            'icon_fg': '#1D4ED8',
        },
        {
            'label': 'Available',
            'value': available_count,
            'icon': 'ti-circle-check',
            'icon_bg': '#F0FDF4',
            'icon_fg': '#16A34A',
        },
        {
            'label': 'Overloaded',
            'value': overloaded_count,
            'icon': 'ti-alert-triangle',
            'icon_bg': '#FEF2F2',
            'icon_fg': '#DC2626',
        },
    ]

    rows = []
    for designer in designer_list:
        workload = getattr(designer, 'workload', 0) or 0
        overdue = getattr(designer, 'overdue', 0) or 0
        status_label, tone = _capacity_status(workload)
        colors = TONE_COLORS[tone]
        rows.append({
            'user': designer,
            'workload': workload,
            'overdue': overdue,
            'status': status_label.title(),
            'status_color': colors['text'],
            'status_bg': colors['bg'],
            'bar_percent': min(round(workload / max_workload * 100), 100),
            'bar_color': colors['fill'],
            'is_suggested': designer.pk == suggested_id,
            'is_danger': workload > 5 or overdue > 0,
        })

    return {'summary': summary, 'rows': rows}


def build_leaderboard_context(rankings, period='monthly'):
    ranking_list = list(rankings)
    scores = [r['score'] for r in ranking_list]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    top_score = scores[0] if scores else 0

    podium = []
    for idx, entry in enumerate(ranking_list[:3], start=1):
        tone = _rate_tone(entry['score'])
        colors = TONE_COLORS[tone]
        podium.append({
            'rank': idx,
            'rank_class': f'rank-{idx}',
            'user': entry['user'],
            'score': entry['score'],
            'score_color': colors['text'],
            'completion_rate': entry['kpis'].get('completion_rate', 0),
        })

    rows = []
    for idx, entry in enumerate(ranking_list, start=1):
        tone = _rate_tone(entry['score'])
        colors = TONE_COLORS[tone]
        kpis = entry['kpis']
        metrics = [
            {
                'label': 'Completion',
                'value': kpis.get('completion_rate', 0),
                'unit': '%',
                'bar_percent': min(float(kpis.get('completion_rate', 0)), 100),
                'fill_color': TONE_COLORS[_rate_tone(kpis.get('completion_rate', 0))]['fill'],
            },
            {
                'label': 'On-time',
                'value': kpis.get('on_time_rate', 0),
                'unit': '%',
                'bar_percent': min(float(kpis.get('on_time_rate', 0)), 100),
                'fill_color': TONE_COLORS[_rate_tone(kpis.get('on_time_rate', 0))]['fill'],
            },
            {
                'label': 'First-time approval',
                'value': kpis.get('first_time_approval_rate', 0),
                'unit': '%',
                'bar_percent': min(float(kpis.get('first_time_approval_rate', 0)), 100),
                'fill_color': TONE_COLORS[_rate_tone(kpis.get('first_time_approval_rate', 0))]['fill'],
            },
        ]
        corrections = kpis.get('total_corrections', 0)
        rows.append({
            'rank': idx,
            'rank_class': f'rank-{idx}' if idx <= 3 else 'rank-other',
            'user': entry['user'],
            'score': entry['score'],
            'score_color': colors['text'],
            'metrics': metrics,
            'completed': kpis.get('total_completed', 0),
            'corrections': corrections,
            'has_corrections': corrections > 0,
        })

    return {
        'period': period,
        'summary': {
            'designers_ranked': len(ranking_list),
            'avg_score': avg_score,
            'top_score': top_score,
        },
        'podium': podium,
        'rows': rows,
    }


def _health_tone(score):
    return _rate_tone(score)


def _build_risk_project_row(project, tier):
    health = getattr(project, 'display_health', getattr(project, 'health_score', 0))
    tone = _health_tone(health)
    colors = TONE_COLORS[tone]
    if tier == 'high':
        health_label = 'Critical'
        accent_color = TONE_COLORS['bad']['text']
        row_bg = TONE_COLORS['bad']['bg']
    else:
        health_label = 'At risk'
        accent_color = TONE_COLORS['medium']['text']
        row_bg = TONE_COLORS['medium']['bg']
    return {
        'project': project,
        'health': health,
        'health_label': health_label,
        'health_color': colors['text'],
        'bar_color': colors['fill'],
        'bar_percent': min(float(health), 100),
        'accent_color': accent_color,
        'row_bg': row_bg,
    }


def build_executive_context(raw):
    portfolio_health = raw.get('portfolio_health', 0)
    completion_rate = raw.get('completion_rate', 0)
    on_track_rate = raw.get('on_track_rate', 0)

    portfolio_tone = TONE_COLORS[_health_tone(portfolio_health)]
    completion_tone = TONE_COLORS[_rate_tone(completion_rate)]
    on_track_tone = TONE_COLORS[_rate_tone(on_track_rate)]
    overdue_drawings = raw.get('overdue_drawings', 0)
    at_risk_projects = raw.get('at_risk_projects', 0)

    active_projects = raw.get('active_projects', raw.get('critical_projects', []))
    high_risk_projects = sorted(
        [_build_risk_project_row(p, 'high') for p in active_projects
         if getattr(p, 'display_health', getattr(p, 'health_score', 0)) < 50],
        key=lambda row: row['health'],
    )
    moderate_risk_projects = sorted(
        [_build_risk_project_row(p, 'moderate') for p in active_projects
         if 50 <= getattr(p, 'display_health', getattr(p, 'health_score', 0)) < 70],
        key=lambda row: row['health'],
    )
    critical_projects = high_risk_projects

    risk_summary = [
        {
            'label': 'At risk',
            'value': at_risk_projects,
            'icon': 'ti-alert-triangle',
            'icon_bg': '#FEF2F2',
            'icon_fg': '#DC2626',
            'value_color': '#DC2626' if at_risk_projects else None,
        },
        {
            'label': 'On-track rate',
            'value': on_track_rate,
            'unit': '%',
            'icon': 'ti-chart-line',
            'icon_bg': on_track_tone['bg'],
            'icon_fg': on_track_tone['text'],
            'value_color': on_track_tone['text'],
        },
        {
            'label': 'Overdue drawings',
            'value': overdue_drawings,
            'icon': 'ti-clock',
            'icon_bg': '#FFFBEB',
            'icon_fg': '#D97706',
            'value_color': '#DC2626' if overdue_drawings else None,
        },
    ]

    design_team_count = raw.get('design_team_count', 0)
    verification_team_count = raw.get('verification_team_count', 0)
    compliance_team_count = raw.get('compliance_team_count', 0)
    team_chips = [
        {'icon': 'ti-users', 'label': f'{design_team_count} designers'},
        {'icon': 'ti-shield', 'label': f'{verification_team_count} verifiers'},
        {'icon': 'ti-scale', 'label': f'{compliance_team_count} compliance'},
    ]

    top_performers = []
    for entry in raw.get('top_performers', []):
        tone = _rate_tone(entry['score'])
        colors = TONE_COLORS[tone]
        top_performers.append({
            'user': entry['user'],
            'score': entry['score'],
            'score_color': colors['text'],
            'bar_percent': min(float(entry['score']), 100),
            'bar_color': colors['fill'],
        })

    bottlenecks = raw.get('bottlenecks', {})
    bottleneck_cards = [
        {
            'title': 'Slow designers',
            'icon': 'ti-user-exclamation',
            'tone': 'bad',
            'count': len(bottlenecks.get('slow_designers', [])),
            'items': [
                {
                    'label': item['user'].get_full_name(),
                    'detail': f"{item['overdue_count']} overdue",
                }
                for item in bottlenecks.get('slow_designers', [])
            ],
        },
        {
            'title': 'Slow verifiers',
            'icon': 'ti-shield-exclamation',
            'tone': 'medium',
            'count': len(bottlenecks.get('slow_verifiers', [])),
            'items': [
                {
                    'label': item['user'].get_full_name(),
                    'detail': f"{item['pending_count']} pending",
                }
                for item in bottlenecks.get('slow_verifiers', [])
            ],
        },
        {
            'title': 'Slow compliance',
            'icon': 'ti-scale',
            'tone': 'medium',
            'count': len(bottlenecks.get('slow_compliance', [])),
            'items': [
                {
                    'label': item['user'].get_full_name(),
                    'detail': f"{item['pending_count']} pending",
                }
                for item in bottlenecks.get('slow_compliance', [])
            ],
        },
        {
            'title': 'Stalled projects',
            'icon': 'ti-building-arch',
            'tone': 'bad',
            'count': len(bottlenecks.get('stalled_projects', [])),
            'items': [
                {
                    'label': item['project'].code,
                    'detail': f"Health {item['health']}",
                }
                for item in bottlenecks.get('stalled_projects', [])
            ],
        },
    ]
    for card in bottleneck_cards:
        card['tone_color'] = TONE_COLORS[card['tone']]['text']
        card['icon_bg'] = TONE_COLORS[card['tone']]['bg']

    summary = [
        {
            'label': 'Total projects',
            'value': raw.get('total_projects', 0),
            'icon': 'ti-folder',
            'icon_bg': '#EFF6FF',
            'icon_fg': '#1D4ED8',
        },
        {
            'label': 'Total drawings',
            'value': raw.get('total_drawings', 0),
            'icon': 'ti-file-text',
            'icon_bg': '#EFF6FF',
            'icon_fg': '#1D4ED8',
        },
        {
            'label': 'Pending',
            'value': raw.get('pending_drawings', 0),
            'icon': 'ti-clock',
            'icon_bg': '#FFFBEB',
            'icon_fg': '#D97706',
        },
        {
            'label': 'Overdue',
            'value': raw.get('overdue_drawings', 0),
            'icon': 'ti-alert-triangle',
            'icon_bg': '#FEF2F2',
            'icon_fg': '#DC2626',
            'is_danger': bool(raw.get('overdue_drawings', 0)),
        },
        {
            'label': 'Completion rate',
            'value': completion_rate,
            'unit': '%',
            'icon': 'ti-chart-line',
            'icon_bg': completion_tone['bg'],
            'icon_fg': completion_tone['text'],
            'value_color': completion_tone['text'],
        },
        {
            'label': 'Portfolio health',
            'value': portfolio_health,
            'unit': '%',
            'icon': 'ti-heartbeat',
            'icon_bg': portfolio_tone['bg'],
            'icon_fg': portfolio_tone['text'],
            'value_color': portfolio_tone['text'],
        },
    ]

    return {
        'summary': summary,
        'at_risk_projects': at_risk_projects,
        'on_track_rate': on_track_rate,
        'on_track_color': on_track_tone['text'],
        'design_team_count': design_team_count,
        'verification_team_count': verification_team_count,
        'risk_summary': risk_summary,
        'team_chips': team_chips,
        'high_risk_projects': high_risk_projects,
        'moderate_risk_projects': moderate_risk_projects,
        'critical_projects': critical_projects,
        'top_performers': top_performers,
        'bottleneck_cards': bottleneck_cards,
    }
