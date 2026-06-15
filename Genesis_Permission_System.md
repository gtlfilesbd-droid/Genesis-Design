# Genesis Design — Permission & Role System (Complete Spec for Cursor Agent)

---

## CORE CONCEPT: Permission-Based System (NOT Role-Based)

**Critical Design Decision:**
This system does NOT use fixed roles. Instead, Admin assigns individual permissions to each user.
A user can have multiple permissions simultaneously.

Example:
- "Rahim" can be both a Designer AND a Verifier
- "Sarah" can be both Head of Design AND a Designer
- "Karim" can be a Requester for Project-A but only a Viewer for Project-B
- "Director" can view all projects but cannot submit requests on any

---

## PERMISSION CATEGORIES

There are 5 permission categories. Each user gets a combination of these.

### CATEGORY 1: SYSTEM-LEVEL PERMISSIONS
These apply globally across the entire application.

```
PERM_ADMIN_PANEL          → Can access /settings/, user management, system config
PERM_VIEW_ALL_PROJECTS    → Can see all projects in the system (not just assigned ones)
PERM_VIEW_REPORTS         → Can access /reports/ page
PERM_MANAGE_USERS         → Can create/edit/disable users
PERM_MANAGE_PERMISSIONS   → Can assign/revoke permissions (subset of admin)
PERM_VIEW_AUDIT_LOG       → Can see full audit trail
```

### CATEGORY 2: PROJECT-LEVEL PERMISSIONS
These are assigned per user per project (stored in ProjectMembership table).

```
PROJECT_PERM_CREATE       → Can create new projects (global, not per-project)
PROJECT_PERM_EDIT         → Can edit project details (name, date, description)
PROJECT_PERM_VIEW         → Can see the project and its contents (read-only)
PROJECT_PERM_REQUEST      → Can submit new design requests in this project
PROJECT_PERM_ASSIGN       → Can assign designers to requests in this project
PROJECT_PERM_REVIEW       → Can review submitted designs (accept/correction)
PROJECT_PERM_VERIFY       → Can perform verification on designs
PROJECT_PERM_APPROVE      → Can give final approval
PROJECT_PERM_COMPLETE     → Can mark design as Completed
PROJECT_PERM_COMMENT      → Can write comments on design requests
```

### CATEGORY 3: DESIGN EXECUTION PERMISSIONS
These determine what a user can DO with designs they are assigned.

```
DESIGN_PERM_WORK          → Can be assigned as a designer and submit completed work
DESIGN_PERM_UPLOAD        → Can upload files/attachments to a request
DESIGN_PERM_REVISE        → Can resubmit after correction
```

### CATEGORY 4: VISIBILITY PERMISSIONS
Control what sections/pages a user can see.

```
VIS_PERM_DASHBOARD        → Can access the main dashboard
VIS_PERM_WORKFLOW_BOARD   → Can see the Kanban workflow board
VIS_PERM_TEAM_PAGE        → Can see the team/users list
VIS_PERM_USER_PROFILES    → Can view other users' profiles and stats
VIS_PERM_NOTIFICATIONS    → Can receive and view notifications
```

### CATEGORY 5: DATA SCOPE PERMISSIONS
Control how much data a user sees within pages they can access.

```
SCOPE_ALL_REQUESTS        → Sees all design requests (not just own)
SCOPE_OWN_REQUESTS        → Sees only requests they created or are assigned to
SCOPE_TEAM_REQUESTS       → Sees requests of their department/team
```

---

## DJANGO MODELS

```python
# permissions/models.py

class Permission(models.Model):
    """Master list of all permissions in the system"""
    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=[
        ('system', 'System Level'),
        ('project', 'Project Level'),
        ('design', 'Design Execution'),
        ('visibility', 'Visibility'),
        ('scope', 'Data Scope'),
    ])

    def __str__(self):
        return f"{self.category} → {self.name}"


class UserPermission(models.Model):
    """
    Global permissions assigned to a user (apply across all projects).
    Example: PERM_VIEW_ALL_PROJECTS, PERM_ADMIN_PANEL
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_permissions_custom')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='granted_permissions')
    granted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'permission')


class ProjectMembership(models.Model):
    """
    Per-project permission assignment.
    A user can have different permissions on different projects.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_memberships')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='members')
    permissions = models.ManyToManyField(Permission, blank=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='added_members')
    added_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('user', 'project')

    def __str__(self):
        return f"{self.user.get_full_name()} in {self.project.name}"


class RoleTemplate(models.Model):
    """
    Pre-built permission bundles that admin can apply quickly.
    NOT a fixed role — just a shortcut for assigning multiple permissions at once.
    Admin can still customize after applying a template.
    """
    name = models.CharField(max_length=100)  # e.g. "Head of Design", "Designer", "Requester"
    description = models.TextField()
    permissions = models.ManyToManyField(Permission)
    is_system_template = models.BooleanField(default=False)  # system templates cannot be deleted
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
```

---

## PERMISSION HELPER / SERVICE LAYER

```python
# permissions/services.py

class PermissionService:
    """
    Central service for all permission checks.
    Use this everywhere — never check permissions directly in views.
    """

    @staticmethod
    def has_global_permission(user, permission_code: str) -> bool:
        """Check if user has a system-level permission"""
        if user.is_superuser:
            return True
        return UserPermission.objects.filter(
            user=user,
            permission__code=permission_code,
            is_active=True
        ).exists()

    @staticmethod
    def has_project_permission(user, project, permission_code: str) -> bool:
        """Check if user has a specific permission on a specific project"""
        if user.is_superuser:
            return True
        # First check global override
        if PermissionService.has_global_permission(user, 'PERM_VIEW_ALL_PROJECTS'):
            if permission_code == 'PROJECT_PERM_VIEW':
                return True
        # Then check project membership
        try:
            membership = ProjectMembership.objects.get(user=user, project=project, is_active=True)
            return membership.permissions.filter(code=permission_code).exists()
        except ProjectMembership.DoesNotExist:
            return False

    @staticmethod
    def get_user_projects(user):
        """Get all projects a user can see"""
        if user.is_superuser or PermissionService.has_global_permission(user, 'PERM_VIEW_ALL_PROJECTS'):
            return Project.objects.all()
        return Project.objects.filter(
            members__user=user,
            members__is_active=True,
            members__permissions__code='PROJECT_PERM_VIEW'
        ).distinct()

    @staticmethod
    def can_be_assigned_as_designer(user, project) -> bool:
        """Check if this user can be assigned design work"""
        return PermissionService.has_project_permission(user, project, 'DESIGN_PERM_WORK')

    @staticmethod
    def can_verify(user, project) -> bool:
        return PermissionService.has_project_permission(user, project, 'PROJECT_PERM_VERIFY')

    @staticmethod
    def get_assignable_designers(project):
        """Returns all users who can be assigned as designer on this project"""
        return User.objects.filter(
            project_memberships__project=project,
            project_memberships__is_active=True,
            project_memberships__permissions__code='DESIGN_PERM_WORK'
        ).distinct()

    @staticmethod
    def get_verifiers(project):
        """Returns all users who can verify designs on this project"""
        return User.objects.filter(
            project_memberships__project=project,
            project_memberships__is_active=True,
            project_memberships__permissions__code='PROJECT_PERM_VERIFY'
        ).distinct()

    @staticmethod
    def get_user_sidebar_items(user) -> list:
        """Returns which sidebar items this user should see"""
        items = []
        if PermissionService.has_global_permission(user, 'VIS_PERM_DASHBOARD'):
            items.append('dashboard')
        items.append('projects')  # everyone sees projects (filtered by access)
        if PermissionService.has_global_permission(user, 'VIS_PERM_WORKFLOW_BOARD'):
            items.append('workflow')
        # "My Tasks" shown if user has DESIGN_PERM_WORK or PROJECT_PERM_ASSIGN on any project
        has_tasks = ProjectMembership.objects.filter(
            user=user, is_active=True,
            permissions__code__in=['DESIGN_PERM_WORK', 'PROJECT_PERM_ASSIGN', 'PROJECT_PERM_VERIFY']
        ).exists()
        if has_tasks:
            items.append('my_tasks')
        if PermissionService.has_global_permission(user, 'VIS_PERM_TEAM_PAGE'):
            items.append('team')
        if PermissionService.has_global_permission(user, 'PERM_VIEW_REPORTS'):
            items.append('reports')
        if PermissionService.has_global_permission(user, 'PERM_ADMIN_PANEL'):
            items.append('settings')
        if PermissionService.has_global_permission(user, 'VIS_PERM_NOTIFICATIONS'):
            items.append('notifications')
        return items
```

---

## DJANGO DECORATORS FOR VIEWS

```python
# permissions/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def require_global_permission(permission_code):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not PermissionService.has_global_permission(request.user, permission_code):
                messages.error(request, "You don't have permission to access this page.")
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_project_permission(permission_code):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, pk=None, **kwargs):
            project = get_object_or_404(Project, pk=pk)
            if not PermissionService.has_project_permission(request.user, project, permission_code):
                messages.error(request, "You don't have permission for this project.")
                return redirect('projects:list')
            return view_func(request, *args, pk=pk, **kwargs)
        return wrapper
    return decorator

# Usage in views:
# @login_required
# @require_global_permission('PERM_ADMIN_PANEL')
# def settings_view(request): ...

# @login_required
# @require_project_permission('PROJECT_PERM_REQUEST')
# def create_request_view(request, pk): ...
```

---

## TEMPLATE CONTEXT: Permission Flags

In every template, inject permission flags via context processor so templates can conditionally show/hide UI elements:

```python
# permissions/context_processors.py

def user_permissions(request):
    if not request.user.is_authenticated:
        return {}

    user = request.user
    ps = PermissionService

    # Get current project from view kwargs if available
    project = getattr(request, 'current_project', None)

    ctx = {
        'sidebar_items': ps.get_user_sidebar_items(user),

        # Global flags
        'can_admin': ps.has_global_permission(user, 'PERM_ADMIN_PANEL'),
        'can_view_reports': ps.has_global_permission(user, 'PERM_VIEW_REPORTS'),
        'can_manage_users': ps.has_global_permission(user, 'PERM_MANAGE_USERS'),
        'can_create_project': ps.has_global_permission(user, 'PROJECT_PERM_CREATE'),
        'can_view_all_projects': ps.has_global_permission(user, 'PERM_VIEW_ALL_PROJECTS'),
    }

    # Project-level flags (only if we're inside a project page)
    if project:
        ctx.update({
            'can_edit_project': ps.has_project_permission(user, project, 'PROJECT_PERM_EDIT'),
            'can_request': ps.has_project_permission(user, project, 'PROJECT_PERM_REQUEST'),
            'can_assign': ps.has_project_permission(user, project, 'PROJECT_PERM_ASSIGN'),
            'can_review': ps.has_project_permission(user, project, 'PROJECT_PERM_REVIEW'),
            'can_verify': ps.has_project_permission(user, project, 'PROJECT_PERM_VERIFY'),
            'can_approve': ps.has_project_permission(user, project, 'PROJECT_PERM_APPROVE'),
            'can_complete': ps.has_project_permission(user, project, 'PROJECT_PERM_COMPLETE'),
            'can_do_design_work': ps.has_project_permission(user, project, 'DESIGN_PERM_WORK'),
            'can_comment': ps.has_project_permission(user, project, 'PROJECT_PERM_COMMENT'),
        })

    return ctx
```

Register in `settings.py`:
```python
TEMPLATES = [{
    'OPTIONS': {
        'context_processors': [
            ...
            'permissions.context_processors.user_permissions',
        ],
    },
}]
```

**In templates, use like this:**
```html
{% if can_request %}
  <a href="{% url 'requests:create' project.pk %}">+ New Design Request</a>
{% endif %}

{% if can_assign %}
  <button>Assign Designer</button>
{% endif %}

{% if can_do_design_work %}
  <button>Submit Completed Work</button>
{% endif %}
```

---

## SIDEBAR — DYNAMIC BASED ON PERMISSIONS

```html
<!-- templates/components/sidebar.html -->

<nav class="sidebar">
  <div class="logo">Genesis Design</div>

  <div class="user-info">
    [avatar] {{ request.user.get_full_name }}
    <!-- Show ALL active permission bundles as tags -->
    {% for perm_label in user_permission_labels %}
      <span class="badge">{{ perm_label }}</span>
    {% endfor %}
  </div>

  <ul class="nav-items">
    {% if 'dashboard' in sidebar_items %}
      <li><a href="{% url 'dashboard' %}">Dashboard</a></li>
    {% endif %}

    <li><a href="{% url 'projects:list' %}">Projects</a></li>

    {% if 'workflow' in sidebar_items %}
      <li><a href="{% url 'workflow:board' %}">Workflow Board</a></li>
    {% endif %}

    {% if 'my_tasks' in sidebar_items %}
      <li><a href="{% url 'tasks:my' %}">My Tasks</a></li>
    {% endif %}

    {% if 'team' in sidebar_items %}
      <li><a href="{% url 'users:list' %}">Team</a></li>
    {% endif %}

    {% if 'reports' in sidebar_items %}
      <li><a href="{% url 'reports:index' %}">Reports</a></li>
    {% endif %}

    {% if 'settings' in sidebar_items %}
      <li><a href="{% url 'settings:index' %}">Settings</a></li>
    {% endif %}

    {% if 'notifications' in sidebar_items %}
      <li><a href="{% url 'notifications:list' %}">Notifications</a></li>
    {% endif %}
  </ul>
</nav>
```

---

## ADMIN SCREENS — PERMISSION MANAGEMENT UI

### Screen: User Permission Management
**URL:** `/settings/users/<user_id>/permissions/`

```
┌──────────────────────────────────────────────────────────────────────┐
│  Manage Permissions — Rahim Ahmed                                    │
│  rahim@genesis.com · Senior Designer                                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  QUICK APPLY TEMPLATE                                                │
│  [Head of Design ▼]  [Apply Template]   ← applies a preset bundle   │
│  Note: Applying template adds permissions, does not remove existing  │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  GLOBAL / SYSTEM PERMISSIONS                                         │
│                                                                      │
│  [✅] Admin Panel Access          [✅] View All Projects             │
│  [✅] View Reports                [❌] Manage Users                  │
│  [❌] Manage Permissions          [✅] View Audit Log                │
│  [✅] Dashboard Access            [✅] View Notifications            │
│  [✅] View Workflow Board         [✅] View Team Page                │
│  [✅] View User Profiles          [❌] Create Project                │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  PROJECT-SPECIFIC PERMISSIONS                                        │
│                                                                      │
│  Project: Tower A Residential    [+ Add Project]                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  [✅] View Project    [✅] Submit Request   [✅] Assign       │   │
│  │  [✅] Review          [✅] Verify           [✅] Final Approve│   │
│  │  [✅] Do Design Work  [✅] Upload Files     [✅] Comment      │   │
│  │  [❌] Edit Project    [❌] Mark Complete                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Project: City Mall-B Commercial                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  [✅] View Project    [❌] Submit Request   [❌] Assign       │   │
│  │  [❌] Review          [❌] Verify           [❌] Final Approve│   │
│  │  [✅] Do Design Work  [✅] Upload Files     [✅] Comment      │   │
│  │  [❌] Edit Project    [❌] Mark Complete                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Project: Office Tower-C    [Remove]                                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  [✅] View Project    [❌] Submit Request   [❌] Assign       │   │
│  │  All others: ❌ (View only)                                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                                           [Cancel]  [Save Changes]   │
└──────────────────────────────────────────────────────────────────────┘
```

**Implementation notes for Cursor:**
- Each checkbox = one Permission object linked via UserPermission or ProjectMembership
- "Apply Template" does `membership.permissions.add(*template.permissions.all())` — additive only
- Save = bulk update, show success toast
- All changes logged in AuditLog with before/after state
- Warn if user tries to remove their own admin access

---

### Screen: Role Templates Management
**URL:** `/settings/role-templates/`

```
┌───────────────────────────────────────────────────────┐
│  Role Templates                         [+ New Template]│
├───────────────────────────────────────────────────────┤
│  Head of Design (System)          18 permissions       │
│  Commonly used for design department leads            │
│  [View Permissions]    [Duplicate]    🔒 Cannot Delete │
├───────────────────────────────────────────────────────┤
│  Designer (System)                10 permissions       │
│  Standard design execution permissions               │
│  [View Permissions]    [Duplicate]    🔒 Cannot Delete │
├───────────────────────────────────────────────────────┤
│  Verifier (System)                 6 permissions       │
│  [View Permissions]    [Duplicate]    🔒 Cannot Delete │
├───────────────────────────────────────────────────────┤
│  Design Requester (System)         5 permissions       │
│  [View Permissions]    [Duplicate]    🔒 Cannot Delete │
├───────────────────────────────────────────────────────┤
│  View Only (System)                2 permissions       │
│  [View Permissions]    [Duplicate]    🔒 Cannot Delete │
├───────────────────────────────────────────────────────┤
│  Senior Designer (Custom)         14 permissions       │
│  Created by Admin on 01 Jan 2025                      │
│  [View]  [Edit]  [Duplicate]  [Delete]                │
└───────────────────────────────────────────────────────┘
```

---

### Screen: Project Members Management
**URL:** `/projects/<pk>/members/`

Accessible from Project Detail page → Members tab

```
┌─────────────────────────────────────────────────────────────────────┐
│  Project Members — Tower A Residential Complex     [+ Add Member]   │
├─────────────────────────────────────────────────────────────────────┤
│  Member           │ Permissions Active          │ Since    │ Action  │
├───────────────────┼─────────────────────────────┼──────────┼─────────┤
│ [av] Sarah Ahmed  │ Assign · Review · Approve   │ 01 Jan   │ [Edit]  │
│      Head of Dept │ Verify · Complete           │          │ [Remove]│
├───────────────────┼─────────────────────────────┼──────────┼─────────┤
│ [av] Rahim Ahmed  │ Do Design Work · Upload     │ 03 Jan   │ [Edit]  │
│      Designer     │ Comment · View              │          │ [Remove]│
├───────────────────┼─────────────────────────────┼──────────┼─────────┤
│ [av] Karim (PM)   │ Request · View · Comment    │ 01 Jan   │ [Edit]  │
├───────────────────┼─────────────────────────────┼──────────┼─────────┤
│ [av] Rafi         │ Do Design Work · Verify     │ 05 Jan   │ [Edit]  │
│                   │ Upload · Comment            │          │ [Remove]│
└───────────────────┴─────────────────────────────┴──────────┴─────────┘
```

**Add Member Modal:**
```
┌───────────────────────────────────────────────────┐
│  Add Member to Tower A Residential Complex        │
├───────────────────────────────────────────────────┤
│  Select User                                      │
│  [Search user by name or email...        ▼]       │
│                                                   │
│  Apply Template (optional)                        │
│  [Select a template to pre-fill...       ▼]       │
│                                                   │
│  Project Permissions                              │
│  [✅] View Project    [✅] Submit Request          │
│  [❌] Assign          [❌] Review                  │
│  [✅] Do Design Work  [✅] Upload Files            │
│  [✅] Comment         [❌] Verify                  │
│  [❌] Final Approve   [❌] Edit Project            │
│  [❌] Mark Complete                               │
│                                                   │
│  Notes (optional)                                 │
│  [e.g. "Added as backup designer"        ]        │
│                                                   │
│  [Cancel]                        [Add Member]     │
└───────────────────────────────────────────────────┘
```

---

## DEFAULT SYSTEM TEMPLATES & THEIR PERMISSIONS

Seed these in a Django migration or management command:

```python
SYSTEM_TEMPLATES = {
    "Head of Design": {
        "global": [
            "VIS_PERM_DASHBOARD", "VIS_PERM_WORKFLOW_BOARD",
            "VIS_PERM_TEAM_PAGE", "VIS_PERM_USER_PROFILES",
            "VIS_PERM_NOTIFICATIONS", "PERM_VIEW_ALL_PROJECTS",
            "PERM_VIEW_REPORTS", "SCOPE_ALL_REQUESTS",
        ],
        "project": [
            "PROJECT_PERM_VIEW", "PROJECT_PERM_ASSIGN",
            "PROJECT_PERM_REVIEW", "PROJECT_PERM_VERIFY",
            "PROJECT_PERM_APPROVE", "PROJECT_PERM_COMPLETE",
            "PROJECT_PERM_COMMENT", "DESIGN_PERM_WORK",
            "DESIGN_PERM_UPLOAD", "DESIGN_PERM_REVISE",
        ]
    },
    "Designer": {
        "global": [
            "VIS_PERM_DASHBOARD", "VIS_PERM_NOTIFICATIONS",
            "SCOPE_OWN_REQUESTS",
        ],
        "project": [
            "PROJECT_PERM_VIEW", "PROJECT_PERM_COMMENT",
            "DESIGN_PERM_WORK", "DESIGN_PERM_UPLOAD", "DESIGN_PERM_REVISE",
        ]
    },
    "Verifier": {
        "global": [
            "VIS_PERM_DASHBOARD", "VIS_PERM_NOTIFICATIONS",
            "SCOPE_TEAM_REQUESTS",
        ],
        "project": [
            "PROJECT_PERM_VIEW", "PROJECT_PERM_VERIFY", "PROJECT_PERM_COMMENT",
            "DESIGN_PERM_UPLOAD",
        ]
    },
    "Design Requester": {
        "global": [
            "VIS_PERM_DASHBOARD", "VIS_PERM_NOTIFICATIONS",
            "SCOPE_OWN_REQUESTS",
        ],
        "project": [
            "PROJECT_PERM_VIEW", "PROJECT_PERM_REQUEST", "PROJECT_PERM_COMMENT",
        ]
    },
    "View Only": {
        "global": ["SCOPE_OWN_REQUESTS"],
        "project": ["PROJECT_PERM_VIEW"],
    },
    "Admin": {
        "global": [
            "PERM_ADMIN_PANEL", "PERM_VIEW_ALL_PROJECTS", "PERM_VIEW_REPORTS",
            "PERM_MANAGE_USERS", "PERM_MANAGE_PERMISSIONS", "PERM_VIEW_AUDIT_LOG",
            "VIS_PERM_DASHBOARD", "VIS_PERM_WORKFLOW_BOARD", "VIS_PERM_TEAM_PAGE",
            "VIS_PERM_USER_PROFILES", "VIS_PERM_NOTIFICATIONS",
            "PROJECT_PERM_CREATE", "SCOPE_ALL_REQUESTS",
        ],
        "project": [
            "PROJECT_PERM_VIEW", "PROJECT_PERM_EDIT", "PROJECT_PERM_REQUEST",
            "PROJECT_PERM_ASSIGN", "PROJECT_PERM_REVIEW", "PROJECT_PERM_VERIFY",
            "PROJECT_PERM_APPROVE", "PROJECT_PERM_COMPLETE", "PROJECT_PERM_COMMENT",
            "DESIGN_PERM_WORK", "DESIGN_PERM_UPLOAD", "DESIGN_PERM_REVISE",
        ]
    }
}
```

---

## REAL-WORLD PERMISSION EXAMPLES

**Example 1: Director (View All, Request Nothing)**
- Global: `PERM_VIEW_ALL_PROJECTS`, `VIS_PERM_DASHBOARD`, `PERM_VIEW_REPORTS`, `SCOPE_ALL_REQUESTS`
- Project permissions: `PROJECT_PERM_VIEW` on all projects
- Result: Sees everything, cannot submit requests, no action buttons appear

**Example 2: PM who is also a Designer**
- Global: `VIS_PERM_DASHBOARD`, `VIS_PERM_NOTIFICATIONS`, `SCOPE_OWN_REQUESTS`
- Project Tower-A: `PROJECT_PERM_VIEW` + `PROJECT_PERM_REQUEST` + `DESIGN_PERM_WORK`
- Project Mall-B: `PROJECT_PERM_VIEW` + `PROJECT_PERM_REQUEST` (no design work)
- Result: On Tower-A, can submit requests AND be assigned designs. On Mall-B, can only request.
- Sidebar shows: Dashboard, Projects, My Tasks, Notifications

**Example 3: Head of Design who also does Design Work**
- Apply "Head of Design" template globally
- Also add `DESIGN_PERM_WORK` + `DESIGN_PERM_UPLOAD` + `DESIGN_PERM_REVISE` on all projects
- Result: Can assign others AND appear in assignable designer list AND submit own work

**Example 4: External Consultant (One Project, View Only)**
- Global: nothing special
- Project Tower-A only: `PROJECT_PERM_VIEW`
- Result: Only sees Tower-A in projects list, read-only, no buttons anywhere
- Sidebar shows: Projects, Notifications only

---

## DESIGN REQUEST WORKFLOW — PERMISSION CHECKS AT EACH STEP

```
Step 1: Create Request
  → Requires: PROJECT_PERM_REQUEST on that project

Step 2: Acknowledge Request  
  → Requires: PROJECT_PERM_ASSIGN on that project

Step 3: Assign Designer
  → Requires: PROJECT_PERM_ASSIGN on that project
  → Designer dropdown: only users with DESIGN_PERM_WORK on that project

Step 4: Designer submits work
  → Requires: DESIGN_PERM_WORK + user must be the assigned designer
               OR user has PROJECT_PERM_ASSIGN (head can submit on behalf)

Step 5: Review (Accept / Correction)
  → Requires: PROJECT_PERM_REVIEW on that project

Step 6: Forward to Verification
  → Requires: PROJECT_PERM_REVIEW on that project
  → Verifier dropdown: only users with PROJECT_PERM_VERIFY on that project

Step 7: Verify
  → Requires: PROJECT_PERM_VERIFY + user must be the assigned verifier
               OR user has PROJECT_PERM_APPROVE

Step 8: Final Approval
  → Requires: PROJECT_PERM_APPROVE on that project

Step 9: Mark Complete
  → Requires: PROJECT_PERM_COMPLETE on that project
```

---

## AUDIT LOG — PERMISSION CHANGES

Every permission change must be logged:

```python
AuditLog.objects.create(
    action='PERMISSION_GRANTED',
    actor=request.user,
    target_user=user,
    project=project,  # null if global
    description=f"Granted '{permission.name}' to {user.get_full_name()}",
    old_value=None,
    new_value=permission.code,
    timestamp=now()
)
```

---

## APP STRUCTURE

```
genesis/
  permissions/
    __init__.py
    models.py          ← Permission, UserPermission, ProjectMembership, RoleTemplate
    services.py        ← PermissionService class
    decorators.py      ← require_global_permission, require_project_permission
    context_processors.py
    views.py           ← Permission management UI views
    urls.py
    admin.py
    migrations/
    management/
      commands/
        seed_permissions.py   ← Creates all Permission objects + system templates
```

---

## SEED COMMAND

```python
# permissions/management/commands/seed_permissions.py

ALL_PERMISSIONS = [
    # (code, name, category, description)
    ('PERM_ADMIN_PANEL', 'Admin Panel Access', 'system', 'Access settings and configuration'),
    ('PERM_VIEW_ALL_PROJECTS', 'View All Projects', 'system', 'See all projects regardless of membership'),
    ('PERM_VIEW_REPORTS', 'View Reports', 'system', 'Access the reports section'),
    ('PERM_MANAGE_USERS', 'Manage Users', 'system', 'Create/edit/disable users'),
    ('PERM_MANAGE_PERMISSIONS', 'Manage Permissions', 'system', 'Assign permissions to users'),
    ('PERM_VIEW_AUDIT_LOG', 'View Audit Log', 'system', 'See full audit trail'),
    ('PROJECT_PERM_CREATE', 'Create Projects', 'project', 'Create new projects'),
    ('PROJECT_PERM_EDIT', 'Edit Project', 'project', 'Edit project details'),
    ('PROJECT_PERM_VIEW', 'View Project', 'project', 'Read-only access to project'),
    ('PROJECT_PERM_REQUEST', 'Submit Design Request', 'project', 'Create design requests'),
    ('PROJECT_PERM_ASSIGN', 'Assign Designer', 'project', 'Assign designers to requests'),
    ('PROJECT_PERM_REVIEW', 'Review Design', 'project', 'Accept or request correction'),
    ('PROJECT_PERM_VERIFY', 'Verify Design', 'project', 'Perform design verification'),
    ('PROJECT_PERM_APPROVE', 'Final Approval', 'project', 'Give final approval'),
    ('PROJECT_PERM_COMPLETE', 'Mark Complete', 'project', 'Mark design as completed'),
    ('PROJECT_PERM_COMMENT', 'Comment', 'project', 'Write comments on requests'),
    ('DESIGN_PERM_WORK', 'Do Design Work', 'design', 'Be assigned and submit design work'),
    ('DESIGN_PERM_UPLOAD', 'Upload Files', 'design', 'Upload attachments'),
    ('DESIGN_PERM_REVISE', 'Revise Design', 'design', 'Resubmit after correction'),
    ('VIS_PERM_DASHBOARD', 'Dashboard Access', 'visibility', 'See main dashboard'),
    ('VIS_PERM_WORKFLOW_BOARD', 'Workflow Board', 'visibility', 'See Kanban workflow board'),
    ('VIS_PERM_TEAM_PAGE', 'Team Page', 'visibility', 'See team member list'),
    ('VIS_PERM_USER_PROFILES', 'User Profiles', 'visibility', 'View other users profiles'),
    ('VIS_PERM_NOTIFICATIONS', 'Notifications', 'visibility', 'Receive notifications'),
    ('SCOPE_ALL_REQUESTS', 'See All Requests', 'scope', 'See every design request'),
    ('SCOPE_OWN_REQUESTS', 'See Own Requests', 'scope', 'See only own requests'),
    ('SCOPE_TEAM_REQUESTS', 'See Team Requests', 'scope', 'See team/dept requests'),
]
```
