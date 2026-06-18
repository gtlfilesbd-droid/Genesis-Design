from apps.accounts.models import UserRole
from apps.designs.models import DesignStatus
from apps.permissions.services import PermissionService
from apps.workflow.services import WORKFLOW_ACTIONS


def workflow_role_allows(user, action: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.role == UserRole.ADMIN:
        return True
    config = WORKFLOW_ACTIONS.get(action)
    if not config:
        return False
    return user.role in config['roles']


def can_run_workflow_action(user, project, action: str, permission_code: str) -> bool:
    if workflow_role_allows(user, action):
        return True
    return PermissionService.has_project_permission(user, project, permission_code)


def can_user_submit_work(user, design) -> bool:
    if not user or not user.is_authenticated:
        return False
    if not design.assigned_designer_id or design.assigned_designer_id != user.pk:
        return False
    project = design.project
    return (
        PermissionService.has_project_permission(user, project, 'DESIGN_PERM_WORK')
        or user.role in (UserRole.DESIGNER, UserRole.HEAD_OF_DESIGN, UserRole.ADMIN)
    )


def design_action_flags(user, design) -> dict:
    project = design.project
    return {
        'can_acknowledge': can_run_workflow_action(
            user, project, 'acknowledge', 'PROJECT_PERM_ASSIGN',
        ),
        'can_assign': can_run_workflow_action(
            user, project, 'assign', 'PROJECT_PERM_ASSIGN',
        ),
        'can_do_design_work': (
            PermissionService.has_project_permission(user, project, 'DESIGN_PERM_WORK')
            or workflow_role_allows(user, 'accept_assignment')
        ),
        'can_submit_work': can_user_submit_work(user, design),
        'can_view_project': PermissionService.has_project_permission(
            user, project, 'PROJECT_PERM_VIEW',
        ),
        'can_review': can_run_workflow_action(
            user, project, 'send_to_verification', 'PROJECT_PERM_REVIEW',
        ),
        'can_send_to_verification': can_run_workflow_action(
            user, project, 'send_to_verification', 'PROJECT_PERM_REVIEW',
        ),
        'can_send_to_compliance': can_run_workflow_action(
            user, project, 'send_to_compliance', 'PROJECT_PERM_APPROVE',
        ),
        'can_revise': (
            PermissionService.has_project_permission(user, project, 'DESIGN_PERM_REVISE')
            or workflow_role_allows(user, 'resubmit')
        ),
        'can_verify': (
            design.status == DesignStatus.VERIFICATION_PENDING
            and design.assigned_verifier_id == user.pk
            and can_run_workflow_action(
                user, project, 'verify_approved', 'PROJECT_PERM_VERIFY',
            )
        ),
        'can_acknowledge_verification': (
            design.status == DesignStatus.VERIFICATION_PENDING_ACK
            and design.assigned_verifier_id == user.pk
            and can_run_workflow_action(
                user, project, 'accept_verification', 'PROJECT_PERM_VERIFY',
            )
        ),
        'can_compliance_review': (
            design.status == DesignStatus.COMPLIANCE_PENDING
            and design.assigned_compliance_officer_id == user.pk
            and can_run_workflow_action(
                user, project, 'compliance_approved', 'PROJECT_PERM_COMPLIANCE',
            )
        ),
        'can_acknowledge_compliance': (
            design.status == DesignStatus.COMPLIANCE_PENDING_ACK
            and design.assigned_compliance_officer_id == user.pk
            and can_run_workflow_action(
                user, project, 'accept_compliance', 'PROJECT_PERM_COMPLIANCE',
            )
        ),
        'can_forward_to_designer': can_run_workflow_action(
            user, project, 'forward_to_designer', 'PROJECT_PERM_ASSIGN',
        ),
        'can_hod_fast_complete': can_run_workflow_action(
            user, project, 'hod_fast_complete', 'PROJECT_PERM_COMPLETE',
        ),
        'can_complete': can_run_workflow_action(
            user, project, 'complete', 'PROJECT_PERM_COMPLETE',
        ),
        'can_cancel_request': (
            design.status == DesignStatus.NEW_REQUEST
            and design.requested_by_id == user.pk
            and PermissionService.has_project_permission(user, project, 'PROJECT_PERM_REQUEST')
        ) or (
            PermissionService.has_global_permission(user, 'PERM_ADMIN_PANEL')
            and design.status not in (DesignStatus.COMPLETED, DesignStatus.CANCELLED)
        ),
    }
