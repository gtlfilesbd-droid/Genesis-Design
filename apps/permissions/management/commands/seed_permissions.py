from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User, UserRole
from apps.permissions.models import Permission, RoleTemplate
from apps.permissions.services import PermissionService
from apps.projects.models import Project

ALL_PERMISSIONS = [
    ('PERM_ADMIN_PANEL', 'Admin Panel Access', 'system', 'Access settings and configuration'),
    ('PERM_VIEW_ALL_PROJECTS', 'View All Projects', 'system', 'See all projects regardless of membership'),
    ('PERM_VIEW_REPORTS', 'View Reports', 'system', 'Access the reports section'),
    ('PERM_MANAGE_USERS', 'Manage Users', 'system', 'Create/edit/disable users'),
    ('PERM_MANAGE_PERMISSIONS', 'Manage Permissions', 'system', 'Assign permissions to users'),
    ('PERM_VIEW_AUDIT_LOG', 'View Audit Log', 'system', 'See full audit trail'),
    ('PROJECT_PERM_CREATE', 'Create Projects', 'project', 'Create new projects'),
    ('PROJECT_PERM_EDIT', 'Edit Project', 'project', 'Edit project details'),
    ('PROJECT_PERM_VIEW', 'View Project', 'project', 'Read-only access to project'),
    ('PROJECT_PERM_REQUEST', 'Submit Design Request', 'project', 'Create design requests'),
    ('PROJECT_PERM_ASSIGN', 'Assign Designer', 'project', 'Assign designers to requests'),
    ('PROJECT_PERM_REVIEW', 'Review Design', 'project', 'Accept or request correction'),
    ('PROJECT_PERM_VERIFY', 'Verify Design', 'project', 'Perform design verification'),
    ('PROJECT_PERM_APPROVE', 'Final Approval', 'project', 'Give final approval'),
    ('PROJECT_PERM_COMPLETE', 'Mark Complete', 'project', 'Mark design as completed'),
    ('PROJECT_PERM_COMMENT', 'Comment', 'project', 'Write comments on requests'),
    ('DESIGN_PERM_WORK', 'Do Design Work', 'design', 'Be assigned and submit design work'),
    ('DESIGN_PERM_UPLOAD', 'Upload Files', 'design', 'Upload attachments'),
    ('DESIGN_PERM_REVISE', 'Revise Design', 'design', 'Resubmit after correction'),
    ('VIS_PERM_DASHBOARD', 'Dashboard Access', 'visibility', 'See main dashboard'),
    ('VIS_PERM_WORKFLOW_BOARD', 'Workflow Board', 'visibility', 'See Kanban workflow board'),
    ('VIS_PERM_TEAM_PAGE', 'Team Page', 'visibility', 'See team member list'),
    ('VIS_PERM_USER_PROFILES', 'User Profiles', 'visibility', 'View other users profiles'),
    ('VIS_PERM_NOTIFICATIONS', 'Notifications', 'visibility', 'Receive notifications'),
    ('SCOPE_ALL_REQUESTS', 'See All Requests', 'scope', 'See every design request'),
    ('SCOPE_OWN_REQUESTS', 'See Own Requests', 'scope', 'See only own requests'),
    ('SCOPE_TEAM_REQUESTS', 'See Team Requests', 'scope', 'See team/dept requests'),
]

SYSTEM_TEMPLATES = {
    'Head of Design': {
        'description': 'Commonly used for design department leads',
        'global': [
            'VIS_PERM_DASHBOARD', 'VIS_PERM_WORKFLOW_BOARD',
            'VIS_PERM_TEAM_PAGE', 'VIS_PERM_USER_PROFILES',
            'VIS_PERM_NOTIFICATIONS', 'PERM_VIEW_ALL_PROJECTS',
            'PERM_VIEW_REPORTS', 'SCOPE_ALL_REQUESTS',
        ],
        'project': [
            'PROJECT_PERM_VIEW', 'PROJECT_PERM_ASSIGN',
            'PROJECT_PERM_REVIEW', 'PROJECT_PERM_VERIFY',
            'PROJECT_PERM_APPROVE', 'PROJECT_PERM_COMPLETE',
            'PROJECT_PERM_COMMENT', 'DESIGN_PERM_WORK',
            'DESIGN_PERM_UPLOAD', 'DESIGN_PERM_REVISE',
        ],
    },
    'Designer': {
        'description': 'Standard design execution permissions',
        'global': [
            'VIS_PERM_DASHBOARD', 'VIS_PERM_NOTIFICATIONS',
            'SCOPE_OWN_REQUESTS',
        ],
        'project': [
            'PROJECT_PERM_VIEW', 'PROJECT_PERM_COMMENT',
            'DESIGN_PERM_WORK', 'DESIGN_PERM_UPLOAD', 'DESIGN_PERM_REVISE',
        ],
    },
    'Verifier': {
        'description': 'Verification team permissions',
        'global': [
            'VIS_PERM_DASHBOARD', 'VIS_PERM_NOTIFICATIONS',
            'SCOPE_TEAM_REQUESTS',
        ],
        'project': [
            'PROJECT_PERM_VIEW', 'PROJECT_PERM_VERIFY', 'PROJECT_PERM_COMMENT',
            'DESIGN_PERM_UPLOAD',
        ],
    },
    'Design Requester': {
        'description': 'Project requester permissions',
        'global': [
            'VIS_PERM_DASHBOARD', 'VIS_PERM_NOTIFICATIONS',
            'SCOPE_OWN_REQUESTS',
        ],
        'project': [
            'PROJECT_PERM_VIEW', 'PROJECT_PERM_REQUEST', 'PROJECT_PERM_COMMENT',
        ],
    },
    'View Only': {
        'description': 'Read-only project access',
        'global': ['SCOPE_OWN_REQUESTS'],
        'project': ['PROJECT_PERM_VIEW'],
    },
    'Admin': {
        'description': 'Full system administrator',
        'global': [
            'PERM_ADMIN_PANEL', 'PERM_VIEW_ALL_PROJECTS', 'PERM_VIEW_REPORTS',
            'PERM_MANAGE_USERS', 'PERM_MANAGE_PERMISSIONS', 'PERM_VIEW_AUDIT_LOG',
            'VIS_PERM_DASHBOARD', 'VIS_PERM_WORKFLOW_BOARD', 'VIS_PERM_TEAM_PAGE',
            'VIS_PERM_USER_PROFILES', 'VIS_PERM_NOTIFICATIONS',
            'PROJECT_PERM_CREATE', 'SCOPE_ALL_REQUESTS',
        ],
        'project': [
            'PROJECT_PERM_VIEW', 'PROJECT_PERM_EDIT', 'PROJECT_PERM_REQUEST',
            'PROJECT_PERM_ASSIGN', 'PROJECT_PERM_REVIEW', 'PROJECT_PERM_VERIFY',
            'PROJECT_PERM_APPROVE', 'PROJECT_PERM_COMPLETE', 'PROJECT_PERM_COMMENT',
            'DESIGN_PERM_WORK', 'DESIGN_PERM_UPLOAD', 'DESIGN_PERM_REVISE',
        ],
    },
}

ROLE_TEMPLATE_MAP = {
    UserRole.ADMIN: 'Admin',
    UserRole.HEAD_OF_DESIGN: 'Head of Design',
    UserRole.DESIGNER: 'Designer',
    UserRole.VERIFICATION_TEAM: 'Verifier',
    UserRole.DESIGN_REQUESTER: 'Design Requester',
}


class Command(BaseCommand):
    help = 'Seed permission definitions, system templates, and assign demo user permissions'

    @transaction.atomic
    def handle(self, *args, **options):
        perm_by_code = {}
        for code, name, category, description in ALL_PERMISSIONS:
            perm, _ = Permission.objects.update_or_create(
                code=code,
                defaults={'name': name, 'category': category, 'description': description},
            )
            perm_by_code[code] = perm

        for name, config in SYSTEM_TEMPLATES.items():
            template, _ = RoleTemplate.objects.update_or_create(
                name=name,
                defaults={
                    'description': config['description'],
                    'is_system_template': True,
                },
            )
            all_codes = config['global'] + config['project']
            template.permissions.set([perm_by_code[c] for c in all_codes])

        admin_user = User.objects.filter(username='admin').first()
        projects = list(Project.objects.all())

        for user in User.objects.filter(is_active=True):
            template_name = ROLE_TEMPLATE_MAP.get(user.role)
            if not template_name:
                continue
            PermissionService.apply_template_to_user(
                user,
                template_name,
                granted_by=admin_user,
                projects=projects,
            )

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(perm_by_code)} permissions, '
            f'{len(SYSTEM_TEMPLATES)} templates, '
            f'and applied permissions to {User.objects.filter(is_active=True).count()} users'
        ))
