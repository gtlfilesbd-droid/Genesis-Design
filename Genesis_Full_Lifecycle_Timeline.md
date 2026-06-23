# Genesis Design — Full Lifecycle Visual Timeline (Complete Redesign)

⚠️ Do NOT touch workflow logic, permissions, or status transitions. This is 
a visual/UI redesign of the timeline card only. The underlying workflow 
(request → acknowledge → assign → submit → review → verify → compliance → 
approve → complete, including correction loops) is working correctly and 
must not change. You are only changing how this is DISPLAYED.

This replaces the previous "Drawing Completion Timeline" attempt — that 
version only showed Designer/Verifier/Compliance and looked basic. This 
spec is more complete and must include **Head of Design** as a visible 
stage too, plus correctly branching bars when corrections happen.

---

## CORE REQUIREMENT

This timeline must show **every stage of the design's life**, starting 
the MOMENT the requester submits the request — not starting later when 
someone acts on it. Every stage must be visible from day one, even 
stages that haven't started yet. The stages are:

```
Requester → Head of Design (Acknowledge + Assign + Review) → Designer → 
Head of Design (Review again) → Verifier → Head of Design → 
Compliance → Head of Design → Completed
```

Head of Design appears MULTIPLE times in this chain because HOD 
acknowledges the request first, assigns the designer, then reviews 
designer's submitted work, then forwards to verifier, reviews verifier's 
result, forwards to compliance, reviews compliance's result, and finally 
marks complete. Every one of these HOD touchpoints should appear as its 
own segment in the timeline — not collapsed into one "HOD" block.

---

## HOW THE BAR BEHAVES — STEP BY STEP

### Step 1: Request Created
The instant the requester submits the request, the timeline immediately 
shows the FULL planned sequence of stages as empty/pending placeholders, 
with the first one ("Awaiting HOD Acknowledgement") already active and 
counting elapsed time.

```
[● Awaiting Acknowledgement] [○ Assign] [○ Designer] [○ HOD Review] [○ Verifier] [○ HOD] [○ Compliance] [○ HOD] [○ Complete]
   counting... 0.4 days                                                                              target: 22 Jun
```

- Filled/colored segment = active or completed stage
- Empty/outlined segment = stage not yet reached
- The requester's **target date** is shown as a marker positioned along 
  the whole bar from the start, so you can see immediately whether the 
  current pace is on track.

### Step 2: HOD Has Not Acknowledged Yet (Time Passing)
If HOD has not acknowledged within a reasonable time, this exact 
situation must be visible directly in the timeline's delay indicator 
area — even before any designer/verifier stage exists yet:

```
[●●●●● Awaiting Acknowledgement — 2.1 days] [○ Assign] [○ Designer] ...

⚠ Delay source: Head of Design has not acknowledged yet
   Waiting since 16 Jun, 10:30 AM
```

This is critical — the delay indicator must work at EVERY stage of the 
chain, not just at Designer/Verifier/Compliance. If nobody has acted yet, 
the system must say so clearly, pointing at HOD.

### Step 3: HOD Acknowledges → Assigns Designer
```
[✓ Acknowledged — 0.3d] [✓ Assigned — 0.1d] [● Designer working — 1.2d] [○ HOD Review] ...
```

### Step 4: Designer Submits → HOD Reviews
```
[✓ Designer — 2.0d] [● HOD reviewing — 0.5d] [○ Verifier] [○ HOD] [○ Compliance] [○ HOD] [○ Complete]
```

### Step 5: CORRECTION HAPPENS (Critical Behavior — Branching Bar)

This is the most important behavior to get right. When HOD sends the 
design back to the Designer for correction, do NOT just extend the 
existing Designer segment. Instead, **add a NEW segment right after the 
HOD review segment, in the Designer's color**, representing this new 
correction round. The timeline grows horizontally to the right, stacking 
each correction round as its own visible block, in sequence, so you can 
see the full back-and-forth history at a glance:

```
[✓ Designer V1 — 2.0d] [✓ HOD Review — 0.5d] [✓ Designer V2 (correction) — 1.5d] [✓ HOD Review — 0.3d] [● Verifier — 0.8d] ...
```

Same logic applies if **Verifier** sends a correction back to HOD (which 
then may go back to Designer again, or HOD may resolve directly):

```
... [✓ Verifier — 1.0d] [✓ HOD — 0.2d] [✓ Designer V3 (correction) — 1.0d] [✓ HOD — 0.2d] [● Verifier (re-check) — 0.5d] ...
```

And the same for **Compliance** sending a correction back:

```
... [✓ Compliance — 0.7d] [✓ HOD — 0.2d] [✓ Designer V4 (correction) — 0.9d] [✓ HOD — 0.2d] [✓ Verifier (re-check)] [✓ HOD] [● Compliance (re-check)] ...
```

**Rules for correction segments:**
- Each correction round gets its OWN segment block, added to the right 
  end of the bar, in chronological order — never overwrite or merge with 
  a previous segment for the same role.
- Label each correction segment with its version number, e.g. 
  "Designer V2", "Designer V3" (matching the existing `DesignRevision` 
  version numbering already in the database — do not invent a separate 
  counter, reuse the real revision count).
- Color stays consistent per ROLE regardless of how many times it 
  repeats: Designer segments are always the Designer's color, HOD 
  segments always HOD's color, Verifier always Verifier's color, 
  Compliance always Compliance's color. The shade/intensity can vary 
  slightly between repeats only if needed for visual distinction, but 
  the base hue must stay tied to the role.
- The bar will grow longer (more segments) for designs with more 
  corrections — that's expected and correct. Allow horizontal scroll on 
  the bar container if it exceeds the card width, so long correction 
  chains don't break the layout.

### Step 6: Final Approval & Completion
```
[✓ ... full history ...] [✓ Final Approval — 0.1d] [✓ Completed]
```
Bar ends with a distinct "Completed" end-cap segment, in the primary 
navy/HOD-complete color, clearly marking the end of the journey.

---

## COLOR SYSTEM (per role, consistent across all repeats)

```
Awaiting Acknowledgement / HOD touchpoints  → Navy/Blue   (#85B7EB fill / #185FA5 dot)
Designer (any version)                      → Green       (#9FE1CB fill / #1D9E75 dot)
Verifier (any round)                        → Amber       (#FAC775 fill / #BA7517 dot)
Compliance (any round)                      → Pink/Purple (#F4C0D1 fill / #993556 dot)
Currently active stage                      → same role color, but with a pulsing/breathing animation or brighter border to show "in progress"
Stage causing current delay                 → Red overlay (#F09595 fill / #A32D2D border) — REPLACES whatever role color would normally show, because red always means "this is where the holdup is right now"
Stage not yet reached                       → Light gray outline only, no fill (#F1EFE8 background, dashed border)
```

**Legend** must be shown once at the top of the card (small color key): 
"● Head of Design  ● Designer  ● Verifier  ● Compliance  ● Delay"

---

## DELAY INDICATOR LOGIC (must work at every single stage)

At any point in time, exactly ONE thing is true: either the request is 
moving normally, or it's stuck somewhere. The delay banner at the bottom 
of the card must always correctly identify WHICH stage currently holds 
it and for how long, by checking stages in this priority order:

```python
def get_current_delay_info(design_request):
    """
    Walks through the full stage chain in order and finds where the 
    request currently sits. Returns info about whether that stage is 
    overdue relative to the requester's target date.
    """
    now_time = timezone.now()
    target = design_request.target_date

    # Define the full ordered chain of timestamps to check
    # Each tuple: (stage_label, person_getter, started_at_field, ended_at_field)
    chain = [
        ('Head of Design — Acknowledgement', lambda r: get_hod_name(r), 'requested_at', 'acknowledged_at'),
        ('Head of Design — Assignment', lambda r: get_hod_name(r), 'acknowledged_at', 'assigned_at'),
        ('Designer', lambda r: r.assigned_to.get_full_name() if r.assigned_to else None, 'assigned_at', 'submitted_at'),
        ('Head of Design — Review', lambda r: get_hod_name(r), 'submitted_at', 'design_accepted_at'),
        ('Verifier', lambda r: r.verification_assigned_to.get_full_name() if r.verification_assigned_to else None, 'verification_acknowledged_at', 'verification_approved_at'),
        ('Head of Design — Post-Verification', lambda r: get_hod_name(r), 'verification_approved_at', 'compliance_assigned_at'),
        ('Compliance', lambda r: r.compliance_assigned_to.get_full_name() if r.compliance_assigned_to else None, 'compliance_acknowledged_at', 'compliance_approved_at'),
        ('Head of Design — Final Approval', lambda r: get_hod_name(r), 'compliance_approved_at', 'approved_at'),
    ]

    # Find the first stage in the chain that has STARTED but not ENDED — 
    # that is the current location of the request.
    for label, person_fn, start_field, end_field in chain:
        start_val = getattr(design_request, start_field, None)
        end_val = getattr(design_request, end_field, None)
        if start_val and not end_val:
            elapsed_days = round((now_time - start_val).total_seconds() / 86400, 1)
            is_overdue = target and now_time > target and not design_request.completed_at
            return {
                'current_stage_label': label,
                'current_person': person_fn(design_request),
                'waiting_since': start_val,
                'elapsed_days': elapsed_days,
                'is_overdue': is_overdue,
                'days_over_target': round((now_time - target).total_seconds() / 86400, 1) if is_overdue else None,
            }

    # If nothing is "started but not ended", check if request hasn't 
    # even been acknowledged yet (very first state)
    if not design_request.acknowledged_at:
        elapsed_days = round((now_time - design_request.requested_at).total_seconds() / 86400, 1)
        is_overdue = target and now_time > target
        return {
            'current_stage_label': 'Head of Design — Acknowledgement',
            'current_person': get_hod_name(design_request),
            'waiting_since': design_request.requested_at,
            'elapsed_days': elapsed_days,
            'is_overdue': is_overdue,
            'days_over_target': round((now_time - target).total_seconds() / 86400, 1) if is_overdue else None,
        }

    return None  # request is fully completed, nothing currently pending


def get_hod_name(design_request):
    """Returns the name of whoever has Head of Design permission on this 
    project — if multiple, show the one who took the most recent action, 
    falling back to the first HOD found on the project."""
    # Reuse existing PermissionService logic already in the codebase to 
    # find users with PROJECT_PERM_ASSIGN/PROJECT_PERM_APPROVE on this project
    ...
```

**Display rule:**
- If `current_delay_info.is_overdue` is `True` → show RED banner: 
  `"⚠ Delay source: {current_stage_label}. Waiting on {current_person} 
  since {waiting_since}, {days_over_target} day(s) past the 
  {target_date} target."`
- If not overdue but something is actively in progress → show a NEUTRAL 
  gray/blue info line (not red, not alarming): 
  `"Currently with: {current_stage_label} ({current_person}) — 
  {elapsed_days} day(s) so far. Target: {target_date}."`
- If fully completed on time → green confirmation: 
  `"Completed on time."`
- If fully completed but was late → red historical note (past tense, no 
  pulsing/urgency styling since it's done): 
  `"Completed {days_late} day(s) past target. Delay source: 
  {stage_that_caused_it}."`

---

## BUILDING THE FULL SEGMENT LIST (for rendering the bar itself)

```python
def build_timeline_segments(design_request):
    """
    Builds the ordered list of ALL segments to render in the bar,
    including repeated correction rounds, using real DesignRevision 
    records already stored in the database.
    """
    segments = []
    now_time = timezone.now()

    def add_segment(label, person, start, end, role_color_key, version_label=None):
        if not start:
            return  # stage hasn't started, don't add it as a real segment
        is_ongoing = end is None
        days = round(((end or now_time) - start).total_seconds() / 86400, 1)
        segments.append({
            'label': version_label or label,
            'role': role_color_key,
            'person': person,
            'days': days,
            'is_ongoing': is_ongoing,
            'is_done': not is_ongoing,
        })

    hod_name = get_hod_name(design_request)

    # 1. Acknowledgement
    add_segment('Awaiting Acknowledgement', hod_name, design_request.requested_at, design_request.acknowledged_at, 'hod')

    # 2. Assignment
    add_segment('Assigning Designer', hod_name, design_request.acknowledged_at, design_request.assigned_at, 'hod')

    # 3+. Walk through ALL DesignRevision records in order — this 
    # naturally captures every correction round as its own entry, 
    # since each resubmission creates a new DesignRevision row already
    revisions = design_request.revisions.order_by('version_number')
    prev_end = design_request.assigned_at

    for revision in revisions:
        designer_name = revision.submitted_by.get_full_name() if revision.submitted_by else None
        add_segment(
            f'Designer V{revision.version_number}',
            designer_name,
            prev_end,
            revision.submitted_at,
            'designer',
            version_label=f'Designer V{revision.version_number}'
        )
        # After each submission, HOD reviews it
        review_end = revision.reviewed_at  # whenever HOD accepted or sent correction
        add_segment(
            f'HOD Review (V{revision.version_number})',
            hod_name,
            revision.submitted_at,
            review_end,
            'hod'
        )
        prev_end = review_end

    # 4. Verification (and re-checks if sent back from compliance, or 
    # correction loops — walk through verification attempts similarly 
    # if multiple verification rounds are stored, otherwise single block)
    if design_request.verification_acknowledged_at:
        add_segment(
            'Verifier',
            design_request.verification_assigned_to.get_full_name() if design_request.verification_assigned_to else None,
            design_request.verification_acknowledged_at,
            design_request.verification_approved_at,
            'verifier'
        )
        add_segment(
            'HOD (post-verification)',
            hod_name,
            design_request.verification_approved_at,
            design_request.compliance_assigned_at,
            'hod'
        )

    # 5. Compliance
    if design_request.compliance_acknowledged_at:
        add_segment(
            'Compliance',
            design_request.compliance_assigned_to.get_full_name() if design_request.compliance_assigned_to else None,
            design_request.compliance_acknowledged_at,
            design_request.compliance_approved_at,
            'compliance'
        )
        add_segment(
            'HOD (final approval)',
            hod_name,
            design_request.compliance_approved_at,
            design_request.approved_at,
            'hod'
        )

    # 6. Completed end-cap
    if design_request.completed_at:
        segments.append({
            'label': 'Completed',
            'role': 'complete',
            'person': None,
            'days': None,
            'is_ongoing': False,
            'is_done': True,
            'is_endcap': True,
        })

    return segments
```

**Important:** If the codebase does NOT already store a `reviewed_at` 
timestamp per `DesignRevision` (when HOD accepted/corrected that specific 
version), add this field now — it's needed to correctly split "Designer 
working" time from "HOD reviewing" time per correction round. Check the 
model first; if something equivalent already exists under a different 
name, reuse it instead of duplicating.

---

## RENDERING — HTML STRUCTURE

```html
<div class="lifecycle-timeline-card">
  <div class="timeline-legend-row">
    <span class="legend-item"><span class="dot dot-hod"></span> Head of Design</span>
    <span class="legend-item"><span class="dot dot-designer"></span> Designer</span>
    <span class="legend-item"><span class="dot dot-verifier"></span> Verifier</span>
    <span class="legend-item"><span class="dot dot-compliance"></span> Compliance</span>
    <span class="legend-item"><span class="dot dot-delay"></span> Delay</span>
  </div>

  <div class="timeline-scroll-wrapper">
    <div class="timeline-bar-v2">
      {% for seg in segments %}
        <div class="seg seg-{{ seg.role }}
                    {% if seg.is_ongoing %}seg-ongoing{% endif %}
                    {% if seg.is_current_delay_source %}seg-delay{% endif %}
                    {% if seg.is_endcap %}seg-endcap{% endif %}"
             style="flex-grow: {{ seg.days|default:1 }};"
             title="{{ seg.label }}{% if seg.person %} — {{ seg.person }}{% endif %}{% if seg.days %} — {{ seg.days }} days{% endif %}">
          <span class="seg-label">{{ seg.label }}</span>
        </div>
      {% endfor %}
    </div>
    {% if target_marker_percent %}
      <div class="target-marker-v2" style="left: {{ target_marker_percent }}%;">
        <span>Target: {{ design_request.target_date|date:"d M" }}</span>
      </div>
    {% endif %}
  </div>

  <div class="timeline-status-line {% if delay_info.is_overdue %}status-overdue{% elif design_request.completed_at %}status-complete{% else %}status-active{% endif %}">
    {% if delay_info %}
      {% if delay_info.is_overdue %}
        <strong>⚠ Delay source: {{ delay_info.current_stage_label }}</strong>
        <p>Waiting on {{ delay_info.current_person }} since {{ delay_info.waiting_since|date:"d M, h:i A" }}, 
           {{ delay_info.days_over_target }} day(s) past the {{ design_request.target_date|date:"d M Y" }} target.</p>
      {% else %}
        <p>Currently with: {{ delay_info.current_stage_label }} ({{ delay_info.current_person }}) — 
           {{ delay_info.elapsed_days }} day(s) so far. Target: {{ design_request.target_date|date:"d M Y" }}.</p>
      {% endif %}
    {% elif design_request.completed_at %}
      {% if is_completed_on_time %}
        <p class="status-good">✓ Completed on time.</p>
      {% else %}
        <p class="status-bad">Completed {{ days_late }} day(s) past target. 
           Delay source: {{ historical_delay_stage }}.</p>
      {% endif %}
    {% endif %}
  </div>
</div>
```

### CSS (extend existing design tokens — match project's existing border-radius, spacing, font scale)

```css
.timeline-bar-v2 {
  display: flex;
  height: 38px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border-color, #E2E8F0);
  min-width: max-content;
}
.timeline-scroll-wrapper {
  overflow-x: auto;
  position: relative;
  padding-top: 18px;
}
.seg {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 60px;
  padding: 0 8px;
  font-size: 11px;
  white-space: nowrap;
  border-right: 1px solid rgba(255,255,255,0.5);
  position: relative;
}
.seg-hod        { background: #B5D4F4; color: #042C53; }
.seg-designer   { background: #9FE1CB; color: #04342C; }
.seg-verifier   { background: #FAC775; color: #412402; }
.seg-compliance { background: #F4C0D1; color: #4B1528; }
.seg-endcap     { background: #1A3C6E; color: #fff; flex-grow: 0.6; }
.seg-ongoing {
  background-image: repeating-linear-gradient(45deg, transparent, transparent 8px, rgba(255,255,255,0.3) 8px, rgba(255,255,255,0.3) 16px);
}
.seg-delay {
  background: #F09595 !important;
  color: #501313 !important;
  animation: pulse-delay 2s ease-in-out infinite;
}
@keyframes pulse-delay {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.75; }
}
.target-marker-v2 {
  position: absolute;
  top: 0;
  bottom: 0;
  border-left: 2px dashed #A32D2D;
}
.target-marker-v2 span {
  position: absolute;
  top: -16px;
  font-size: 11px;
  color: #791F1F;
  white-space: nowrap;
  transform: translateX(-50%);
}
.timeline-status-line {
  margin-top: 14px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
}
.status-overdue { background: #FCEBEB; border: 1px solid #F09595; color: #791F1F; }
.status-active  { background: #F8FAFC; border: 1px solid #E2E8F0; color: #475569; }
.status-complete.status-good { background: #EAF3DE; border: 1px solid #C0DD97; color: #173404; }
```

---

## WHAT MUST STAY CORRECT

- This is purely a rendering/display change. Do not alter any model 
  field that drives actual workflow state (`status`, `correction_count`, 
  permission checks, etc.) — only ADD a `reviewed_at` field to 
  `DesignRevision` if it's genuinely missing, since the timeline needs 
  it for accurate per-round HOD review timing.
- Reuse the real `DesignRevision` records for correction history — do 
  not invent a separate/parallel tracking mechanism. The number of 
  segments shown must exactly match the actual number of correction 
  rounds stored in the database.
- The bar must be horizontally scrollable, not compressed, when there 
  are many correction rounds — never shrink text below 11px to force-fit.

---

## TESTING CHECKLIST

- [ ] Brand new request (not yet acknowledged) shows the full planned chain as outlined/empty, with "Awaiting Acknowledgement" actively counting and a delay warning if it's taking too long
- [ ] Request shows correctly through Acknowledge → Assign → Designer → HOD Review with no corrections
- [ ] A request with 2 designer correction rounds shows TWO separate green "Designer V1" / "Designer V2" segments plus two HOD review segments between them, in correct order
- [ ] A request where Verifier sent a correction shows Designer correction segment appearing AFTER the verifier segment, correctly colored
- [ ] A request where Compliance sent a correction shows the same branching pattern after the compliance segment
- [ ] Head of Design appears as its own colored segment at every touchpoint (ack, post-designer review, post-verification, post-compliance, final approval) — never missing
- [ ] Delay banner correctly identifies HOD as the delay source when HOD hasn't acknowledged yet (very first stage)
- [ ] Delay banner correctly identifies Designer/Verifier/Compliance as the delay source when the request is stuck with them
- [ ] Target date marker line appears at the correct proportional position on the bar
- [ ] Completed-on-time request shows green confirmation, no red anywhere
- [ ] Completed-but-late request shows historical red note without active pulsing animation (since it's already finished)
- [ ] Bar scrolls horizontally without breaking layout when a request has many correction rounds
