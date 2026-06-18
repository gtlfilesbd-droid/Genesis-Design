# Genesis Design — Fix Fake Data in Deadline Timer & Time Breakdown Cards

⚠️ Do NOT touch workflow logic, permissions, or status transitions. 
This is purely a data-binding bug fix — the cards are showing 
hardcoded/placeholder values instead of real calculated data from 
the database.

---

## LOCATION
Request Detail page → right sidebar → two cards:
1. **Deadline Timer** card
2. **Time Breakdown** card

---

## BUG

Both cards currently show static/incorrect placeholder data regardless 
of the actual request:
- "Deadline Timer" always shows "0% elapsed" no matter how much time 
  has actually passed
- "Time Breakdown" always shows "Delay: acknowledged (0.00 days)" — 
  this text doesn't even make sense as a delay source, and the value 
  is always 0.00 regardless of actual elapsed time

This means the view is either passing hardcoded context values, or the 
calculation function exists but is broken/not being called/not using 
real model timestamps.

---

## FIX PART 1: Deadline Timer Card

This card should show REAL progress toward the relevant due date for 
whoever currently holds the request (Designer's due date, Verifier's 
due date, or Compliance's due date — whichever stage is currently active).

**Logic to implement/fix:**

```python
def get_deadline_timer_data(design_request):
    """
    Returns deadline progress based on the CURRENT active stage.
    """
    status = design_request.status

    if status in ['assigned', 'in_progress']:
        start = design_request.assigned_at
        due = design_request.due_date
    elif status == 'verification_pending':
        start = design_request.verification_acknowledged_at
        due = design_request.verification_due_date
    elif status == 'compliance_pending':
        start = design_request.compliance_acknowledged_at
        due = design_request.compliance_due_date
    else:
        # No active countdown for stages like 'new', 'completed', 'cancelled'
        return None

    if not start or not due:
        return None  # don't show fake data if real timestamps aren't set yet

    now_time = timezone.now()
    total_duration = (due - start).total_seconds()
    elapsed_duration = (now_time - start).total_seconds()

    if total_duration <= 0:
        percent_elapsed = 100
    else:
        percent_elapsed = min(100, max(0, (elapsed_duration / total_duration) * 100))

    is_overdue = now_time > due

    return {
        'percent_elapsed': round(percent_elapsed, 1),
        'due_date': due,
        'is_overdue': is_overdue,
        'days_remaining': (due - now_time).days if not is_overdue else 0,
        'days_overdue': (now_time - due).days if is_overdue else 0,
    }
```

**Fix the view** to call this function and pass real data:
```python
context['deadline_timer'] = get_deadline_timer_data(design_request)
```

**Fix the template** to use these real values instead of hardcoded text:
```django
{% if deadline_timer %}
  <div class="deadline-timer-card">
    <div class="progress-bar" style="width: {{ deadline_timer.percent_elapsed }}%"></div>
    <p>{{ deadline_timer.percent_elapsed }}% elapsed</p>
    <p>Due: {{ deadline_timer.due_date|date:"d M Y, h:i A" }}</p>
    {% if deadline_timer.is_overdue %}
      <p class="text-red-600">⚠ Overdue by {{ deadline_timer.days_overdue }} day(s)</p>
    {% else %}
      <p class="text-slate-500">{{ deadline_timer.days_remaining }} day(s) remaining</p>
    {% endif %}
  </div>
{% else %}
  <p class="text-slate-400 text-sm">No active deadline for the current stage</p>
{% endif %}
```

**Color the progress bar based on percent_elapsed:**
- 0–50% → green
- 50–80% → amber/yellow
- 80–100% or overdue → red

---

## FIX PART 2: Time Breakdown Card

This card should show the REAL time spent at each stage of the 
workflow, calculated from actual timestamps stored on the model — not 
a single fake "delay: acknowledged" line.

**Logic to implement/fix:**

```python
def get_time_breakdown_data(design_request):
    """
    Returns a breakdown of how long the request spent in each stage,
    using real timestamps. Only includes stages that have actually 
    happened (don't show future/skipped stages).
    """
    breakdown = []

    def days_between(start, end):
        if not start or not end:
            return None
        return round((end - start).total_seconds() / 86400, 2)

    # Request → Acknowledged
    if design_request.requested_at and design_request.acknowledged_at:
        breakdown.append({
            'label': 'Request to Acknowledgement',
            'days': days_between(design_request.requested_at, design_request.acknowledged_at)
        })

    # Acknowledged → Assigned
    if design_request.acknowledged_at and design_request.assigned_at:
        breakdown.append({
            'label': 'Acknowledgement to Assignment',
            'days': days_between(design_request.acknowledged_at, design_request.assigned_at)
        })

    # Assigned → Submitted (design time)
    if design_request.assigned_at and design_request.submitted_at:
        breakdown.append({
            'label': 'Design Work Time',
            'days': days_between(design_request.assigned_at, design_request.submitted_at)
        })

    # Submitted → Accepted by HOD (review time)
    if design_request.submitted_at and design_request.design_accepted_at:
        breakdown.append({
            'label': 'Review Time (Head of Design)',
            'days': days_between(design_request.submitted_at, design_request.design_accepted_at)
        })

    # Sent to verification → Verifier acknowledged
    if design_request.verification_assigned_at and design_request.verification_acknowledged_at:
        breakdown.append({
            'label': 'Wait Time Before Verifier Acknowledged',
            'days': days_between(design_request.verification_assigned_at, design_request.verification_acknowledged_at)
        })

    # Verifier acknowledged → Verification approved
    if design_request.verification_acknowledged_at and design_request.verification_approved_at:
        breakdown.append({
            'label': 'Verification Time',
            'days': days_between(design_request.verification_acknowledged_at, design_request.verification_approved_at)
        })

    # Sent to compliance → Compliance acknowledged
    if design_request.compliance_assigned_at and design_request.compliance_acknowledged_at:
        breakdown.append({
            'label': 'Wait Time Before Compliance Acknowledged',
            'days': days_between(design_request.compliance_assigned_at, design_request.compliance_acknowledged_at)
        })

    # Compliance acknowledged → Compliance approved
    if design_request.compliance_acknowledged_at and design_request.compliance_approved_at:
        breakdown.append({
            'label': 'Compliance Review Time',
            'days': days_between(design_request.compliance_acknowledged_at, design_request.compliance_approved_at)
        })

    # Total elapsed so far (request created → now, or → completed)
    end_point = design_request.completed_at or timezone.now()
    total_days = days_between(design_request.requested_at, end_point)

    # Identify the single biggest contributor to delay
    slowest_stage = None
    if breakdown:
        valid_stages = [b for b in breakdown if b['days'] is not None]
        if valid_stages:
            slowest_stage = max(valid_stages, key=lambda x: x['days'])

    return {
        'stages': breakdown,
        'total_days': total_days,
        'slowest_stage': slowest_stage,  # e.g. {'label': 'Design Work Time', 'days': 4.2}
    }
```

**Fix the view:**
```python
context['time_breakdown'] = get_time_breakdown_data(design_request)
```

**Fix the template:**
```django
<div class="time-breakdown-card">
  <h4>Time Breakdown</h4>
  {% for stage in time_breakdown.stages %}
    <div class="breakdown-row">
      <span>{{ stage.label }}</span>
      <span>{{ stage.days }} day(s)</span>
    </div>
  {% endfor %}
  <div class="breakdown-row total">
    <span>Total Elapsed</span>
    <span>{{ time_breakdown.total_days }} day(s)</span>
  </div>
  {% if time_breakdown.slowest_stage %}
    <p class="text-amber-600 text-sm">
      Biggest delay source: {{ time_breakdown.slowest_stage.label }} 
      ({{ time_breakdown.slowest_stage.days }} days)
    </p>
  {% endif %}
</div>
```

---

## IMPORTANT — DATA SOURCE INTEGRITY

1. Before writing this logic, confirm these fields actually exist and 
   are being correctly set (saved with real timestamps, not left null) 
   at every workflow step in the model:
   `requested_at`, `acknowledged_at`, `assigned_at`, `submitted_at`, 
   `design_accepted_at`, `verification_assigned_at`, 
   `verification_acknowledged_at`, `verification_approved_at`, 
   `compliance_assigned_at`, `compliance_acknowledged_at`, 
   `compliance_approved_at`, `completed_at`

2. If any of these fields are missing from the model, add them as 
   nullable `DateTimeField`s and create a migration. Then make sure 
   each corresponding workflow action view sets the field with 
   `timezone.now()` at the moment that action happens (most of these 
   may already be set from the earlier workflow fixes — just confirm 
   nothing is missing).

3. Test with a real request that has gone through several stages 
   (assigned → submitted → corrected → resubmitted → verified) and 
   manually verify the displayed days/percentages match the actual 
   dates in the database — not just that something renders.

4. For a brand-new request that hasn't reached verification/compliance 
   yet, the Time Breakdown card should simply NOT show those rows 
   (don't show "Verification Time: 0.00 days" if verification hasn't 
   happened — only show stages that have actually occurred).

---

## TESTING CHECKLIST

- [ ] Deadline Timer shows correct % based on real assigned_at/due_date difference
- [ ] Deadline Timer updates correctly depending on which stage is currently active (designer/verifier/compliance)
- [ ] Deadline Timer shows "No active deadline" gracefully for new/completed/cancelled requests instead of fake 0%
- [ ] Time Breakdown shows only stages that have actually happened — no zero-value rows for future stages
- [ ] Time Breakdown's day calculations match manual date-subtraction from the database
- [ ] "Biggest delay source" correctly identifies the stage with the highest day count
- [ ] Both cards tested on at least 3 different requests: one brand new, one mid-workflow, one fully completed
