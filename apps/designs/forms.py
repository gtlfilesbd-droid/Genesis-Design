from django import forms
from django.db import transaction

from .models import DesignRequest, DesignStatus, DrawingType


INPUT = 'w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

class DesignRequestForm(forms.ModelForm):
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
        if project:
            self.fields['reference_design'].queryset = DesignRequest.objects.filter(
                project=project,
                status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED],
            )
        self.fields['reference_design'].required = False


def create_design_request(project, user, cleaned_data):
    with transaction.atomic():
        design = DesignRequest(
            project=project,
            drawing_type=cleaned_data['drawing_type'],
            priority=cleaned_data['priority'],
            target_completion_date=cleaned_data.get('target_completion_date'),
            request_message=cleaned_data.get('request_message', ''),
            reference_design=cleaned_data.get('reference_design'),
            requested_by=user,
            status=DesignStatus.NEW_REQUEST,
            current_holder=None,
        )
        design.save()
    return design
