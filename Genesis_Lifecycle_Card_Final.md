# Genesis Design — Final Lifecycle Timeline Card (Exact Code + Implementation Prompt)

⚠️ Do NOT touch workflow logic, permissions, status transitions, or any 
backend action views. This task is ONLY about replacing the visual 
sidebar card on the Request Detail page with the exact design below. 
The underlying workflow (request → acknowledge → assign → submit → 
review → verify → compliance → approve → complete, with correction 
loops) is already working correctly.

---

## WHAT TO REMOVE

On `Home / Design Requests / Request Detail`, remove these cards 
entirely from the sidebar:
1. "Deadline Timer" card
2. "Time Breakdown" card
3. Any previous "Drawing Completion Timeline" card if one was already 
   added from an earlier pass

---

## WHAT TO BUILD: "Design Lifecycle" Card

Use the EXACT HTML/CSS structure below as the template. Do not redesign 
it — implement it as written, then wire up the dynamic Django template 
variables in place of the hardcoded example values. This card replaces 
all three previous cards with one unified, professional component that 
serves four purposes at once: status-at-a-glance, historical record, 
delay accountability, and target-date tracking.

### Reference screenshot description (what you're building)
A single white card with:
- Header row: drawing number + type on the left, project + requester 
  below it, and a colored status badge on the right (e.g. "2 days 
  overdue" in red, or "On track" in green, or "Completed on time" in 
  green)
- A 4-column stat grid: Elapsed / Allowed / Corrections / Current Stage
- A small color legend (Head of Design / Designer / Verifier / 
  Compliance / Delay)
- A horizontally-scrollable segmented timeline bar — one segment per 
  stage, including repeated correction rounds, color-coded by role, 
  with a dashed red target-date marker
- A row of "people chips" — avatar + name + role for everyone currently 
  involved
- A colored status banner at the bottom explaining exactly where the 
  request currently sits and whether it's delayed
- Two action buttons: "Send reminder" and "Full history"

---

## EXACT HTML TEMPLATE (Django)

Save as `templates/components/lifecycle_card.html` and include it in 
the request detail page sidebar with 
`{% include 'components/lifecycle_card.html' with request=design_request %}`

```html
{% load humanize %}
<div class="lc-wrap">
<div class="lc-card">

  <div class="lc-top">
    <div>
      <p class="lc-title">{{ request.design_number }} — {{ request.drawing_type.name|lower }}</p>
      <p class="lc-sub">{{ request.project.name }} · requested by {{ request.requested_by.get_full_name }}</p>
    </div>
    {% if lifecycle.is_overdue %}
      <span class="lc-badge lc-badge-danger">{{ lifecycle.days_over_target }} day(s) overdue</span>
    {% elif lifecycle.is_completed_on_time %}
      <span class="lc-badge lc-badge-success">Completed on time</span>
    {% elif request.completed_at %}
      <span class="lc-badge lc-badge-danger">Completed {{ lifecycle.days_late }}d late</span>
    {% else %}
      <span class="lc-badge lc-badge-neutral">On track</span>
    {% endif %}
  </div>

  <div class="lc-stats">
    <div class="lc-stat">
      <p class="lc-stat-label">Elapsed</p>
      <p class="lc-stat-val">{{ lifecycle.total_days }}d</p>
    </div>
    <div class="lc-stat">
      <p class="lc-stat-label">Allowed</p>
      <p class="lc-stat-val">{{ lifecycle.days_allowed }}d</p>
    </div>
    <div class="lc-stat">
      <p class="lc-stat-label">Corrections</p>
      <p class="lc-stat-val">{{ request.correction_count }}</p>
    </div>
    <div class="lc-stat">
      <p class="lc-stat-label">Current stage</p>
      <p class="lc-stat-val lc-stat-val-stage {% if lifecycle.is_overdue %}lc-text-danger{% endif %}">
        {{ lifecycle.current_stage_label|default:"Completed" }}
      </p>
    </div>
  </div>

  <div class="lc-legend">
    <span><span class="dot" style="background:#185FA5"></span>Head of design</span>
    <span><span class="dot" style="background:#1D9E75"></span>Designer</span>
    <span><span class="dot" style="background:#BA7517"></span>Verifier</span>
    <span><span class="dot" style="background:#993556"></span>Compliance</span>
    <span><span class="dot" style="background:#A32D2D"></span>Delay</span>
  </div>

  <div class="lc-scroll">
    <div class="lc-track-wrap">
      <div class="lc-track">
        {% for seg in lifecycle.segments %}
          <div class="seg seg-{{ seg.role }} {% if seg.is_ongoing %}seg-ongoing{% endif %} {% if seg.is_delay %}seg-delay{% endif %}"
               style="flex-grow: {{ seg.grow }};"
               title="{{ seg.label }}{% if seg.person %} — {{ seg.person }}{% endif %}">
            <span class="seg-title">{{ seg.label }}</span>
            <span class="seg-sub">{{ seg.days }}d{% if seg.note %}, {{ seg.note }}{% endif %}</span>
          </div>
        {% endfor %}
      </div>
      {% if lifecycle.target_marker_percent %}
        <div class="marker" style="left: {{ lifecycle.target_marker_percent }}%;"></div>
        <div class="marker-label" style="left: {{ lifecycle.target_marker_percent }}%;">
          Target · {{ request.target_date|date:"d M" }}
        </div>
      {% endif %}
    </div>
  </div>

  <div class="lc-people">
    {% for p in lifecycle.people %}
      <span class="person-chip">
        <span class="avatar" style="background:{{ p.bg }};color:{{ p.fg }};">{{ p.initials }}</span>
        {{ p.name }} · {{ p.role_label }}
      </span>
    {% endfor %}
  </div>

  <div class="lc-status {% if lifecycle.is_overdue %}lc-status-danger{% elif request.completed_at and lifecycle.is_completed_on_time %}lc-status-success{% else %}lc-status-neutral{% endif %}">
    <i class="ti {% if lifecycle.is_overdue %}ti-alert-triangle{% elif request.completed_at %}ti-check{% else %}ti-clock{% endif %}" aria-hidden="true"></i>
    <p>
      {% if lifecycle.is_overdue %}
        <strong>Delay source — {{ lifecycle.delay_stage_label }}</strong>
        <span>Waiting on {{ lifecycle.delay_person }} since {{ lifecycle.delay_since|date:"d M, h:i A" }} — {{ lifecycle.days_over_target }} day(s) past the {{ request.target_date|date:"d M Y" }} target.</span>
      {% elif request.completed_at and lifecycle.is_completed_on_time %}
        <strong>Completed on time</strong>
        <span>Finished within the {{ request.target_date|date:"d M Y" }} target window.</span>
      {% elif request.completed_at %}
        <strong>Completed {{ lifecycle.days_late }} day(s) late</strong>
        <span>Delay source: {{ lifecycle.delay_stage_label }}.</span>
      {% else %}
        <strong>Currently with {{ lifecycle.current_stage_label }}</strong>
        <span>{{ lifecycle.current_person }} — {{ lifecycle.current_elapsed_days }} day(s) so far. Target: {{ request.target_date|date:"d M Y" }}.</span>
      {% endif %}
    </p>
  </div>

  {% if not request.completed_at %}
  <div class="lc-actions">
    {% if lifecycle.is_overdue and lifecycle.delay_person_id %}
      <button onclick="sendReminderAction({{ request.id }}, '{{ lifecycle.delay_person_id }}')">
        <i class="ti ti-bell" aria-hidden="true"></i>Send reminder
      </button>
    {% endif %}
    <a href="#activity-log-section" class="lc-action-link">
      <button><i class="ti ti-history" aria-hidden="true"></i>Full history</button>
    </a>
  </div>
  {% endif %}

</div>
</div>
```

---

## EXACT CSS

Save as `static/css/lifecycle_card.css` and include in `base.html`, or 
add to the existing project stylesheet:

```css
.lc-wrap { font-family: inherit; }

.lc-card {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 20px 22px;
}

.lc-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}
.lc-title { font-size: 15px; font-weight: 600; color: #0F172A; margin: 0; }
.lc-sub { font-size: 12px; color: #64748B; margin: 2px 0 0; }

.lc-badge {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 8px;
  font-weight: 600;
  white-space: nowrap;
}
.lc-badge-danger  { background: #FEF2F2; color: #991B1B; }
.lc-badge-success { background: #F0FDF4; color: #166534; }
.lc-badge-neutral { background: #F1F5F9; color: #475569; }

.lc-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}
.lc-stat {
  background: #F8FAFC;
  border-radius: 8px;
  padding: 10px 12px;
}
.lc-stat-label { font-size: 11px; color: #64748B; margin: 0 0 4px; }
.lc-stat-val { font-size: 18px; font-weight: 600; color: #0F172A; margin: 0; }
.lc-stat-val-stage { font-size: 14px; }
.lc-text-danger { color: #DC2626; }

.lc-legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 10px;
  font-size: 11px;
  color: #64748B;
}
.lc-legend span { display: inline-flex; align-items: center; gap: 5px; }
.dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; flex-shrink: 0; }

.lc-scroll { overflow-x: auto; margin: 0 -4px; padding: 0 4px 4px; }
.lc-track-wrap { position: relative; min-width: max-content; padding-top: 18px; }
.lc-track { display: flex; height: 40px; border-radius: 8px; overflow: hidden; }

.seg {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 84px;
  padding: 0 12px;
  border-right: 2px solid #FFFFFF;
  position: relative;
}
.seg:last-child { border-right: none; }
.seg-title { font-size: 11px; font-weight: 600; white-space: nowrap; }
.seg-sub { font-size: 10px; white-space: nowrap; margin-top: 1px; opacity: 0.9; }

.seg-hod        { background: #B5D4F4; color: #042C53; }
.seg-designer   { background: #9FE1CB; color: #04342C; }
.seg-verifier   { background: #FAC775; color: #412402; }
.seg-compliance { background: #F4C0D1; color: #4B1528; }
.seg-endcap     { background: #1A3C6E; color: #FFFFFF; flex-grow: 0.6 !important; }

.seg-ongoing::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: repeating-linear-gradient(135deg, transparent, transparent 6px, rgba(255,255,255,0.3) 6px, rgba(255,255,255,0.3) 12px);
}
.seg-delay {
  background: #F09595 !important;
  color: #501313 !important;
}

.marker {
  position: absolute;
  top: -18px;
  bottom: 0;
  width: 0;
  border-left: 1.5px dashed #A32D2D;
}
.marker-label {
  position: absolute;
  top: -18px;
  transform: translateX(-50%);
  font-size: 10px;
  color: #791F1F;
  white-space: nowrap;
  font-weight: 600;
}

.lc-people { display: flex; gap: 6px; margin-top: 14px; flex-wrap: wrap; }
.person-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #F8FAFC;
  border-radius: 999px;
  padding: 3px 10px 3px 4px;
  font-size: 11px;
  color: #475569;
}
.avatar {
  width: 18px; height: 18px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 9px; font-weight: 600;
  flex-shrink: 0;
}

.lc-status {
  margin-top: 16px;
  padding: 11px 13px;
  border-radius: 8px;
  font-size: 12.5px;
  display: flex;
  gap: 9px;
  align-items: flex-start;
}
.lc-status i { font-size: 16px; margin-top: 1px; flex-shrink: 0; }
.lc-status strong { font-weight: 600; display: block; margin-bottom: 1px; font-size: 13px; }
.lc-status p { margin: 0; line-height: 1.45; }

.lc-status-danger  { background: #FEF2F2; border: 1px solid #F09595; color: #791F1F; }
.lc-status-danger i, .lc-status-danger strong { color: #791F1F; }
.lc-status-success { background: #F0FDF4; border: 1px solid #C0DD97; color: #166534; }
.lc-status-success i, .lc-status-success strong { color: #166534; }
.lc-status-neutral { background: #F8FAFC; border: 1px solid #E2E8F0; color: #475569; }
.lc-status-neutral i, .lc-status-neutral strong { color: #475569; }

.lc-actions { display: flex; gap: 8px; margin-top: 14px; }
.lc-actions button {
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid #E2E8F0;
  background: #FFFFFF;
  color: #334155;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.lc-actions button:hover { background: #F8FAFC; }
.lc-actions button i { font-size: 14px; }
.lc-action-link { text-decoration: none; }
```

---

## DJANGO VIEW LOGIC — Building the `lifecycle` Context Object

Add this to `requests/services.py` (or wherever workflow helper 
functions already live):

```python
from django.utils import timezone


def get_hod_name_and_id(design_request):
    """Returns (name, user_id) of the Head of Design relevant to this 
    request, using existing PermissionService lookups already in the 
    codebase."""
    hod_users = PermissionService.get_users_with_project_permission(
        design_request.project, 'PROJECT_PERM_ASSIGN'
    )
    hod = hod_users.first()
    if hod:
        return hod.get_full_name(), hod.id
    return 'Head of design', None


def get_initials(full_name):
    if not full_name:
        return '?'
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def build_lifecycle_data(design_request):
    """
    Builds the complete context object for the lifecycle card:
    segments, stats, current delay info, and people list.
    """
    now_time = timezone.now()
    target = design_request.target_date
    hod_name, hod_id = get_hod_name_and_id(design_request)

    segments = []
    people = {}

    def add_person(name, role_key, role_label, user_id=None):
        if not name or name in people:
            return
        palette = {
            'hod':        ('#B5D4F4', '#042C53'),
            'designer':   ('#9FE1CB', '#04342C'),
            'verifier':   ('#FAC775', '#412402'),
            'compliance': ('#F4C0D1', '#4B1528'),
        }
        bg, fg = palette.get(role_key, ('#F1F5F9', '#475569'))
        people[name] = {
            'name': name, 'initials': get_initials(name),
            'bg': bg, 'fg': fg, 'role_label': role_label, 'user_id': user_id,
        }

    def add_segment(label, role, person, start, end, note=None):
        if not start:
            return
        is_ongoing = end is None
        days = round(((end or now_time) - start).total_seconds() / 86400, 1)
        segments.append({
            'label': label, 'role': role, 'person': person,
            'days': days, 'grow': max(days, 0.3),
            'is_ongoing': is_ongoing, 'is_delay': False, 'note': note,
            'start': start, 'end': end,
        })

    add_segment('Ack', 'hod', hod_name, design_request.requested_at, design_request.acknowledged_at)
    add_segment('Assign', 'hod', hod_name, design_request.acknowledged_at, design_request.assigned_at)

    revisions = list(design_request.revisions.order_by('version_number'))
    prev_end = design_request.assigned_at
    for rev in revisions:
        designer_name = rev.submitted_by.get_full_name() if rev.submitted_by else None
        note = 'correction' if rev.version_number > 1 else None
        add_segment(f'Designer V{rev.version_number}', 'designer', designer_name, prev_end, rev.submitted_at, note=note)
        if designer_name:
            add_person(designer_name, 'designer', 'designer')
        review_end = getattr(rev, 'reviewed_at', None)
        add_segment('HOD', 'hod', hod_name, rev.submitted_at, review_end)
        prev_end = review_end

    if getattr(design_request, 'verification_acknowledged_at', None):
        verifier_name = design_request.verification_assigned_to.get_full_name() if design_request.verification_assigned_to else None
        add_segment('Verifier', 'verifier', verifier_name, design_request.verification_acknowledged_at, design_request.verification_approved_at)
        if verifier_name:
            add_person(verifier_name, 'verifier', 'verifier')
        add_segment('HOD', 'hod', hod_name, design_request.verification_approved_at, getattr(design_request, 'compliance_assigned_at', None))

    if getattr(design_request, 'compliance_acknowledged_at', None):
        compliance_name = design_request.compliance_assigned_to.get_full_name() if design_request.compliance_assigned_to else None
        add_segment('Compliance', 'compliance', compliance_name, design_request.compliance_acknowledged_at, design_request.compliance_approved_at)
        if compliance_name:
            add_person(compliance_name, 'compliance', 'compliance')
        add_segment('HOD', 'hod', hod_name, design_request.compliance_approved_at, design_request.approved_at)

    if design_request.completed_at:
        segments.append({
            'label': 'Completed', 'role': 'endcap', 'person': None,
            'days': None, 'grow': 0.6, 'is_ongoing': False, 'is_delay': False, 'note': None,
        })

    add_person(hod_name, 'hod', 'head of design', hod_id)

    is_overdue = bool(target and now_time > target and not design_request.completed_at)
    delay_stage_label = None
    delay_person = None
    delay_person_id = None
    delay_since = None
    current_stage_label = None
    current_person = None
    current_elapsed_days = None

    for seg in segments:
        if seg.get('is_ongoing'):
            current_stage_label = seg['label']
            current_person = seg['person']
            current_elapsed_days = seg['days']
            if is_overdue:
                seg['is_delay'] = True
                delay_stage_label = seg['label']
                delay_person = seg['person']
                delay_since = seg['start']
                person_obj = people.get(seg['person'])
                delay_person_id = person_obj['user_id'] if person_obj else None
            break

    total_days = round((((design_request.completed_at or now_time) - design_request.requested_at).total_seconds()) / 86400, 1) if design_request.requested_at else None
    days_allowed = round(((target - design_request.requested_at).total_seconds()) / 86400, 1) if target and design_request.requested_at else None
    days_over_target = round(((now_time if not design_request.completed_at else design_request.completed_at) - target).total_seconds() / 86400, 1) if is_overdue or (design_request.completed_at and target and design_request.completed_at > target) else None

    is_completed_on_time = bool(design_request.completed_at and target and design_request.completed_at <= target)
    days_late = days_over_target if (design_request.completed_at and not is_completed_on_time) else None

    total_grow = sum(s['grow'] for s in segments) or 1
    target_marker_percent = None
    if target and design_request.requested_at:
        elapsed_to_target = (target - design_request.requested_at).total_seconds() / 86400
        cumulative = 0
        running_days_total = sum(s['days'] or 0 for s in segments if s['role'] != 'endcap')
        if running_days_total > 0:
            target_marker_percent = min(100, max(0, round((elapsed_to_target / max(running_days_total, elapsed_to_target)) * 100, 1)))

    return {
        'segments': segments,
        'people': list(people.values()),
        'total_days': total_days,
        'days_allowed': days_allowed,
        'is_overdue': is_overdue,
        'is_completed_on_time': is_completed_on_time,
        'days_over_target': days_over_target,
        'days_late': days_late,
        'current_stage_label': current_stage_label,
        'current_person': current_person,
        'current_elapsed_days': current_elapsed_days,
        'delay_stage_label': delay_stage_label,
        'delay_person': delay_person,
        'delay_person_id': delay_person_id,
        'delay_since': delay_since,
        'target_marker_percent': target_marker_percent,
    }
```

In the view (`DesignRequestDetailView` or equivalent):

```python
context['lifecycle'] = build_lifecycle_data(design_request)
```

---

## "SEND REMINDER" BUTTON BEHAVIOR

Add a small JS function (in the same template or a shared JS file):

```html
<script>
function sendReminderAction(requestId, userId) {
  fetch(`/api/requests/${requestId}/send-reminder/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ target_user_id: userId }),
  }).then(res => {
    if (res.ok) {
      alert('Reminder sent.');
    } else {
      alert('Could not send reminder. Please try again.');
    }
  });
}
</script>
```

Add the corresponding view:
```python
def send_reminder(request, pk):
    design_request = get_object_or_404(DesignRequest, pk=pk)
    target_user_id = request.POST.get('target_user_id') or json.loads(request.body).get('target_user_id')
    target_user = get_object_or_404(User, pk=target_user_id)
    NotificationService.notify(
        recipient=target_user,
        notif_type='reminder',
        message=f"Reminder: {design_request.design_number} ({design_request.project.name}) is waiting on your action.",
        related_request=design_request,
    )
    return JsonResponse({'status': 'ok'})
```

Add URL: `path('api/requests/<int:pk>/send-reminder/', send_reminder, name='send_reminder')`

---

## "FULL HISTORY" BUTTON BEHAVIOR

This button simply scrolls down to the existing Activity Log section 
already on the page (do not build a new history view — reuse what's 
already there from the earlier Activity Card redesign). Make sure the 
Activity Log card on the page has `id="activity-log-section"` so the 
anchor link works:

```html
<div class="activity-log-card" id="activity-log-section">
  ...
</div>
```

---

## IMPORTANT DATA DEPENDENCY

This card depends on the `reviewed_at` field on `DesignRevision` (when 
HOD accepted/corrected that specific version) and on 
`verification_assigned_to`, `compliance_assigned_to`, 
`compliance_approved_at` fields on `DesignRequest`. Check the model 
first — these may already exist from earlier workflow fixes. Only add 
migrations for genuinely missing fields; do not duplicate existing 
fields under new names.

---

## TESTING CHECKLIST

- [ ] Old "Deadline Timer", "Time Breakdown", and any earlier timeline card variants are fully removed
- [ ] New card renders for a request still with Designer only (single segment, no verifier/compliance segments shown)
- [ ] Renders correctly with 2 designer correction rounds — shows "Designer V1" and "Designer V2" as separate green segments with HOD segments between them
- [ ] Renders correctly through full chain: Designer → Verifier → Compliance → Completed
- [ ] Red overdue badge + red status banner appear only when actually past target_date and not completed
- [ ] Green "Completed on time" badge appears for on-time completions
- [ ] Red "Completed Xd late" badge appears for late completions, banner uses past tense, no pulsing/ongoing styling
- [ ] Stat grid (Elapsed/Allowed/Corrections/Current Stage) shows correct real numbers
- [ ] People chips show correct names, roles, and colors matching the segments
- [ ] Target date dashed marker lines up at the correct proportional position on the bar
- [ ] "Send reminder" button only shows when overdue and a responsible person is identified; clicking it sends a real notification
- [ ] "Full history" button scrolls to the existing Activity Log card
- [ ] Bar scrolls horizontally without breaking card layout when there are many correction rounds
- [ ] Card looks correct on a freshly created request (not yet acknowledged) — shows just the "Ack" segment as ongoing
