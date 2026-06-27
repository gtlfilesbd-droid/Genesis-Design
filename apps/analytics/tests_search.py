from datetime import date, timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.core.settings_forms import ensure_role_permissions
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.projects.models import Project


class DesignLibrarySearchTests(TestCase):
    def setUp(self):
        ensure_role_permissions()
        self.client = Client()
        self.hod = User.objects.create_user(
            username='hodsearch', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='HS1',
        )
        self.designer = User.objects.create_user(
            username='dessearch', password='pass', role=UserRole.DESIGNER, employee_id='DS1',
        )
        self.other_designer = User.objects.create_user(
            username='desother', password='pass', role=UserRole.DESIGNER, employee_id='DS2',
        )
        self.requester = User.objects.create_user(
            username='reqsearch', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='RS1',
        )
        self.project = Project.objects.create(
            name='P', code='PS1', client_name='C',
            start_date=date.today(), created_by=self.requester,
        )
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )
        self.past_due = timezone.now() - timedelta(days=2)

    def _create_design(self, *, designer=None, status=DesignStatus.IN_PROGRESS, due_date=None):
        return DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            assigned_designer=designer or self.designer,
            status=status,
            due_date=due_date if due_date is not None else self.past_due,
        )

    def test_search_page_renders_overdue_filter(self):
        self.client.login(username='hodsearch', password='pass')
        response = self.client.get(reverse('analytics:search'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Running only')
        self.assertContains(response, 'Overdue only')

    def test_running_filter_excludes_completed(self):
        active = self._create_design(status=DesignStatus.IN_PROGRESS)
        self._create_design(
            designer=self.other_designer,
            status=DesignStatus.COMPLETED,
        )

        self.client.login(username='hodsearch', password='pass')
        response = self.client.get(reverse('analytics:search'), {'deadline': 'running'})
        self.assertEqual(response.status_code, 200)
        designs = list(response.context['designs'])
        self.assertEqual(len(designs), 1)
        self.assertEqual(designs[0].pk, active.pk)

    def test_legacy_overdue_param_still_works(self):
        active_overdue = self._create_design(status=DesignStatus.IN_PROGRESS)
        self._create_design(
            designer=self.other_designer,
            status=DesignStatus.IN_PROGRESS,
            due_date=timezone.now() + timedelta(days=3),
        )

        self.client.login(username='hodsearch', password='pass')
        response = self.client.get(reverse('analytics:search'), {'overdue': '1'})
        self.assertEqual(response.status_code, 200)
        designs = list(response.context['designs'])
        self.assertEqual(len(designs), 1)
        self.assertEqual(designs[0].pk, active_overdue.pk)

    def test_overdue_filter_returns_only_active_overdue_designs(self):
        active_overdue = self._create_design(status=DesignStatus.IN_PROGRESS)
        self._create_design(
            designer=self.other_designer,
            status=DesignStatus.COMPLETED,
            due_date=self.past_due,
        )
        on_time = self._create_design(
            designer=self.other_designer,
            status=DesignStatus.IN_PROGRESS,
            due_date=timezone.now() + timedelta(days=3),
        )

        self.client.login(username='hodsearch', password='pass')
        response = self.client.get(reverse('analytics:search'), {'overdue': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['result_count'], 1)
        self.assertContains(response, '1 record found')
        designs = list(response.context['designs'])
        self.assertEqual(len(designs), 1)
        self.assertEqual(designs[0].pk, active_overdue.pk)
        self.assertNotIn(on_time.pk, {d.pk for d in designs})

    def test_overdue_filter_composes_with_designer_filter(self):
        target = self._create_design(designer=self.designer, status=DesignStatus.IN_PROGRESS)
        self._create_design(designer=self.other_designer, status=DesignStatus.IN_PROGRESS)

        self.client.login(username='hodsearch', password='pass')
        response = self.client.get(reverse('analytics:search'), {
            'overdue': '1',
            'designer': self.designer.pk,
        })
        self.assertEqual(response.status_code, 200)
        designs = list(response.context['designs'])
        self.assertEqual(len(designs), 1)
        self.assertEqual(designs[0].pk, target.pk)
