from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.permissions.decorators import require_global_permission
from apps.permissions.services import PermissionService
from apps.accounts.models import User, UserRole
from apps.designs.models import DesignRequest, DesignStatus

from .services import WorkflowError, suggest_designer, transition
from .permissions import can_run_workflow_action, can_user_submit_work, design_action_flags


INPUT = 'w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'


class AssignDesignerForm(forms.Form):
    designer = forms.ModelChoiceField(
        queryset=User.objects.filter(role=UserRole.DESIGNER, is_active=True),
        widget=forms.Select(attrs={'class': INPUT}),
    )
    due_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': INPUT}),
        required=False,
    )
    instructions = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': INPUT}), required=False)


class CommentForm(forms.Form):
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': INPUT, 'placeholder': 'Add a comment (optional)'}),
        required=False,
        label='Comment',
    )


class SendToVerificationForm(forms.Form):
    verifier = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={'class': INPUT}),
        label='Verification Team Member',
    )
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': INPUT}),
        required=False,
        label='Message',
    )

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields['verifier'].queryset = PermissionService.get_verifiers(project)


class SendToComplianceForm(forms.Form):
    compliance_officer = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={'class': INPUT}),
        label='Compliance Team Member',
    )
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': INPUT}),
        required=True,
        label='Message',
    )

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields['compliance_officer'].queryset = PermissionService.get_compliance_officers(project)


ACTION_PERMISSIONS = {
    'acknowledge': 'PROJECT_PERM_ASSIGN',
    'assign': 'PROJECT_PERM_ASSIGN',
    'accept_assignment': 'DESIGN_PERM_WORK',
    'submit_work': 'DESIGN_PERM_WORK',
    'request_correction': 'PROJECT_PERM_REVIEW',
    'send_to_verification': 'PROJECT_PERM_REVIEW',
    'accept_design': 'PROJECT_PERM_REVIEW',
    'verification_correction': 'PROJECT_PERM_VERIFY',
    'verify_approved': 'PROJECT_PERM_VERIFY',
    'send_to_compliance': 'PROJECT_PERM_APPROVE',
    'compliance_correction': 'PROJECT_PERM_COMPLIANCE',
    'compliance_approved': 'PROJECT_PERM_COMPLIANCE',
    'forward_to_designer': 'PROJECT_PERM_ASSIGN',
    'resubmit': 'DESIGN_PERM_REVISE',
    'hod_fast_complete': 'PROJECT_PERM_COMPLETE',
    'complete': 'PROJECT_PERM_COMPLETE',
}


def _check_workflow_permission(request, design, action):
    required = ACTION_PERMISSIONS.get(action)
    if not required:
        return True
    project = design.project
    if action in ('accept_assignment', 'submit_work', 'resubmit'):
        if action in ('submit_work', 'resubmit'):
            return can_user_submit_work(request.user, design)
        if can_run_workflow_action(request.user, project, action, required):
            return True
        if design.assigned_designer_id == request.user.pk:
            return PermissionService.has_project_permission(
                request.user, project, 'DESIGN_PERM_WORK',
            )
        return False
    return can_run_workflow_action(request.user, project, action, required)


@login_required
def workflow_action(request, pk, action):
    design = get_object_or_404(DesignRequest, pk=pk)
    if not _check_workflow_permission(request, design, action):
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('requests:detail', pk=pk)

    form_actions = {
        'assign': AssignDesignerForm,
        'submit_work': CommentForm,
        'resubmit': CommentForm,
        'request_correction': CommentForm,
        'verification_correction': CommentForm,
        'compliance_correction': CommentForm,
        'accept_design': lambda **kw: SendToVerificationForm(project=design.project, **kw),
        'send_to_verification': lambda **kw: SendToVerificationForm(project=design.project, **kw),
        'send_to_compliance': lambda **kw: SendToComplianceForm(project=design.project, **kw),
        'verify_approved': CommentForm,
        'compliance_approved': CommentForm,
    }

    if request.method == 'GET' and action in form_actions:
        form = form_actions[action]()
        from apps.core.models import CompanySettings
        company = CompanySettings.objects.first()
        return render(request, 'workflow/action_form.html', {
            'design': design,
            'action': action,
            'form': form,
            'file_sharing_policy': company.file_sharing_policy if company else '',
        })

    if request.method == 'POST':
        try:
            kwargs = {}
            if action == 'assign':
                form = AssignDesignerForm(request.POST)
                if not form.is_valid():
                    return render(request, 'workflow/action_form.html', {
                        'design': design, 'action': action, 'form': form,
                    })
                kwargs = form.cleaned_data
            elif action in ('submit_work', 'resubmit'):
                form = CommentForm(request.POST)
                if not form.is_valid():
                    from apps.core.models import CompanySettings
                    company = CompanySettings.objects.first()
                    return render(request, 'workflow/action_form.html', {
                        'design': design, 'action': action, 'form': form,
                        'file_sharing_policy': company.file_sharing_policy if company else '',
                    })
                kwargs['comments'] = form.cleaned_data.get('comments', '')
            elif action in ('send_to_verification', 'accept_design'):
                form = SendToVerificationForm(request.POST, project=design.project)
                if not form.is_valid():
                    return render(request, 'workflow/action_form.html', {
                        'design': design, 'action': action, 'form': form,
                    })
                kwargs = {
                    'verifier': form.cleaned_data['verifier'],
                    'comments': form.cleaned_data['comments'],
                }
            elif action == 'send_to_compliance':
                form = SendToComplianceForm(request.POST, project=design.project)
                if not form.is_valid():
                    return render(request, 'workflow/action_form.html', {
                        'design': design, 'action': action, 'form': form,
                    })
                kwargs = {
                    'compliance_officer': form.cleaned_data['compliance_officer'],
                    'comments': form.cleaned_data['comments'],
                }
            elif action in (
                'request_correction', 'verification_correction', 'compliance_correction',
                'verify_approved', 'compliance_approved',
            ):
                form = CommentForm(request.POST)
                form.is_valid()
                kwargs['comments'] = form.cleaned_data.get('comments', '')

            transition(design, action, request.user, request=request, **kwargs)
            messages.success(request, f'Action "{action}" completed successfully.')
        except WorkflowError as e:
            messages.error(request, str(e))
    return redirect('requests:detail', pk=pk)


@login_required
def assign_designer_view(request, pk):
    design = get_object_or_404(DesignRequest, pk=pk)
    if not PermissionService.has_project_permission(request.user, design.project, 'PROJECT_PERM_ASSIGN'):
        messages.error(request, "You don't have permission to assign designers.")
        return redirect('requests:detail', pk=pk)
    suggested = suggest_designer(design)
    if request.method == 'POST':
        form = AssignDesignerForm(request.POST)
        form.fields['designer'].queryset = PermissionService.get_assignable_designers(design.project)
        if form.is_valid():
            try:
                transition(design, 'assign', request.user, request=request, **form.cleaned_data)
                messages.success(request, 'Designer assigned successfully.')
                return redirect('requests:detail', pk=pk)
            except WorkflowError as e:
                messages.error(request, str(e))
    else:
        initial = {}
        if suggested:
            initial['designer'] = suggested
        form = AssignDesignerForm(initial=initial)
        form.fields['designer'].queryset = PermissionService.get_assignable_designers(design.project)
    return render(request, 'workflow/assign.html', {
        'design': design, 'form': form, 'suggested_designer': suggested,
    })


@login_required
@require_global_permission('VIS_PERM_WORKFLOW_BOARD')
def kanban_board(request):
    statuses = [
        (s.value, s.label) for s in DesignStatus
        if s not in [DesignStatus.DRAFT]
    ]
    columns = {}
    queryset = PermissionService.filter_design_requests(
        request.user,
        DesignRequest.objects.select_related(
            'project', 'drawing_type', 'assigned_designer', 'current_holder'
        ).exclude(status=DesignStatus.DRAFT),
    )

    project_id = request.GET.get('project')
    priority = request.GET.get('priority')
    designer_id = request.GET.get('designer')

    if project_id:
        queryset = queryset.filter(project_id=project_id)
    if priority:
        queryset = queryset.filter(priority=priority)
    if designer_id:
        queryset = queryset.filter(assigned_designer_id=designer_id)

    for value, label in statuses:
        columns[value] = {
            'label': label,
            'cards': list(queryset.filter(status=value).order_by('-priority', 'due_date')[:20]),
        }

    from apps.projects.models import Project
    return render(request, 'workflow/kanban.html', {
        'columns': columns,
        'projects': PermissionService.get_user_projects(request.user).filter(status='active')[:50],
        'designers': PermissionService.get_assignable_designers(
            Project.objects.filter(status='active').first()
        ) if Project.objects.filter(status='active').exists() else User.objects.none(),
    })
