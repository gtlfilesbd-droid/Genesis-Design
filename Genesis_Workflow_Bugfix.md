# Genesis Design — Workflow & Permission Fixes (Cursor Agent Prompt)

Do NOT change any UI/CSS/layout. These are backend logic, permission, and 
workflow correctness fixes only. Check the existing codebase carefully 
before making changes — these are fixes to EXISTING broken behavior, 
not new screens.

---

## ISSUE 1: Requester Should Not Be Able to Cancel After HOD Acknowledges

**Bug:** Once Head of Design (HOD) has acknowledged a design request, the 
original Design Requester can still see and click "Cancel Request" in 
their "Your Action" panel. This must be blocked.

**Fix:**
1. Find the action panel logic that renders the "Cancel Request" button 
   for the Design Requester role.
2. The Cancel button should only be visible/enabled when 
   `design_request.status == 'new'` (i.e., before HOD has acknowledged).
3. Once status moves to `'acknowledged'` or beyond, hide the Cancel 
   button entirely for the requester.
4. Also add a server-side guard in the cancel view/API endpoint itself 
   (not just hiding the button in UI) — if someone tries to POST a 
   cancel action after acknowledgement, reject it with an error message: 
   "This request has already been acknowledged and cannot be cancelled."
5. Check both the template conditional AND the view/API permission check — 
   fix both layers.

```python
# Example guard in the cancel view
def cancel_request(request, pk):
    obj = get_object_or_404(DesignRequest, pk=pk)
    if obj.status != 'new':
        messages.error(request, "This request has already been acknowledged and cannot be cancelled.")
        return redirect('requests:detail', pk=pk)
    if obj.requested_by != request.user:
        raise PermissionDenied
    obj.status = 'cancelled'
    obj.save()
    ...
```

---

## ISSUE 2: Head of Design Should Be Able to Assign Himself as Designer

**Bug:** In the "Assign Designer" dropdown, Head of Design cannot select 
himself — only other designers appear. But in our SRS, Head of Design 
also does design work himself sometimes.

**Fix:**
1. Check the query/logic that populates the "Assign Designer" dropdown 
   (likely in `PermissionService.get_assignable_designers(project)` or 
   similar).
2. Currently it probably excludes the current user or only includes 
   users with a separate "Designer" role — fix it to be permission-based: 
   ANY user with `DESIGN_PERM_WORK` permission on that project should 
   appear in the dropdown, **including the Head of Design himself**, 
   as long as he also has `DESIGN_PERM_WORK` granted on that project.
3. Confirm in the permission management UI that an admin CAN grant 
   `DESIGN_PERM_WORK` to a user who also has `PROJECT_PERM_ASSIGN`, 
   `PROJECT_PERM_REVIEW`, etc. on the same project — these are not 
   mutually exclusive.
4. Test case: Grant a user both `PROJECT_PERM_ASSIGN` and 
   `DESIGN_PERM_WORK` on Project X. Open "Assign Designer" dropdown on 
   a request in Project X — this user's own name should appear as a 
   selectable option.
5. If HOD assigns himself, the workflow should proceed exactly as if 
   he assigned any other designer (he receives the assignment 
   notification, sees it in "My Tasks", submits work the same way, 
   and then separately reviews his own submission — yes, this means 
   he can review/accept his own work too, since SRS confirms HOD can 
   self-manage this entire chain).

```python
@staticmethod
def get_assignable_designers(project):
    """Returns ALL users with DESIGN_PERM_WORK on this project — 
    including Head of Design if granted this permission."""
    return User.objects.filter(
        project_memberships__project=project,
        project_memberships__is_active=True,
        project_memberships__permissions__code='DESIGN_PERM_WORK'
    ).distinct()
    # Do NOT exclude request.user or filter by "designer-only" role
```

---

## ISSUE 3: HOD Must Set Due Date/Time When Sending to Verifier (Same as Designer Assignment)

**Bug:** When HOD forwards a design to a Verification Team member, there 
is no due date/time field — only verifier selection + message. This 
needs to match the Designer assignment flow exactly.

**Fix:**
1. Find the "Send to Verification" form/modal (triggered from HOD's 
   action panel after accepting a design).
2. Add the same fields used in Designer Assignment:
   - Verifier selection (dropdown — only users with `PROJECT_PERM_VERIFY` 
     on this project)
   - **Due Date** (date picker)
   - **Due Time** (optional, or just date + default end-of-day)
   - Message/Instructions (textarea)
3. On submit, save these to the DesignRequest model:
   ```python
   verification_assigned_to = models.ForeignKey(User, ...)
   verification_due_date = models.DateTimeField(...)
   verification_instructions = models.TextField(...)
   verification_assigned_at = models.DateTimeField(auto_now_add=True)
   ```
4. Display this due date on the Verifier's task card/queue exactly like 
   designer due dates are shown (with the same color-coded urgency 
   indicator: green/yellow/red).
5. Apply the EXACT same fields and pattern when HOD forwards to 
   **Compliance Team** as well (see Issue 6/NB note below) — Compliance 
   assignment should also require due date + message, identical 
   structure to Verification assignment.

---

## ISSUE 4: Verifier Must Acknowledge First — Timer Should Start From Acknowledgement, Not Assignment

**Bug:** Currently, the moment HOD sends a request to the Verifier, the 
workflow timer/clock might be starting immediately. It should NOT. The 
Verifier needs an explicit "Acknowledge" step first (same pattern as 
how Designer acknowledges an assignment before "In Progress" begins).

**Fix:**
1. Add a new status state: `verification_pending_acknowledgement` (the 
   request sits here right after HOD sends it, before Verifier 
   acknowledges).
2. Verifier's action panel should show an "Acknowledge" button when 
   status is in this state. They must click it before they can act 
   further.
3. On acknowledgement:
   ```python
   def verifier_acknowledge(request, pk):
       obj = get_object_or_404(DesignRequest, pk=pk)
       obj.status = 'verification_pending'  # now actively in progress
       obj.verification_acknowledged_at = now()  # ← this is when timer starts
       obj.save()
       ActivityLog.objects.create(
           request=obj, actor=request.user,
           action_type='verification_acknowledged',
           description=f"{request.user.get_full_name()} acknowledged verification request"
       )
       NotificationService.notify(obj.requested_by, ..., "Verifier acknowledged your request")
       return redirect(...)
   ```
4. **Critical:** Any "time elapsed" or "days remaining" calculation for 
   the verification stage must use `verification_acknowledged_at` as 
   the start point — NOT `verification_assigned_at`. Find wherever 
   the SLA/deadline countdown logic computes verifier time and fix 
   the start timestamp reference.
5. Apply this exact same Acknowledge-first pattern to **Compliance 
   Team** as well — they must also acknowledge before their timer 
   starts (per the NB note: Designer, Verifier, and Compliance should 
   all follow the same acknowledge → timer-starts → work pattern).
6. Add corresponding fields:
   ```python
   verification_acknowledged_at = models.DateTimeField(null=True, blank=True)
   compliance_acknowledged_at = models.DateTimeField(null=True, blank=True)
   ```

---

## ISSUE 5: Verifier "Accept" Action is Broken — Throws Error, No Notification

**Bug:** When Verifier clicks "Accept" after reviewing a design, the 
workflow does not proceed — it throws an error and no notification is 
sent to anyone.

**Fix:**
1. Locate the Verifier's "Accept" view/API endpoint. Check Django logs/ 
   console for the actual error trace — likely causes to check:
   - A status transition that isn't defined in the state machine 
     (e.g., trying to set status to a value not in `STATUS_CHOICES`)
   - A missing field that's required on save (e.g., trying to set 
     `verified_by` or `verified_at` on a model field that doesn't exist 
     yet, or a foreign key constraint issue)
   - A notification call referencing a method that doesn't exist or a 
     wrong recipient lookup (e.g., `obj.requested_by.profile.x` where 
     `profile` is None)
2. Confirm the correct state transition for "Verifier Accepts":
   ```python
   def verifier_accept(request, pk):
       obj = get_object_or_404(DesignRequest, pk=pk)
       
       # Permission check
       if not PermissionService.has_project_permission(request.user, obj.project, 'PROJECT_PERM_VERIFY'):
           raise PermissionDenied
       
       obj.status = 'verification_approved'  # or next correct status per workflow
       obj.verified_by = request.user
       obj.verified_at = now()
       obj.save()
       
       ActivityLog.objects.create(
           request=obj, actor=request.user,
           action_type='verification_approved',
           description=f"{request.user.get_full_name()} approved verification"
       )
       
       NotificationService.on_verification_approved(obj)  # confirm this method exists and works
       
       return redirect('requests:detail', pk=pk)
   ```
3. Confirm `NotificationService.on_verification_approved()` exists in 
   `notifications/services.py` and correctly resolves the recipient 
   (HOD — users with `PROJECT_PERM_APPROVE` on that project). If this 
   method is missing or has a bug, fix/add it.
4. After Verifier accepts, the workflow should move to whatever the 
   correct next stage is per SRS:
   - If this was the **first pass** (HOD sent directly to verification 
     without designer correction loop) → status becomes ready for HOD's 
     next action (forward to Compliance, or mark complete)
   - HOD's action panel should now show: "Forward to Compliance" and 
     "Mark Complete" options
5. Test the full chain after fixing: Verifier Accept → no error → 
   HOD receives notification → HOD's action panel updates correctly → 
   Activity log entry appears.

---

## ISSUE 6: Activity Log Incomplete/Incorrect After Verification

**Bug:** After a design passes verification, the Activity Log for that 
design request does not correctly show what happened (missing entries, 
wrong order, or wrong actor/timestamp).

**Fix:**
1. Audit every workflow transition function (acknowledge, assign, 
   submit, review-accept, review-correction, send-to-verify, 
   verifier-acknowledge, verifier-accept, verifier-correction, 
   send-to-compliance, compliance-acknowledge, compliance-accept, 
   compliance-correction, final-approve, complete) and confirm **EVERY 
   ONE** creates an `ActivityLog` entry immediately after saving the 
   status change. Many of these are likely missing the log call 
   entirely — add it wherever missing.
2. Standard pattern to enforce everywhere:
   ```python
   ActivityLog.objects.create(
       request=design_request,
       project=design_request.project,
       actor=request.user,
       action_type='<specific_action>',
       description='<human readable description>',
       old_value=<previous status>,
       new_value=<new status>,
       timestamp=now()
   )
   ```
3. Confirm the Activity Log query on the Request Detail page orders by 
   `timestamp` ascending (oldest first) or descending (newest first) — 
   consistently, matching how it's displayed elsewhere (e.g., Project 
   Activity Log tab).
4. Confirm `old_value`/`new_value` are being populated correctly (not 
   left blank) so the log entry is meaningful, e.g., 
   "Status changed from Verification Pending → Verification Approved."

---

## NB (IMPORTANT — APPLIES ACROSS ALL FIXES): Everyone Must Work Within the Requester's Target Date

The original Design Requester sets a **Target Completion Date** when 
creating the request. Designer, Verifier, and Compliance Team should 
all be operating within/aware of this overall target — not just their 
own individual due dates in isolation.

**Fix:**
1. Confirm `DesignRequest.target_date` (set by requester at creation) 
   is always visible on:
   - HOD's assignment screen (so HOD sets Designer/Verifier/Compliance 
     due dates that don't exceed it, or at least sees it as reference)
   - Designer's task card
   - Verifier's task card
   - Compliance's task card
2. Add a visual warning (not a hard block, unless you confirm otherwise) 
   if HOD sets a due date for Designer/Verifier/Compliance that is 
   LATER than the requester's `target_date`:
   ```
   ⚠️ Warning: This due date (20 Jun) is after the requester's 
   target completion date (15 Jun).
   ```
3. The SLA/deadline color indicator (green/yellow/red) shown to 
   Designer, Verifier, and Compliance should be calculated relative to 
   their OWN assigned due date (not the requester's target date 
   directly) — but the requester's target date should always be 
   displayed alongside for context, so everyone sees the full picture.
4. This rule must apply identically to Compliance Team once that 
   stage is added (see workflow spec below) — same due-date field, 
   same acknowledge-first pattern, same visibility of target date.

---

## ADDITIONAL CONTEXT: Confirmed Workflow (For Reference While Fixing)

This is the confirmed end-to-end flow these fixes must support correctly:

```
1. Designer submits work
2. HOD reviews:
   a. HOD can send back to Designer for correction (loop until accepted)
      → each correction creates a new DesignRevision entry, 
        correction_count increments
   b. HOD accepts → proceeds to step 3
3. HOD decides verification path:
   a. EITHER assign/re-assign a Designer for more work first, OR
   b. Forward directly to Verification Team:
      - Select Verifier from dropdown (only DESIGN_PERM_VERIFY users)
      - Set Due Date + Message (Issue 3)
4. Verifier Acknowledges first (Issue 4) → timer starts
5. Verifier reviews:
   a. Accept → moves to step 6 (Issue 5 — currently broken)
   b. Correction Required → goes back to HOD directly (not designer) 
      with verifier's comment
      → HOD can then re-assign Designer if correction needs design 
        changes (creates new correction version), OR resolve directly
6. Once Verification Approved → HOD forwards to Compliance Team:
   - Same pattern as Verification: select Compliance member, 
     Due Date, Message
   - Compliance Acknowledges first → timer starts (Issue 4, same rule)
7. Compliance reviews:
   a. Accept → moves to Approved status
   b. Correction Required → goes back to HOD with comment, 
      HOD resolves same as before (loop back through designer if needed)
8. Once Compliance Approved → status = Approved
9. HOD marks Completed from action panel → completion_date saved
10. Shortcut: HOD can skip Verification and/or Compliance entirely 
    and mark Complete directly — but Verification Team and Compliance 
    Team members must still be able to SEE this request and its full 
    history (read access), even though they weren't actively involved.
```

---

## TESTING CHECKLIST AFTER FIXES

- [ ] Requester cannot see Cancel button after HOD acknowledges (UI + API both blocked)
- [ ] HOD can select himself in Assign Designer dropdown if he has DESIGN_PERM_WORK
- [ ] HOD self-assigned design works through the full flow (assign → submit → review → forward)
- [ ] Send to Verification form has Due Date field, saves correctly, shows on verifier's task card
- [ ] Send to Compliance form has Due Date field, saves correctly, shows on compliance's task card
- [ ] Verifier sees "Acknowledge" button first, timer does NOT start until clicked
- [ ] Compliance sees "Acknowledge" button first, timer does NOT start until clicked
- [ ] Verifier "Accept" works with no error, sends notification, moves workflow forward
- [ ] Verifier "Correction Required" sends back to HOD (not designer) with comment
- [ ] Compliance "Accept" works with no error, sends notification, moves workflow forward
- [ ] Compliance "Correction Required" sends back to HOD with comment
- [ ] Activity Log shows complete, correctly-ordered entries for every step including verification and compliance stages
- [ ] Requester's target_date is visible to Designer, Verifier, and Compliance throughout
- [ ] Warning shown if HOD sets a due date later than requester's target_date
- [ ] HOD can skip Verification/Compliance and mark Complete directly; both teams retain read access to the request afterward
