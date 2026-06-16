from datetime import date

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.core.models import RolePermission
from apps.core.settings_forms import ensure_role_permissions
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.permissions.services import PermissionService
from apps.projects.models import Project


class RoleBasedPermissionTests(TestCase):
    def setUp(self):
        ensure_role_permissions()
        self.hod = User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='H1',
        )
        self.compliance = User.objects.create_user(
            username='cmp', password='pass', role=UserRole.COMPLIANCE_TEAM, employee_id='C1',
        )
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R1',
        )
        self.project = Project.objects.create(
            name='P', code='P1', client_name='C', start_date=date.today(), created_by=self.requester,
        )

    def test_hod_has_assign_and_review_from_role_matrix(self):
        self.assertTrue(PermissionService.has_global_permission(self.hod, 'PROJECT_PERM_ASSIGN'))
        self.assertTrue(PermissionService.has_global_permission(self.hod, 'PROJECT_PERM_REVIEW'))
        self.assertTrue(PermissionService.has_global_permission(self.hod, 'SCOPE_ALL_REQUESTS'))

    def test_compliance_role_has_compliance_permission(self):
        perms = RolePermission.objects.get(role=UserRole.COMPLIANCE_TEAM)
        self.assertTrue(perms.can_compliance)
        self.assertTrue(
            PermissionService.has_project_permission(
                self.compliance, self.project, 'PROJECT_PERM_COMPLIANCE',
            )
        )

    def test_settings_matrix_change_affects_access(self):
        rp = RolePermission.objects.get(role=UserRole.HEAD_OF_DESIGN)
        rp.can_assign_designer = False
        rp.save()
        self.hod._cached_role_perms = None
        self.assertFalse(PermissionService.has_global_permission(self.hod, 'PROJECT_PERM_ASSIGN'))

    def test_get_verifiers_returns_verification_role_users(self):
        verifier = User.objects.create_user(
            username='ver', password='pass', role=UserRole.VERIFICATION_TEAM, employee_id='V1',
        )
        verifiers = PermissionService.get_verifiers(self.project)
        self.assertIn(verifier, verifiers)

    def test_filter_design_requests_scopes_requester_to_own(self):
        drawing_type = DrawingType.objects.create(name='ID', code_prefix='ID', allowed_days=3)
        own = DesignRequest.objects.create(
            project=self.project, drawing_type=drawing_type, requested_by=self.requester,
        )
        other_user = User.objects.create_user(
            username='other', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R2',
        )
        other = DesignRequest.objects.create(
            project=self.project, drawing_type=drawing_type, requested_by=other_user,
        )
        visible = PermissionService.filter_design_requests(
            self.requester, DesignRequest.objects.all(),
        )
        self.assertIn(own, visible)
        self.assertNotIn(other, visible)

    def test_extra_permission_grants_verify_to_designer(self):
        designer = User.objects.create_user(
            username='des', password='pass', role=UserRole.DESIGNER, employee_id='D1',
        )
        from apps.core.models import UserExtraPermission
        UserExtraPermission.objects.create(user=designer, can_verify=True)
        self.assertTrue(
            PermissionService.has_project_permission(
                designer, self.project, 'PROJECT_PERM_VERIFY',
            )
        )
        self.assertIn(designer, list(PermissionService.get_verifiers(self.project)))

    def test_permissions_profile_includes_extras(self):
        from apps.core.models import UserExtraPermission
        UserExtraPermission.objects.create(user=self.hod, can_verify=True)
        profile = PermissionService.get_user_permissions_profile(self.hod)
        extra_labels = [p['label'] for p in profile['extra_permissions']]
        self.assertIn('Verify Designs', extra_labels)

    def test_permissions_profile_returns_role_flags(self):
        profile = PermissionService.get_user_permissions_profile(self.hod)
        labels = [p['label'] for p in profile['role_permissions']]
        self.assertIn('Assign Designers', labels)
        self.assertIn('Review Designs', labels)
