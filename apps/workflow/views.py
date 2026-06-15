from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import role_required
from apps.accounts.models import User, UserRole
from apps.designs.models import DesignRequest, DesignStatus

from .services import WorkflowError, suggest_designer, transition


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


class SubmitWorkForm(forms.Form):
    file = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': INPUT}))
    internal_file_reference = forms.CharField(max_length=500, required=False, widget=forms.TextInput(attrs={'class': INPUT}))
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': INPUT}), required=False)


class CommentForm(forms.Form):
    comments = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': INPUT}), required=False)


@login_required
def workflow_action(request, pk, action):
    design = get_object_or_404(DesignRequest, pk=pk)

    form_actions = {
        'assign': AssignDesignerForm,
        'submit_work': SubmitWorkForm,
        'request_correction': CommentForm,
        'verification_correction': CommentForm,
        'accept_design': CommentForm,
        'verify_approved': CommentForm,
    }

    if request.method == 'GET' and action in form_actions:
        form_class = form_actions[action]
        form = form_class()
        return render(request, 'workflow/action_form.html', {
            'design': design, 'action': action, 'form': form,
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
            elif action == 'submit_work':
                form = SubmitWorkForm(request.POST, request.FILES)
                if not form.is_valid():
                    return render(request, 'workflow/action_form.html', {
                        'design': design, 'action': action, 'form': form,
                    })
                kwargs = form.cleaned_data
            elif action in (
                'request_correction', 'verification_correction',
                'accept_design', 'verify_approved',
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
    suggested = suggest_designer(design)
    if request.method == 'POST':
        form = AssignDesignerForm(request.POST)
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
    return render(request, 'workflow/assign.html', {
        'design': design, 'form': form, 'suggested_designer': suggested,
    })


@login_required
def kanban_board(request):
    statuses = [
        (s.value, s.label) for s in DesignStatus
        if s not in [DesignStatus.DRAFT]
    ]
    columns = {}
    queryset = DesignRequest.objects.select_related(
        'project', 'drawing_type', 'assigned_designer', 'current_holder'
    ).exclude(status=DesignStatus.DRAFT)

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
        'projects': Project.objects.filter(status='active')[:50],
        'designers': User.objects.filter(role=UserRole.DESIGNER, is_active=True),
    })
