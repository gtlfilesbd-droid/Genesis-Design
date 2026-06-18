from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.core.settings_forms import ensure_role_permissions
from apps.designs.models import DesignRequest, DesignStatus, DesignSubmission, DrawingType, RequestAttachment
from apps.projects.models import Project
from apps.workflow.services import transition


class ReferenceOnlyFileStorageTests(TestCase):
    def setUp(self):
        ensure_role_permissions()
        self.client = Client()
        self.requester = User.objects.create_user(
            username='reqref', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='RR001',
        )
        self.designer = User.objects.create_user(
            username='desref', password='pass', role=UserRole.DESIGNER, employee_id='DR001',
        )
        self.hod = User.objects.create_user(
            username='hodref', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='HR001',
        )
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )
        self.project = Project.objects.create(
            name='Ref Project', code='PRJ-REF', client_name='Client',
            start_date=date.today(), created_by=self.requester,
        )
        self.design = DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            priority='medium',
            requested_by=self.requester,
            assigned_designer=self.designer,
            status=DesignStatus.IN_PROGRESS,
            current_holder=self.designer,
        )

    def test_design_create_ignores_file_upload(self):
        self.client.login(username='reqref', password='pass')
        upload = SimpleUploadedFile('brief.pdf', b'pdf-content', content_type='application/pdf')
        url = reverse('projects:request_new', kwargs={'pk': self.project.pk})
        response = self.client.post(url, {
            'drawing_type': self.drawing_type.pk,
            'priority': 'medium',
            'request_message': 'Need drawing',
            'target_completion_date': '',
            'attachments': upload,
        })
        self.assertEqual(response.status_code, 302)
        design = DesignRequest.objects.filter(project=self.project).order_by('-pk').first()
        self.assertIsNotNone(design)
        self.assertEqual(RequestAttachment.objects.filter(design=design).count(), 0)

    def test_submit_work_auto_generates_metadata(self):
        transition(self.design, 'submit_work', self.designer, comments='Initial submit')
        self.design.refresh_from_db()
        submission = DesignSubmission.objects.get(design=self.design)
        self.assertTrue(submission.file_name.endswith('-V01'))
        self.assertIn('ID', submission.file_name)
        self.assertIsNotNone(submission.revision_date)
        self.assertEqual(submission.change_summary, 'Initial submit')
        self.assertFalse(submission.file)

    def test_design_detail_hides_attachment_download_urls(self):
        RequestAttachment.objects.create(
            design=self.design,
            file=SimpleUploadedFile('legacy.pdf', b'x', content_type='application/pdf'),
            filename='legacy.pdf',
            uploaded_by=self.requester,
        )
        self.client.login(username='reqref', password='pass')
        response = self.client.get(reverse('requests:detail', kwargs={'pk': self.design.pk}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('/media/', content)
        self.assertNotIn('Download', content)
        self.assertIn('archived', content.lower())
