from datetime import date

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User, UserRole
from apps.core.models import RolePermission, UserExtraPermission
from apps.projects.models import Project, ProjectDirector, ProjectEngineer
from apps.projects.views import ProjectForm


class ProjectTeamFormTests(TestCase):
    def setUp(self):
        self.director_active = ProjectDirector.objects.create(name='Director One')
        self.director_inactive = ProjectDirector.objects.create(
            name='Director Retired', is_active=False,
        )
        self.engineer_active = ProjectEngineer.objects.create(name='Engineer One')
        self.engineer_inactive = ProjectEngineer.objects.create(
            name='Engineer Retired', is_active=False,
        )
        self.lead_a = User.objects.create_user(
            username='lead_a',
            password='pass',
            role=UserRole.VERIFICATION_TEAM,
            employee_id='LA001',
            first_name='Kamruzzaman',
            last_name='Lead',
        )
        self.lead_b = User.objects.create_user(
            username='lead_b',
            password='pass',
            role=UserRole.VERIFICATION_TEAM,
            employee_id='LB001',
            first_name='Tarikul',
            last_name='Islam',
        )
        UserExtraPermission.objects.create(user=self.lead_a, can_site_engineer=True)
        UserExtraPermission.objects.create(user=self.lead_b, can_site_engineer=True)

    def test_director_engineer_querysets_only_active(self):
        form = ProjectForm()
        director_ids = set(form.fields['project_director'].queryset.values_list('pk', flat=True))
        engineer_ids = set(form.fields['project_engineer'].queryset.values_list('pk', flat=True))
        self.assertEqual(director_ids, {self.director_active.pk})
        self.assertEqual(engineer_ids, {self.engineer_active.pk})

    def test_coordinator_manager_queryset_uses_site_engineers(self):
        form = ProjectForm()
        lead_ids = set(form.fields['project_coordinator'].queryset.values_list('pk', flat=True))
        self.assertEqual(lead_ids, {self.lead_a.pk, self.lead_b.pk})

    def test_same_user_as_coordinator_and_manager_rejected(self):
        form = ProjectForm(data={
            'client_name': 'Client',
            'code': 'TEAM01',
            'address': '',
            'project_director': self.director_active.pk,
            'project_engineer': self.engineer_active.pk,
            'project_coordinator': self.lead_a.pk,
            'project_manager': self.lead_a.pk,
            'start_date': date.today().isoformat(),
            'expected_completion_date': '',
            'description': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('project_coordinator', form.errors)
        self.assertIn('project_manager', form.errors)

    def test_manager_queryset_excludes_selected_coordinator_on_post(self):
        form = ProjectForm(data={
            'client_name': 'Client',
            'code': 'TEAM02',
            'address': '',
            'project_coordinator': self.lead_a.pk,
            'start_date': date.today().isoformat(),
        })
        manager_ids = set(form.fields['project_manager'].queryset.values_list('pk', flat=True))
        self.assertEqual(manager_ids, {self.lead_b.pk})

    def test_coordinator_queryset_excludes_selected_manager_on_post(self):
        form = ProjectForm(data={
            'client_name': 'Client',
            'code': 'TEAM03',
            'address': '',
            'project_manager': self.lead_b.pk,
            'start_date': date.today().isoformat(),
        })
        coordinator_ids = set(form.fields['project_coordinator'].queryset.values_list('pk', flat=True))
        self.assertEqual(coordinator_ids, {self.lead_a.pk})

    def test_site_lead_options_property(self):
        form = ProjectForm()
        names = {item['name'] for item in form.site_lead_options}
        self.assertIn('Kamruzzaman Lead', names)
        self.assertIn('Tarikul Islam', names)


class ProjectCreateTeamFieldsTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            username='creator',
            password='pass',
            role=UserRole.DESIGN_REQUESTER,
            employee_id='CR001',
            first_name='Creator',
            last_name='User',
        )
        RolePermission.objects.filter(role=UserRole.DESIGN_REQUESTER).update(
            can_create_project=True,
        )
        self.director = ProjectDirector.objects.create(name='Site Director')
        self.engineer = ProjectEngineer.objects.create(name='Site Engineer')
        self.coordinator = User.objects.create_user(
            username='coord',
            password='pass',
            role=UserRole.VERIFICATION_TEAM,
            employee_id='CO001',
            first_name='Project',
            last_name='Coordinator',
        )
        self.manager = User.objects.create_user(
            username='mgr',
            password='pass',
            role=UserRole.VERIFICATION_TEAM,
            employee_id='MG001',
            first_name='Project',
            last_name='Manager',
        )
        UserExtraPermission.objects.create(user=self.coordinator, can_site_engineer=True)
        UserExtraPermission.objects.create(user=self.manager, can_site_engineer=True)
        self.client = Client()
        self.client.login(username='creator', password='pass')

    def test_create_project_saves_team_fields(self):
        response = self.client.post(reverse('projects:new'), {
            'client_name': 'Essential Clothing',
            'code': 'ESS-TEAM',
            'address': 'Dhaka',
            'project_director': self.director.pk,
            'project_engineer': self.engineer.pk,
            'project_coordinator': self.coordinator.pk,
            'project_manager': self.manager.pk,
            'start_date': date.today().isoformat(),
            'expected_completion_date': '',
            'description': 'Team test',
        })
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(code='ESS-TEAM')
        self.assertEqual(project.project_director_id, self.director.pk)
        self.assertEqual(project.project_engineer_id, self.engineer.pk)
        self.assertEqual(project.project_coordinator_id, self.coordinator.pk)
        self.assertEqual(project.project_manager_id, self.manager.pk)
