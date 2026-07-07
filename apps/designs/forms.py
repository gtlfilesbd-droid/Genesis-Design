from django import forms
from django.db import transaction
from django.utils import timezone

from apps.permissions.services import PermissionService
from apps.systems.models import SystemName
from apps.systems.services import resolve_group_for_systems

from .models import DesignRequest, DesignStatus, DrawingType


INPUT = (
    'w-full border border-slate-200 rounded-xl bg-white px-4 py-2.5 text-sm text-slate-900 '
    'placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary-light transition'
)
SELECT = (
    'w-full appearance-none border border-slate-200 rounded-xl bg-white px-4 py-2.5 pr-10 text-sm text-slate-900 '
    'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary-light transition'
)
TEXTAREA = (
    'w-full border border-slate-200 rounded-xl bg-white px-4 py-3 text-sm text-slate-900 '
    'placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary-light transition min-h-[120px] resize-y'
)
DATE = (
    'w-full border border-slate-200 rounded-xl bg-white px-4 py-2.5 text-sm text-slate-900 '
    'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary-light transition'
)


class DesignRequestForm(forms.ModelForm):
    systems = forms.ModelMultipleChoiceField(
        queryset=SystemName.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(),
        label='System Name',
        required=True,
    )

    class Meta:
        model = DesignRequest
        fields = [
            'systems', 'drawing_type', 'priority', 'target_completion_date',
            'request_message', 'reference_design',
        ]
        widgets = {
            'drawing_type': forms.RadioSelect(),
            'priority': forms.Select(attrs={'class': INPUT}),
            'target_completion_date': forms.DateInput(attrs={'type': 'date', 'class': DATE}),
            'request_message': forms.Textarea(attrs={
                'rows': 4,
                'class': TEXTAREA,
                'placeholder': 'Describe scope, site conditions, deliverables, or any context the design team should know…',
            }),
            'reference_design': forms.Select(attrs={'class': SELECT}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.fields['drawing_type'].queryset = DrawingType.objects.filter(is_active=True)
        self.fields['drawing_type'].label = 'Drawing Type'
        self.fields['systems'].queryset = SystemName.objects.filter(is_active=True)
        self.fields['target_completion_date'].required = True
        self.fields['request_message'].label = 'Request Message'
        self.fields['request_message'].required = False
        self.fields['reference_design'].label = 'Reference Design'
        self.fields['reference_design'].required = False
        if project:
            self.fields['reference_design'].queryset = DesignRequest.objects.filter(
                project=project,
                status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED],
            )
        else:
            self.fields['reference_design'].queryset = DesignRequest.objects.none()

    def clean_systems(self):
        systems = self.cleaned_data.get('systems')
        if not systems:
            raise forms.ValidationError('At least one system must be selected.')
        try:
            self.resolved_group = resolve_group_for_systems(systems)
        except Exception as exc:
            raise forms.ValidationError(str(exc)) from exc
        return systems


def create_design_request(project, user, cleaned_data):
    systems = list(cleaned_data['systems'])
    group = resolve_group_for_systems(systems)
    with transaction.atomic():
        design = DesignRequest(
            project=project,
            drawing_type=cleaned_data['drawing_type'],
            priority=cleaned_data['priority'],
            target_completion_date=cleaned_data['target_completion_date'],
            request_message=cleaned_data.get('request_message', ''),
            reference_design=cleaned_data.get('reference_design'),
            requested_by=user,
            status=DesignStatus.REQUEST_UNDER_REVIEW,
            assigned_review_user=group.review_user,
            current_holder=group.review_user,
        )
        design.save()
        design.systems.set(systems)
        from apps.workflow.services import start_workflow_stage
        start_workflow_stage(design, DesignStatus.REQUEST_UNDER_REVIEW, group.review_user)
    return design


class CancelRequestForm(forms.Form):
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': TEXTAREA, 'placeholder': 'Reason for cancellation...'}),
        required=True,
        label='Cancel Reason',
    )
