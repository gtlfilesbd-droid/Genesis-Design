# Genesis Design — Replace Deadline Timer & Time Breakdown with a Visual Stage Timeline

⚠️ Do NOT touch workflow logic, permissions, or status transitions. This is a 
UI replacement task — remove two existing cards and replace them with one 
new visual component, using data that should already be correctly calculated 
from the earlier "Fix Fake Timer Data" pass. If that earlier fix was not 
fully completed, do it now as part of this task (see Data Requirements below).

---

## WHAT TO REMOVE

On the Request Detail page (`Home / Design Requests / Request Detail`), 
remove these two cards entirely from the sidebar:
1. "Deadline Timer" card
2. "Time Breakdown" card

---

## WHAT TO BUILD INSTEAD: "Drawing Completion Timeline" Card

A single visual card showing the entire journey of the request as a 
horizontal segmented bar — one segment per stage (Designer, Verifier, 
Compliance), sized proportionally to how many days each stage took/is 
taking, with the requester's target date marked as a vertical line, and 
a clear red warning message if the request is currently over target.

### Visual structure

```
┌──────────────────────────────────────────────────────────────────┐
│  Drawing completion — day 7 of 5 allowed                          │
│  2 days over target                                               │
│                                                                    │
│  [=== Designer ===][======= Verifier =======][== Compliance ==]   │
│                                              ┊ ← target date line  │
│                                                                    │
│  ● Designer — Rahim         2.0 days                              │
│  ● Verifier — Karim         3.0 days                               │
│  ● Compliance — Nadia       2.0 days — still pending, overdue     │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ ⚠ Delay source: Compliance review                         │    │
│  │   Waiting on Nadia since 20 Jun, 2 days past the          │    │
│  │   22 Jun target                                            │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### Color rules (apply consistently)
- **Designer segment:** green tones (`#9FE1CB` fill / `#1D9E75` dot — on-time, completed stage)
- **Verifier segment:** amber tones (`#FAC775` fill / `#BA7517` dot — completed but took longer, still acceptable)
- **Compliance segment (or whichever stage is CURRENT and causing delay):** red tones (`#F09595` fill / `#A32D2D` dot) — ONLY if this stage is the one currently overdue or responsible for the delay. If a stage completed on time, it should NOT be colored red even if it's the last one — red is reserved specifically for "this is where the delay is happening."
- **Target date marker:** dashed vertical red line (`#A32D2D`) cutting across the bar at the position corresponding to the requester's target date, with a small label above it.
- **Warning banner at the bottom:** light red background (`#FCEBEB`), red border (`#F09595`), red text (`#791F1F`) — only shown if the request IS currently past the target date. If the request is on track or already completed on time, do not show this banner at all — instead show a small green confirmation line like "Completed on time" or "On track, X days remaining."

### Segment sizing logic
Each stage's segment width is proportional to the number of days it took 
relative to the total bar width. A stage still in progress (not yet 
completed) should visually extend up to "today" and then show a subtle 
diagonal hatch pattern or lighter shade for the portion beyond today to 
indicate "still ongoing, exact end unknown yet."

---

## DATA REQUIREMENTS (build this if not already correctly available)

```python
def get_completion_timeline_data(design_request):
    """
    Builds the full stage-by-stage timeline for the visual bar.
    Returns None gracefully if not enough data exists yet (e.g. brand new request).
    """
    stages = []

    def days_between(start, end):
        if not start or not end:
            return None
        return round((end - start).total_seconds() / 86400, 1)

    now_time = timezone.now()
    target = design_request.target_date

    # Stage 1: Designer
    if design_request.assigned_at:
        design_end = design_request.submitted_at or now_time
        stages.append({
            'name': 'Designer',
            'person': design_request.assigned_to.get_full_name() if design_request.assigned_to else None,
            'start': design_request.assigned_at,
            'end': design_request.submitted_at,
            'days': days_between(design_request.assigned_at, design_end),
            'is_ongoing': design_request.submitted_at is None,
            'is_current_delay_source': False,
        })

    # Stage 2: Verifier (only if it happened/is happening)
    if design_request.verification_acknowledged_at:
        verify_end = design_request.verification_approved_at or now_time
        stages.append({
            'name': 'Verifier',
            'person': design_request.verification_assigned_to.get_full_name() if design_request.verification_assigned_to else None,
            'start': design_request.verification_acknowledged_at,
            'end': design_request.verification_approved_at,
            'days': days_between(design_request.verification_acknowledged_at, verify_end),
            'is_ongoing': design_request.verification_approved_at is None,
            'is_current_delay_source': False,
        })

    # Stage 3: Compliance (only if it happened/is happening)
    if design_request.compliance_acknowledged_at:
        compliance_end = design_request.compliance_approved_at or now_time
        stages.append({
            'name': 'Compliance',
            'person': design_request.compliance_assigned_to.get_full_name() if design_request.compliance_assigned_to else None,
            'start': design_request.compliance_acknowledged_at,
            'end': design_request.compliance_approved_at,
            'days': days_between(design_request.compliance_acknowledged_at, compliance_end),
            'is_ongoing': design_request.compliance_approved_at is None,
            'is_current_delay_source': False,
        })

    if not stages:
        return None  # nothing meaningful to show yet (request just created)

    # Determine total elapsed and whether overdue
    overall_end = design_request.completed_at or now_time
    total_days = days_between(design_request.requested_at, overall_end)
    is_overdue = target and overall_end > target and not design_request.completed_at
    is_completed_on_time = design_request.completed_at and target and design_request.completed_at <= target

    days_over = None
    if is_overdue and target:
        days_over = days_between(target, overall_end)

    # Mark the CURRENTLY ONGOING stage as the delay source, only if overdue
    if is_overdue:
        for stage in stages:
            if stage['is_ongoing']:
                stage['is_current_delay_source'] = True

    # Days allowed = total time from request to target
    days_allowed = days_between(design_request.requested_at, target) if target else None

    return {
        'stages': stages,
        'total_days': total_days,
        'days_allowed': days_allowed,
        'target_date': target,
        'is_overdue': is_overdue,
        'is_completed_on_time': is_completed_on_time,
        'days_over': days_over,
        'days_remaining': days_between(now_time, target) if target and not is_overdue and not design_request.completed_at else None,
    }
```

If any of these model fields don't exist yet (`verification_assigned_to`, 
`compliance_assigned_to`, `compliance_approved_at`, etc.), check the model 
first — they should already exist from the earlier workflow fixes. Only 
add migrations if genuinely missing; do not duplicate fields that exist 
under slightly different names (search the model file carefully first).

---

## TEMPLATE / RENDERING APPROACH

Build this as an HTML/CSS card (not a canvas chart) so it stays sharp and 
matches the design system. Structure:

```html
<div class="timeline-card">
  <div class="timeline-header">
    <h4>
      {% if data.is_completed_on_time %}
        Drawing completed on time
      {% elif data.is_overdue %}
        Drawing completion — day {{ data.total_days }} of {{ data.days_allowed }} allowed
      {% else %}
        Drawing in progress — day {{ data.total_days }} of {{ data.days_allowed }} allowed
      {% endif %}
    </h4>
    {% if data.is_overdue %}
      <p class="timeline-overdue-text">{{ data.days_over }} day(s) over target</p>
    {% elif data.is_completed_on_time %}
      <p class="timeline-ontime-text">Finished within the target window</p>
    {% elif data.days_remaining %}
      <p class="timeline-ontrack-text">{{ data.days_remaining }} day(s) remaining</p>
    {% endif %}
  </div>

  <div class="timeline-bar">
    {% for stage in data.stages %}
      <div class="timeline-segment
                  {% if stage.is_current_delay_source %}segment-delay
                  {% elif stage.is_ongoing %}segment-ongoing
                  {% else %}segment-done{% endif %}"
           style="flex-grow: {{ stage.days|default:1 }};">
      </div>
    {% endfor %}
    {% if data.target_date %}
      <div class="target-marker" style="left: {{ target_marker_position_percent }}%;">
        <span>Target</span>
      </div>
    {% endif %}
  </div>

  <div class="timeline-legend">
    {% for stage in data.stages %}
      <div class="legend-row {% if stage.is_current_delay_source %}legend-delay{% endif %}">
        <span class="dot"></span>
        <span class="stage-name">{{ stage.name }}{% if stage.person %} — {{ stage.person }}{% endif %}</span>
        <span class="stage-days">
          {{ stage.days }} day(s)
          {% if stage.is_ongoing and stage.is_current_delay_source %} — still pending, overdue{% endif %}
          {% if stage.is_ongoing and not stage.is_current_delay_source %} — in progress{% endif %}
        </span>
      </div>
    {% endfor %}
  </div>

  {% if data.is_overdue %}
    <div class="timeline-warning-banner">
      <strong>Delay source: {{ delay_stage_name }} review</strong>
      <p>Waiting on {{ delay_person_name }} since {{ delay_start_date|date:"d M" }}, 
         {{ data.days_over }} day(s) past the {{ data.target_date|date:"d M" }} target</p>
    </div>
  {% endif %}
</div>
```

Calculate `target_marker_position_percent` in the view (percentage 
position of the target date along the total bar width, based on 
proportion of elapsed time vs total time from request creation to now/
completion). Pass it as a ready-to-use number — don't do this math in 
the template.

### CSS guidance (match existing design system tokens — colors, radius, 
spacing already defined in the project's base CSS):
```css
.timeline-bar {
  display: flex;
  height: 34px;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
  border: 1px solid #E2E8F0;
}
.segment-done { background: #9FE1CB; }
.segment-ongoing { background: #FAC775; }
.segment-delay {
  background: repeating-linear-gradient(45deg, #F09595, #F09595 6px, #F7C1C1 6px, #F7C1C1 12px);
}
.target-marker {
  position: absolute;
  top: -18px;
  bottom: -6px;
  border-left: 2px dashed #A32D2D;
}
.target-marker span {
  font-size: 11px;
  color: #791F1F;
  white-space: nowrap;
  position: absolute;
  top: -18px;
  transform: translateX(-50%);
}
.legend-delay .stage-days { color: #791F1F; font-weight: 600; }
.timeline-warning-banner {
  background: #FCEBEB;
  border: 1px solid #F09595;
  border-radius: 8px;
  padding: 12px 14px;
  margin-top: 12px;
  color: #791F1F;
}
```

---

## EDGE CASES TO HANDLE GRACEFULLY

1. **Brand new request** (not yet assigned) → don't show this card at all, 
   or show a simple "Workflow not started yet" placeholder.
2. **Completed on time** → show the green confirmation message, no red 
   anywhere, no warning banner.
3. **Completed but was late** → show all final segment colors normally 
   (green/amber for stages that were done within reason), but mark 
   whichever stage caused the actual lateness in red — even though it's 
   finished now, the historical record should still show where the 
   delay happened. Banner text changes to past tense: "This drawing was 
   completed 2 days late. Delay source: Compliance review."
4. **Currently in Designer stage only** (no verification/compliance yet) 
   → bar shows just one segment, sized to fill proportionally, with 
   target marker positioned correctly relative to that single stage.
5. **HOD skipped verification/compliance entirely** → bar shows only 
   "Designer" stage leading straight to a "Completed" end-cap — don't 
   show empty/zero segments for stages that were never used.

---

## TESTING CHECKLIST

- [ ] Old "Deadline Timer" and "Time Breakdown" cards are completely removed from the template
- [ ] New "Drawing Completion Timeline" card renders correctly for a request still in Designer stage
- [ ] Renders correctly for a request that has passed Designer and is in Verifier stage
- [ ] Renders correctly for a request that has gone through Designer → Verifier → Compliance
- [ ] Red segment + warning banner appears ONLY when actually overdue against requester's target_date
- [ ] Green "on time" message appears for a completed request that finished before target
- [ ] Target date marker position on the bar visually lines up with the correct proportional point
- [ ] No segment shows for a stage that was skipped (e.g. HOD completed directly without verification)
- [ ] Card looks correct in both a request with corrections/revisions and one with a clean single pass
