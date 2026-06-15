"""One-off script: rename SLA terminology to Deadline across the codebase."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REPLACEMENTS = [
    ('SLAConfigurationForm', 'DeadlineConfigurationForm'),
    ('SLAConfiguration', 'DeadlineConfiguration'),
    ('SLARecord', 'DeadlineRecord'),
    ('SLAStatus', 'DeadlineStatus'),
    ('default_sla_days', 'allowed_days'),
    ('sla_warning_hours', 'deadline_warning_hours'),
    ('sla_breached', 'deadline_missed'),
    ('sla_start', 'deadline_start'),
    ('sla_due', 'deadline_due'),
    ('sla_status', 'deadline_status'),
    ('sla_record', 'deadline_record'),
    ('_sla_compliance_data', '_deadline_compliance_data'),
    ('sla_compliance', 'deadline_compliance'),
    ('check_sla_statuses', 'check_deadline_statuses'),
    ('process_sla_escalations', 'process_deadline_escalations'),
    ('update_sla_status', 'update_deadline_status'),
    ('_start_sla', '_start_deadline'),
    ('sla_penalty', 'deadline_penalty'),
    ('sla_data', 'deadline_data'),
    ('sla_pct', 'deadline_pct'),
    ('sla_config', 'deadline_config'),
    ('sla_form', 'deadline_form'),
    ('SLA_BADGE', 'DEADLINE_BADGE'),
    ('sla_badge', 'deadline_badge'),
    ("'update_sla'", "'update_deadline'"),
    ('SLA Configuration', 'Deadline Configuration'),
    ('SLA configuration', 'Deadline configuration'),
    ('SLA Settings', 'Deadline Settings'),
    ('SLA Compliance', 'Deadline Compliance'),
    ('SLA Overview', 'Deadline Overview'),
    ('SLA Tracker', 'Deadline Timer'),
    ('SLA Days', 'Allowed Days'),
    ('SLA Status', 'Deadline Status'),
    ('SLA:', 'Deadline:'),
    ('SLA rules', 'deadline rules'),
    ('breached SLA deadline', 'missed deadline'),
    ('SLA Escalation', 'Deadline Escalation'),
    ('breached SLA', 'missed deadline'),
    ('SLA Compliance %', 'Deadline Compliance %'),
    ('Breached SLA', 'Missed Deadlines'),
    ('check-sla-statuses', 'check-deadline-statuses'),
    ('process-sla-escalations', 'process-deadline-escalations'),
    ('NotificationType.SLA', 'NotificationType.DEADLINE'),
    ('for name, prefix, sla_days in', 'for name, prefix, allowed_days in'),
    ('sla_days,', 'allowed_days,'),
    ('sla_days =', 'allowed_days ='),
    ("tab == 'sla'", "tab == 'deadline'"),
    ("?tab=sla", "?tab=deadline"),
    ("'sla', 'Deadline Configuration'", "'deadline', 'Deadline Configuration'"),
    ("'sla', 'SLA", "'deadline', 'Deadline"),
    ('get_sla_status_display', 'get_deadline_status_display'),
    ('stats.sla_breached', 'stats.deadline_missed'),
    ("sla_status='red'", "deadline_status='red'"),
    ("sla_status='green'", "deadline_status='green'"),
    ("sla_status='yellow'", "deadline_status='yellow'"),
    ("exclude(sla_due__isnull=True)", "exclude(deadline_due__isnull=True)"),
    ("design.sla_status", "design.deadline_status"),
    ("d.sla_status", "d.deadline_status"),
    ("d.sla_due", "d.deadline_due"),
    ('SLA tracking', 'Deadline tracking'),
    ('SLA status', 'Deadline status'),
]

EXTENSIONS = {'.py', '.html', '.js', '.md'}
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'staticfiles', 'migrations', 'scripts'}
SKIP_MD = {
    'Genesis_Design_Cursor_Prompt.md',
    'Genesis_Design_UI_Plan.md',
    'Genesis_Permission_System.md',
}


def should_process(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.suffix not in EXTENSIONS:
        return False
    if path.suffix == '.md' and path.name in SKIP_MD:
        return False
    return True


def main():
    for path in ROOT.rglob('*'):
        if not path.is_file() or not should_process(path):
            continue
        text = path.read_text(encoding='utf-8')
        original = text
        for old, new in REPLACEMENTS:
            text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding='utf-8')
            print(f'updated {path.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
