from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    label = 'core'

    def ready(self):
        from django.conf import settings

        avatars_dir = settings.MEDIA_ROOT / 'avatars'
        avatars_dir.mkdir(parents=True, exist_ok=True)
