# Genesis Design — Activity Card Redesign, Date/Time Consistency, Dashboard Audit

⚠️ **CRITICAL WARNING:** The workflow logic (design pass/correction/verification/
compliance system) is now working correctly. Do NOT touch, refactor, or modify 
ANY workflow logic, status transitions, permission checks, or backend action 
views. This prompt is ONLY about visual polish, text/copy improvements, and 
date-time display consistency. If you need to touch a workflow file just to 
read/improve a notification message string, do so carefully — change ONLY 
the text, never the logic, conditions, or function structure around it.

---

## TASK 1: Redesign the Activity Card on Request Detail Page

**Location:** Home / Design Requests / Request Detail page → Activity Log card

### 1A. Visual Redesign

Current activity card is plain/unstyled. Redesign it as a clean vertical 
timeline:

```
┌─────────────────────────────────────────────────────────────┐
│  Activity History                                            │
├─────────────────────────────────────────────────────────────┤
│   ●  Design request created                                  │
│   │  Karim Ahmed submitted a new request for Shop Drawing     │
│   │  16 Jun 2026, 10:30 AM                                    │
│   │                                                          │
│   ●  Request acknowledged                                     │
│   │  Sarah Ahmed (Head of Design) acknowledged this request   │
│   │  16 Jun 2026, 11:15 AM                                    │
│   │                                                          │
│   ●  Designer assigned                                        │
│   │  Sarah Ahmed assigned Rahim Hossain · Due 20 Jun 2026     │
│   │  16 Jun 2026, 11:20 AM                                    │
│   │                                                          │
│   ●  Work submitted                                           │
│   │  Rahim Hossain submitted completed design for review      │
│   │  18 Jun 2026, 04:45 PM                                    │
│   │                                                          │
│   ●  Correction required                                      │
│   │  Sarah Ahmed requested correction: "Check column scale"   │
│   │  19 Jun 2026, 09:00 AM                                    │
│   │                                                          │
│   ●  Sent for verification                                    │
│   ●  Verification acknowledged                                │
│   ●  Verification approved                                    │
│   ●  Sent for compliance review                                │
│   ●  Compliance approved                                       │
│   ●  Design approved                                          │
│   ●  Design marked completed                                  │
└─────────────────────────────────────────────────────────────┘
```

**Styling specs:**
- Vertical line connecting all dots (1px, color `#E2E8F0`)
- Dot: 10px circle, color-coded by action type:
  - Creation/submission events → blue `#2E75B6`
  - Acknowledgement events → slate `#64748B`
  - Correction/rejection events → amber/red `#D97706`
  - Approval/acceptance events → green `#16A34A`
  - Completion event → primary navy `#1A3C6E` (slightly larger dot, 14px, to mark the end)
- Each entry: bold title (14px, `#0F172A`) + description line (13px, `#64748B`) 
  + timestamp line (12px, `#94A3B8`)
- Spacing between entries: 20px
- Card padding: 20px, border-radius 12px, border `#E2E8F0`, bg white

### 1B. Rewrite Activity Descriptions to be Meaningful

Audit every `ActivityLog` creation point in the codebase (every workflow 
action: create, acknowledge, assign, submit, correction, accept, send-to-
verify, verifier-acknowledge, verifier-accept, verifier-correction, send-
to-compliance, compliance-acknowledge, compliance-accept, compliance-
correction, approve, complete, cancel).

Replace generic/technical descriptions (e.g. "Status changed to assigned") 
with human-readable, specific sentences. Use this exact pattern — 
`{actor name} {action} {key detail}`:

```python
ACTIVITY_DESCRIPTIONS = {
    'request_created': "{actor} submitted a new {drawing_type} request",
    'acknowledged': "{actor} (Head of Design) acknowledged this request",
    'designer_assigned': "{actor} assigned {designer_name} as designer · Due {due_date}",
    'designer_self_assigned': "{actor} assigned this design to themselves · Due {due_date}",
    'work_submitted': "{actor} submitted completed work for review",
    'correction_required': "{actor} requested correction: \"{comment}\"",
    'work_resubmitted': "{actor} resubmitted the corrected design (Version {version})",
    'design_accepted': "{actor} accepted the submitted design",
    'sent_to_verification': "{actor} forwarded this design to {verifier_name} for verification · Due {due_date}",
    'verification_acknowledged': "{actor} acknowledged the verification request",
    'verification_approved': "{actor} approved the design after verification",
    'verification_correction': "{actor} requested correction during verification: \"{comment}\"",
    'sent_to_compliance': "{actor} forwarded this design to {compliance_name} for compliance review · Due {due_date}",
    'compliance_acknowledged': "{actor} acknowledged the compliance review request",
    'compliance_approved': "{actor} approved the design after compliance review",
    'compliance_correction': "{actor} requested correction during compliance review: \"{comment}\"",
    'design_approved': "{actor} gave final approval to this design",
    'design_completed': "{actor} marked this design as completed",
    'request_cancelled': "{actor} cancelled this design request",
}
```

Update every `ActivityLog.objects.create(...)` call to use 
`.format()` or an f-string with this dictionary so descriptions are 
consistent and readable everywhere (Activity Card on Request Detail, 
Project Activity Log tab, anywhere else activity is shown).

### 1C. Date + Time Together, Always

Currently activity timestamps may show only date, or inconsistent format. 
Fix the template filter so EVERY timestamp on the Activity Card shows 
both date and time, formatted like: `16 Jun 2026, 10:30 AM`

```django
{{ activity.timestamp|date:"d M Y, h:i A" }}
```

If there's a custom template tag/filter for "humanized" time (e.g. 
"2 hours ago"), you may show that as a secondary subtle hint, but the 
full date+time must always be visible too — never date-only or 
relative-time-only.

### 1D. Remove the Notification Card Below Activity Log

There is currently a Notification card/section displayed directly below 
the Activity Log on the Request Detail page. Remove this card entirely 
from this page. (Notifications should still exist normally on the 
Notifications page — only remove this specific duplicate card from the 
Request Detail view.)

---

## TASK 2: Dashboard-Wide Date Display Audit — Always Show Date + Time

**Problem:** Across dashboard pages, some date fields show only the date 
with no time, which is inconsistent and unclear (especially for fields 
like "Submitted At", "Assigned At", "Last Updated").

**Fix:**
1. Search the entire codebase (all templates) for date filters like:
   ```django
   {{ something.date|date:"d M Y" }}
   {{ something.created_at|date:"M d" }}
   ```
2. For any field that is a `DateTimeField` (has both date AND time stored 
   in the database) — wherever it's displayed anywhere in the UI 
   (dashboard cards, tables, timelines, profile pages, task queues) — 
   it MUST show both date and time:
   ```django
   {{ something.created_at|date:"d M Y, h:i A" }}
   ```
3. For fields that are genuinely `DateField` only (e.g. `target_date`, 
   `due_date` if these were designed as date-only without time) — 
   these can correctly show date-only. Do NOT force time onto pure 
   date fields where time was never collected/meaningful.
4. Double check these specific known timestamp fields across the project 
   and confirm date+time format everywhere they appear:
   - `created_at`, `requested_at`
   - `acknowledged_at`
   - `assigned_at`
   - `submitted_at`
   - `verification_acknowledged_at`, `verification_approved_at`
   - `compliance_acknowledged_at`, `compliance_approved_at`
   - `approved_at`
   - `completed_at`
   - `last_login`, `joined_at` (user profile)
5. Apply this audit across ALL dashboards: Main Dashboard, Project 
   Dashboard, Workflow Board cards, User Profile Dashboard, Reports 
   page, Notifications list — anywhere a timestamp is rendered.

---

## TASK 3: Audit Every Role's Dashboard Against the Original SRS Structure

Go back to the original SRS specification for each role's dashboard 
(Design Requester, Head of Design, Designer, Verification Team, 
Compliance Team, Admin) and verify the CURRENT implementation actually 
shows everything specified. Do not redesign — just verify completeness 
and fix any missing/incorrect data bindings.

### 3A. Design Requester Dashboard — Verify it shows:
- [ ] Projects Created: Total, Active, Completed, Cancelled counts
- [ ] Per-project breakdown: Name, Code, Creation Date, Current Status, 
      Total/Running/Completed Drawings counts
- [ ] Design Request History list: Drawing Type, Request Date, Priority, 
      Current Holder (who has it now), Current Stage

### 3B. Head of Design Dashboard — Verify it shows:
- [ ] Current Workload: New Requests Waiting, Assigned to Designer, 
      Waiting for Review, Waiting for Verification, Waiting for 
      Compliance, Waiting for Approval, Overdue Designs (each as 
      separate accurate counts, not merged/wrong)
- [ ] Performance Statistics: Total Requests Managed, Total Approved, 
      Total Rejected/Cancelled, Total Corrections Issued, Average 
      Review Time, Average Assignment Time
- [ ] Work Queue table: Design Name, Project, Current Stage, Assigned 
      Designer/Verifier/Compliance (whoever currently holds it), 
      Pending Since (date+time), Due Date, Priority

### 3C. Designer Dashboard — Verify it shows:
- [ ] Work Summary: Total Assigned, Running, Completed, Overdue, 
      Correction Received count, Rework Count
- [ ] Productivity: Average Completion Time, Fastest Completed, 
      Slowest Completed, Monthly Output, Yearly Output
- [ ] Per-design list: Drawing Name, Project, Request Date, Assigned 
      Date, Due Date, Status, Current Stage, Revision Count

### 3D. Verification Team Dashboard — Verify it shows:
- [ ] Verification Summary: Total Verified, Pending, Approved, 
      Rejected/Correction-requested counts
- [ ] Current Queue: Drawing Name, Project, Received Date (when HOD 
      sent it), Acknowledged Date, Pending Days (counted from 
      acknowledgement, not assignment — confirm this matches the 
      Issue 4 fix from before), Priority, Assigned By (which HOD)
- [ ] Performance: Average Verification Time, Total Corrections Raised, 
      Total Final Approvals Given

### 3E. Compliance Team Dashboard — Verify this exists and mirrors the 
     Verification Team Dashboard structure exactly:
- [ ] Compliance Summary: Total Reviewed, Pending, Approved, Correction-
      requested counts
- [ ] Current Queue: same fields as verification queue
- [ ] Performance: Average Review Time, Total Corrections Raised, 
      Total Final Approvals Given
- [ ] If this dashboard doesn't exist yet, build it now using the exact 
      same template/layout as the Verification Team Dashboard — just 
      pointing to compliance-stage data instead of verification-stage 
      data. Do not invent a new layout.

### 3F. Admin Dashboard — Verify it shows:
- [ ] System-wide overview: Total Users, Total Active Projects, Total 
      Design Requests (all statuses), Total Overdue
- [ ] Quick links to: User Management, Permission Management, Drawing 
      Type Settings, Reports

For every gap found above, fix the VIEW (context data being passed) — 
not the template structure — unless a field is genuinely missing from 
the template and needs to be added to match what's already styled 
elsewhere on that same dashboard.

---

## TASK 4: Improve Notification Message Wording

Audit every notification message generated by `NotificationService` 
(all the `on_*` methods). Rewrite each message to be clear and 
immediately understandable without needing to open the request. Use 
this tone: direct, specific, includes the key fact (who/what/which 
project), no jargon.

```python
NOTIFICATION_MESSAGES = {
    'request_created': "{requester} submitted a new {drawing_type} request for {project}",
    'acknowledged': "Your request for {drawing_type} ({project}) has been acknowledged by {hod_name}",
    'designer_assigned': "You've been assigned to design {drawing_type} for {project} · Due {due_date}",
    'work_submitted': "{designer_name} submitted {drawing_type} ({project}) for your review",
    'correction_required': "Correction needed on {drawing_type} ({project}): \"{comment}\"",
    'design_accepted': "Your design for {drawing_type} ({project}) has been accepted",
    'sent_to_verification': "You've been asked to verify {drawing_type} for {project} · Due {due_date}",
    'verification_acknowledged': "{verifier_name} has started verifying {drawing_type} ({project})",
    'verification_approved': "{verifier_name} approved {drawing_type} ({project}) after verification",
    'verification_correction': "Verification correction needed on {drawing_type} ({project}): \"{comment}\"",
    'sent_to_compliance': "You've been asked to review {drawing_type} for {project} for compliance · Due {due_date}",
    'compliance_acknowledged': "{compliance_name} has started compliance review on {drawing_type} ({project})",
    'compliance_approved': "{compliance_name} approved {drawing_type} ({project}) after compliance review",
    'compliance_correction': "Compliance correction needed on {drawing_type} ({project}): \"{comment}\"",
    'design_approved': "{drawing_type} ({project}) has received final approval",
    'design_completed': "{drawing_type} ({project}) has been marked completed",
}
```

Make sure every `NotificationService.notify(...)` call uses one of 
these templates with the actual values filled in (requester name, 
drawing type, project name, due date, comment text, etc.) — not a 
generic "Status updated" message.

**Do not change WHO receives which notification or WHEN it's sent — 
only improve the message text itself.**

---

## SAFETY CHECKLIST BEFORE YOU FINISH

- [ ] Confirm no workflow status transition logic was altered
- [ ] Confirm no permission check (`PermissionService` calls) was altered
- [ ] Confirm no view function signature or URL routing was changed
- [ ] Confirm the full workflow (Request → Assign → Submit → Review → 
      Verify → Compliance → Approve → Complete) still runs end-to-end 
      without errors after these changes
- [ ] Confirm Activity Card renders correctly on an existing request 
      with full history (one that has gone through corrections, 
      verification, and compliance)
- [ ] Confirm all 6 dashboards (Requester, HOD, Designer, Verification, 
      Compliance, Admin) load without errors and show real data, not 
      blank/zero placeholders
