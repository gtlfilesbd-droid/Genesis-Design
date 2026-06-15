# Genesis Design Management System

Design workflow management platform built with Django + PostgreSQL per SRS v1.0.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env
```

Edit `.env` with your PostgreSQL credentials:

```env
DB_NAME=genesis_design
DB_USER=genesis_admin
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

`DB_HOST=localhost` is correct when PostgreSQL runs on the same PC as Django. Remote users open the **website URL** in a browser; Django still talks to the database on `localhost`.

### 3. Migrate and seed

Create the database and user in PostgreSQL first (pgAdmin or `psql`), then:

```bash
python manage.py migrate
python manage.py seed_data
```

**Optional — Docker:** `docker compose up -d db` only if you prefer a container instead of local PostgreSQL.

### 4. Run server

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Demo Users

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| Head of Design | hod | hod123 |
| Designer | designer1 | design123 |
| Designer | designer2 | design123 |
| Verification | verifier | verify123 |
| Requester | requester | request123 |

Django Admin: http://127.0.0.1:8000/django-admin/

## Features

- **Phase 1**: Projects, design requests, 11-step workflow, role dashboards, activity logs
- **Phase 2**: SLA tracking, notifications, Kanban board, version history, audit trail, reports (CSV/Excel/PDF)
- **Phase 3**: KPIs, leaderboard, workload balancing, executive dashboard, drawing library

## Workflow

1. Requester creates project → submits design request
2. Head of Design acknowledges → assigns designer
3. Designer accepts → submits work
4. Head of Design reviews → accepts or requests correction
5. Verification team verifies → approves or requests correction
6. Head of Design marks completed

## Celery (optional)

```bash
celery -A genesis_design worker -l info
celery -A genesis_design beat -l info
```

Runs SLA status checks and escalation tasks.
