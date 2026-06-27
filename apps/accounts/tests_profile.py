import os
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts.models import User, UserRole
from apps.core.settings_forms import ensure_role_permissions


def _test_image(name='avatar.png'):
    buffer = BytesIO()
    Image.new('RGB', (64, 64), color='blue').save(buffer, format='PNG')
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type='image/png')


class ProfileAvatarTests(TestCase):
    def setUp(self):
        ensure_role_permissions()
        self.client = Client()
        self.user = User.objects.create_user(
            username='rahim',
            password='pass',
            role=UserRole.DESIGNER,
            employee_id='D100',
            first_name='Rahim',
            last_name='Ahmed',
        )
        self.admin = User.objects.create_user(
            username='admin',
            password='pass',
            role=UserRole.ADMIN,
            employee_id='A100',
            is_staff=True,
        )

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_profile_avatar_upload(self):
        self.client.login(username='rahim', password='pass')
        response = self.client.post(
            reverse('accounts:profile'),
            {
                'first_name': 'Rahim',
                'last_name': 'Ahmed',
                'email': '',
                'mobile_number': '',
                'designation': '',
                'department': '',
                'avatar': _test_image(),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar)
        self.assertTrue(self.user.avatar.name.startswith('avatars/'))
        self.assertTrue(os.path.exists(self.user.avatar.path))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_admin_user_edit_avatar_upload(self):
        self.client.login(username='admin', password='pass')
        response = self.client.post(
            reverse('accounts:user_edit', kwargs={'pk': self.user.pk}),
            {
                'first_name': 'Rahim',
                'last_name': 'Ahmed',
                'email': '',
                'employee_id': 'D100',
                'designation': '',
                'department': '',
                'role': UserRole.DESIGNER,
                'team': '',
                'manager': '',
                'mobile_number': '',
                'status': self.user.status,
                'is_active': 'on',
                'avatar': _test_image('admin-set.png'),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar)
        self.assertTrue(os.path.exists(self.user.avatar.path))
