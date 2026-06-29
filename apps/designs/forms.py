from django import forms
from django.db import transaction
from django.utils import timezone

from apps.permissions.services import PermissionService
from apps.workflow.deadline_utils import add_allowed_duration, get_deadline_config

from .models import DesignRequest, DesignStatus, DrawingType


INPUT = 'w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'


class DesignRequestForm(forms.ModelForm):
    assigned_site_engineer = forms.ModelChoiceField(
        queryset=PermissionService.get_site_engineers(),
        widget=forms.Select(attrs={'class': INPUT}),
        label='Site Engineer',
        required=True,
    )
    engineer_due_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': INPUT}),
        required=True,
        label='Engineer Due Date',
    )
    engineer_instructions = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': INPUT}),
        required=False,
        label='Instructions for Engineer',
    )

    class Meta:
        model = DesignRequest
        fields = [
            'drawing_type', 'priority', 'target_completion_date',
            'request_message', 'reference_design',
        ]
        widgets = {
            'drawing_type': forms.Select(attrs={'class': INPUT}),
            'priority': forms.Select(attrs={'class': INPUT}),
            'target_completion_date': forms.DateInput(attrs={'type': 'date', 'class': INPUT}),
            'request_message': forms.Textarea(attrs={'rows': 4, 'class': INPUT}),
            'reference_design': forms.Select(attrs={'class': INPUT}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.fields['drawing_type'].queryset = DrawingType.objects.filter(is_active=True)
        self.fields['assigned_site_engineer'].queryset = PermissionService.get_site_engineers()
        if project:
            self.fields['reference_design'].queryset = DesignRequest.objects.filter(
                project=project,
                status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED],
            )
        self.fields['reference_design'].required = False
        if not self.is_bound and 'engineer_due_date' not in self.initial:
            drawing_type = None
            if self.data.get('drawing_type'):
                drawing_type = DrawingType.objects.filter(pk=self.data.get('drawing_type')).first()
            elif self.initial.get('drawing_type'):
                drawing_type = self.initial['drawing_type']
            if drawing_type:
                config = get_deadline_config()
                due = add_allowed_duration(
                    timezone.now(),
                    drawing_type.allowed_days,
                    drawing_type.allowed_hours,
                    count_weekends=config.count_weekends,
                )
                self.fields['engineer_due_date'].initial = timezone.localtime(due).strftime(
                    '%Y-%m-%dT%H:%M'
                )


def create_design_request(project, user, cleaned_data):
    now = timezone.now()
    engineer = cleaned_data['assigned_site_engineer']
    with transaction.atomic():
        design = DesignRequest(
            project=project,
            drawing_type=cleaned_data['drawing_type'],
            priority=cleaned_data['priority'],
            target_completion_date=cleaned_data.get('target_completion_date'),
            request_message=cleaned_data.get('request_message', ''),
            reference_design=cleaned_data.get('reference_design'),
            requested_by=user,
            assigned_site_engineer=engineer,
            engineer_due_date=cleaned_data['engineer_due_date'],
            engineer_instructions=cleaned_data.get('engineer_instructions', ''),
            engineer_assigned_at=now,
            status=DesignStatus.ENGINEER_PENDING_ACK,
            current_holder=engineer,
        )
        design.save()
    return design
