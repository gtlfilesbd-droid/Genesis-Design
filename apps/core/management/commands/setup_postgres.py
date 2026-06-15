"""Initialize PostgreSQL role and database for Genesis Design."""

import os
from pathlib import Path

import environ
import psycopg
from django.conf import settings
from django.core.management.base import BaseCommand

env = environ.Env()
env.read_env(Path(settings.BASE_DIR) / '.env')

DEFAULT_ADMIN_URLS = [
    'postgresql://postgres:postgres@localhost:5432/postgres',
    'postgresql://postgres:@localhost:5432/postgres',
    'postgresql://postgres:admin@localhost:5432/postgres',
]

DB_NAME = 'genesis_design'
DB_USER = 'genesis'
DB_PASSWORD = 'genesis'


class Command(BaseCommand):
    help = 'Create PostgreSQL user and database (requires admin connection)'

    def handle(self, *args, **options):
        admin_urls = []
        custom = os.environ.get('POSTGRES_ADMIN_URL') or env('POSTGRES_ADMIN_URL', default='')
        if custom:
            admin_urls.append(custom)
        admin_urls.extend(DEFAULT_ADMIN_URLS)

        last_error = None
        for admin_url in admin_urls:
            try:
                self._setup(admin_url)
                self.stdout.write(self.style.SUCCESS(
                    f'PostgreSQL ready: {DB_USER}@{DB_NAME} '
                    f'(DATABASE_URL=postgres://{DB_USER}:{DB_PASSWORD}@localhost:5432/{DB_NAME})'
                ))
                return
            except Exception as exc:
                last_error = exc
                continue

        self.stdout.write(self.style.ERROR(
            'Could not connect to PostgreSQL with admin credentials.\n'
            'Option A: Start Docker — docker compose up -d db\n'
            'Option B: Set POSTGRES_ADMIN_URL to your postgres superuser, e.g.:\n'
            '  POSTGRES_ADMIN_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/postgres\n'
            f'Last error: {last_error}'
        ))

    def _setup(self, admin_url):
        with psycopg.connect(admin_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', [DB_USER])
                if not cur.fetchone():
                    cur.execute(
                        f"CREATE USER {DB_USER} WITH PASSWORD %s CREATEDB",
                        [DB_PASSWORD],
                    )
                    self.stdout.write(f'Created role {DB_USER}')
                else:
                    cur.execute(f"ALTER USER {DB_USER} WITH PASSWORD %s", [DB_PASSWORD])

                cur.execute('SELECT 1 FROM pg_database WHERE datname = %s', [DB_NAME])
                if not cur.fetchone():
                    cur.execute(f'CREATE DATABASE {DB_NAME} OWNER {DB_USER}')
                    self.stdout.write(f'Created database {DB_NAME}')
                else:
                    self.stdout.write(f'Database {DB_NAME} already exists')

                cur.execute(f'GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER}')
