# Genesis Design Management System — Complete UI/UX Design Prompt for Cursor Agent

---

## OVERVIEW & TECH STACK

Build a **full-stack Design Management System** called **Genesis Design** using:
- **Backend:** Django + Django REST Framework
- **Database:** PostgreSQL
- **Frontend:** Django Templates + Tailwind CSS (via CDN) + Alpine.js (via CDN) + Chart.js (via CDN)
- **Icons:** Lucide Icons or Heroicons (via CDN)

This is an **internal enterprise tool** for a design company. The UI must feel like a **modern SaaS product** — think Linear.app, Vercel Dashboard, or Notion. Clean, data-dense, professional. NOT like default Django admin or Bootstrap 3.

---

## DESIGN SYSTEM (Apply to EVERY screen)

### Color Palette
```
Primary:        #1A3C6E   (Deep Navy — headers, sidebar, primary buttons)
Primary Light:  #2E75B6   (Medium Blue — active states, links, badges)
Accent:         #E8F0F8   (Ice Blue — card backgrounds, highlights)
Background:     #F8FAFC   (Off White — page background)
Surface:        #FFFFFF   (Pure White — cards, panels)
Border:         #E2E8F0   (Light Gray — dividers, card borders)
Text Primary:   #0F172A   (Near Black — headings)
Text Secondary: #64748B   (Slate Gray — secondary labels)
Text Muted:     #94A3B8   (Light Slate — placeholders, timestamps)

Status Colors:
  Success:      #16A34A  (Green)
  Warning:      #D97706  (Amber)
  Danger:       #DC2626  (Red)
  Info:         #0284C7  (Sky Blue)

Priority Colors:
  Critical:     #DC2626  with bg #FEF2F2
  High:         #D97706  with bg #FFFBEB
  Medium:       #2563EB  with bg #EFF6FF
  Low:          #16A34A  with bg #F0FDF4
```

### Typography
```
Font: Inter (import from Google Fonts)
  - Page Title:     28px, font-weight 700, color #0F172A
  - Section Title:  20px, font-weight 600, color #0F172A
  - Card Title:     16px, font-weight 600, color #0F172A
  - Body:           14px, font-weight 400, color #0F172A
  - Label/Caption:  12px, font-weight 500, color #64748B, uppercase + letter-spacing
  - Muted:          13px, font-weight 400, color #94A3B8
```

### Spacing & Layout
```
Sidebar Width:      260px (fixed, always visible on desktop)
Top Navbar:         64px height
Content Padding:    24px on all sides
Card Border Radius: 12px
Button Radius:      8px
Input Radius:       8px
Card Shadow:        0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)
```

### Component Patterns

**Stat Card:**
```html
<div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
  <div class="flex items-center justify-between mb-3">
    <span class="text-xs font-semibold uppercase tracking-wide text-slate-500">TOTAL REQUESTS</span>
    <div class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
      [icon in text-blue-600]
    </div>
  </div>
  <div class="text-3xl font-bold text-slate-900">248</div>
  <div class="text-sm text-green-600 mt-1 flex items-center gap-1">
    ↑ 12% from last month
  </div>
</div>
```

**Status Badge:**
```html
<!-- Use pill-shaped badges with colored bg + text -->
<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-700">In Progress</span>
<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-700">Completed</span>
<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700">Correction Required</span>
<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">Verification Pending</span>
<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-700">Approved</span>
<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600">Cancelled</span>
```

**Data Table:**
```
- Header: bg-slate-50, text-xs font-semibold uppercase tracking-wide text-slate-500
- Row: hover:bg-slate-50 transition, border-b border-slate-100
- Cell padding: py-3 px-4
- Sticky header on scroll
- Zebra striping optional but rows must have clear separation
```

**Primary Button:** `bg-[#1A3C6E] hover:bg-[#153260] text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors`

**Secondary Button:** `bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 px-4 py-2 rounded-lg text-sm font-semibold transition-colors`

**Danger Button:** `bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-semibold`

**Form Input:** `w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent`

**Form Label:** `block text-sm font-medium text-slate-700 mb-1`

---

## GLOBAL LAYOUT STRUCTURE

### Left Sidebar (Fixed, 260px)
```
┌─────────────────────┐
│  [Logo] Genesis     │  ← Logo + app name, bg #1A3C6E, text white
│  Design             │
├─────────────────────┤
│  [avatar] John Doe  │  ← Logged-in user avatar + name + role badge
│  Head of Design     │
├─────────────────────┤
│  NAVIGATION         │  ← Section label (uppercase, tiny, muted)
│  □ Dashboard        │  ← Active = bg white/10 + left border #60A5FA 3px
│  □ Projects         │
│  □ Design Requests  │
│  □ My Tasks         │
│  □ Workflow Board   │
├─────────────────────┤
│  MANAGEMENT         │
│  □ Team / Users     │
│  □ Reports          │
│  □ Settings         │
├─────────────────────┤
│  □ Notifications 🔴3│  ← Red badge for unread count
│  □ Logout           │
└─────────────────────┘
```
- Sidebar bg: `#1A3C6E`
- Active nav item: left border 3px `#60A5FA`, bg `rgba(255,255,255,0.1)`, text white
- Inactive nav item: text `rgba(255,255,255,0.65)`, hover text white, hover bg `rgba(255,255,255,0.08)`
- Icons: 18px, inline with label, 12px gap

### Top Navbar (64px)
```
┌─────────────────────────────────────────────────────────────┐
│  [≡ breadcrumb: Home / Projects / ABC Project]   [🔔] [👤] │
└─────────────────────────────────────────────────────────────┘
```
- bg: white, border-bottom: 1px solid #E2E8F0
- Right side: notification bell (with badge count) + user avatar dropdown

### Main Content Area
- bg: `#F8FAFC`
- Padding: 24px
- All content inside cards or sections with bg white + border + shadow-sm

---

## SCREEN 01 — LOGIN PAGE

**Layout:** Full-screen split. Left 45% = brand panel, Right 55% = form.

**Left Panel (bg #1A3C6E):**
- Large "G" logo mark (or SVG icon) centered top-third
- Headline: "Genesis Design" in white, 36px bold
- Subtitle: "Design Management System" in rgba(255,255,255,0.7), 16px
- Below: 3 feature bullets with checkmark icons:
  - "Track every design from request to completion"
  - "Real-time workflow visibility"
  - "Full audit trail & accountability"
- Bottom: small text "Powered by Genesis © 2025"

**Right Panel (bg white):**
- Vertically centered form, max-width 380px, mx-auto
- "Welcome back" heading (24px, bold, #0F172A)
- "Sign in to your account" subtext (14px, #64748B)
- Form fields:
  - Email input with mail icon inside (left inset)
  - Password input with lock icon + show/hide toggle
- "Forgot password?" link (right-aligned, text-sm)
- "Sign In" button (full width, bg #1A3C6E)
- NO "Register" or "Sign Up" link (admin-only account creation)

---

## SCREEN 02 — MAIN DASHBOARD (Role-aware)

**Page Title:** "Dashboard" with date subtitle "Monday, 16 June 2025"

### Section A: Stat Cards Row (4 cards)
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Total Active │  │ Running      │  │  Overdue     │  │ Completed    │
│ Projects     │  │ Designs      │  │  Today       │  │ This Month   │
│    24        │  │    87        │  │     6        │  │    43        │
│ ↑ 3 new      │  │ ↑ 12 today  │  │ ⚠ Action req │  │ ↑ 8% growth  │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```
- Overdue card: border-left 4px solid #DC2626, bg #FEF2F2 tint

### Section B: Two Column Layout (60% / 40%)

**Left (60%) — Recent Activity Feed:**
```
┌─────────────────────────────────────────────────────┐
│ Recent Activity                          [View All] │
├─────────────────────────────────────────────────────┤
│ 🔵 [avatar] Rahim submitted "Shop Drawing V2"       │
│    Project: Tower-A  ·  2 min ago                   │
├─────────────────────────────────────────────────────┤
│ 🟡 [avatar] Sarah requested correction on DD-023    │
│    Project: Mall-B  ·  15 min ago                   │
├─────────────────────────────────────────────────────┤
│ 🟢 [avatar] Karim completed Initial Drawing         │
│    Project: Office-C  ·  1 hour ago                 │
└─────────────────────────────────────────────────────┘
```
- Timeline-style: left colored dot + vertical line connecting entries
- Each entry: avatar (32px circle) + bold action text + muted project + timestamp
- Max 8 entries, then "View all activity" link

**Right (40%) — My Tasks / Pending Actions:**
```
┌───────────────────────────────────┐
│ My Pending Actions            (3) │
├───────────────────────────────────┤
│ ⚠ Review: SD-045              │
│   Tower-A  ·  Due Today  [Review]│
├───────────────────────────────────┤
│ 📋 Assign: DD-067             │
│   Mall-B  ·  New Request  [Assign]│
└───────────────────────────────────┘
```

### Section C: Charts Row (shown for Head of Design, Admin)
- Left chart: Bar chart — "Designs by Status This Month" (Chart.js)
- Right chart: Doughnut chart — "Workload by Designer"
- Charts inside white cards with titles and "This Month" select dropdown

### Section D: SLA Alert Strip (if any overdue)
```
⚠️  6 designs have breached SLA deadline — View Overdue Designs →
```
- Full-width banner, bg #FEF2F2, border #FECACA, text #991B1B, icon warning

---

## SCREEN 03 — PROJECTS LIST PAGE

**Page Header:**
```
Projects                              [+ New Project]
3 active · 12 total
```

**Search & Filter Bar:**
```
[🔍 Search projects...]  [Status ▼]  [Client ▼]  [Date Range ▼]
```

**Project Cards Grid (3 columns):**
```
┌──────────────────────────────────┐
│ Tower A Residential Complex      │
│ PRJ-001                          │
│ ────────────────────────────     │
│ Client: Rahman Holdings          │
│ Started: 01 Jan 2025             │
│ ────────────────────────────     │
│ 12 Drawings  |  8 Done  |  2 OD │
│ ████████░░  75% Complete         │
│ ────────────────────────────     │
│ [View Project]       🟢 Active   │
└──────────────────────────────────┘
```
- Progress bar: thin (6px), bg slate-100, fill based on completion %
- Overdue count (OD) in red if > 0
- Status badge top-right: Active (green), On Hold (amber), Completed (blue)
- Card hover: shadow-md, slight translateY(-2px) transition

---

## SCREEN 04 — SINGLE PROJECT DASHBOARD

**Page Header:**
```
← Projects / Tower A Residential Complex
PRJ-001 · Client: Rahman Holdings · Started 01 Jan 2025     [+ New Design Request]
```

**Tab Navigation:**
```
[Overview]  [Design Requests]  [Activity Log]  [Documents]
```

### Tab: Overview
**Row 1 — 4 Stat Cards:**
- Total Design Requests / Running / Completed / Overdue

**Row 2 — Two Columns:**
Left: Project Info Card
```
┌─────────────────────────┐
│ PROJECT DETAILS         │
│ Address: Dhaka-1200     │
│ Start: 01 Jan 2025      │
│ Target: 31 Dec 2025     │
│ Description: ...        │
│ [Edit Project]          │
└─────────────────────────┘
```
Right: Progress Visualization (donut chart showing drawing status breakdown)

**Row 3 — Design History Table:**
```
┌──────┬──────────────┬──────────┬─────────────┬─────────────┬──────────┬────────────┐
│ #    │ Drawing Type │ Req Date │ Requested By│ Designer    │ Status   │ Action     │
├──────┼──────────────┼──────────┼─────────────┼─────────────┼──────────┼────────────┤
│ID-001│ Initial Dwg  │01 Jan 25 │ Karim (PM)  │ Rahim       │ ✅ Done  │ [View]     │
│SD-002│ Shop Drawing │05 Jan 25 │ Sarah (PD)  │ Rafi        │ 🔄 Review│ [View]     │
│DD-003│ Detail Dwg   │10 Jan 25 │ Karim (PM)  │ —           │ 🆕 New   │ [View]     │
└──────┴──────────────┴──────────┴─────────────┴─────────────┴──────────┴────────────┘
```

### Tab: Activity Log
- Chronological timeline of ALL events on this project
- Each event: timestamp (left, fixed width) + colored dot + description + actor

---

## SCREEN 05 — NEW DESIGN REQUEST FORM

**Page:** Modal overlay OR dedicated page `/projects/PRJ-001/request/new/`

**Form Layout (Single column, max-width 640px, centered card):**

```
┌───────────────────────────────────────────────┐
│  New Design Request                           │
│  Project: Tower A Residential Complex         │
├───────────────────────────────────────────────┤
│  Drawing Type *                               │
│  [Select drawing type...              ▼]      │
│                                               │
│  Priority *                                   │
│  ○ Critical  ○ High  ● Medium  ○ Low          │
│  (Radio buttons styled as pill toggles)       │
│                                               │
│  Target Completion Date *                     │
│  [📅 DD/MM/YYYY              ]                │
│                                               │
│  Request Message                              │
│  [                                    ]       │
│  [  textarea, 4 rows, resize-none     ]       │
│  [                                    ]       │
│                                               │
│  Attachments (Optional)                       │
│  ┌─────────────────────────────────────┐      │
│  │  📎 Drag & drop files or click      │      │
│  │     to browse                       │      │
│  └─────────────────────────────────────┘      │
│                                               │
│  [Cancel]                  [Submit Request]   │
└───────────────────────────────────────────────┘
```

**Priority pill toggles:**
- Selected: bg #1A3C6E text white
- Unselected: bg white border slate-200 text slate-600
- Critical selected: bg red-600 text white

---

## SCREEN 06 — DESIGN REQUEST DETAIL PAGE

**URL:** `/requests/REQ-001/`

**Page Header:**
```
← Tower A / Initial Drawing                    [PRJ-001-ID-001]
Shop Drawing · Tower A Residential             [🔴 Critical]
```

**Layout: Two columns (65% left content, 35% right sidebar)**

### Left Column

**Status Progress Bar (Horizontal Steps):**
```
● Request → ● Acknowledged → ● Assigned → ◐ In Progress → ○ Review → ○ Verification → ○ Approved → ○ Completed
```
- Completed steps: filled circle + blue connector line
- Current step: half-filled + pulsing dot animation
- Future steps: empty circle + gray line

**Detail Cards (stacked vertically):**

Card 1: Request Information
```
Request By: Karim Ahmed (PM)      Request Date: 01 Jan 2025
Drawing Type: Shop Drawing        Priority: 🔴 Critical
Target Date: 15 Jan 2025          Message: "Please prioritize..."
```

Card 2: Assignment Information (shown after assignment)
```
Assigned By: Sarah (Head)         Assigned Date: 02 Jan 2025
Assigned To: Rahim                Due Date: 12 Jan 2025
Instructions: "Focus on column dimensions..."
```

Card 3: Revision History (Version Table)
```
Ver  │ Submitted By │ Date       │ Status           │ Notes
─────┼──────────────┼────────────┼──────────────────┼────────────────
V1   │ Rahim        │ 05 Jan 25  │ ❌ Correction    │ Column dims wrong
V2   │ Rahim        │ 08 Jan 25  │ ❌ Correction    │ Scale issue  
V3   │ Rahim        │ 10 Jan 25  │ ✅ Accepted      │ Final version
```

Card 4: Internal Chat / Comments
```
[avatar] Sarah (Head) — 02 Jan 2025 · 10:15 AM
"Please check the column dimensions carefully."

[avatar] Rahim — 02 Jan 2025 · 11:30 AM  
"@Sarah Understood. Will resubmit by EOD."

────────────────────────────────────────────────
[Type a comment... @mention]          [Send →]
```

### Right Sidebar (35%)

**Action Card (changes based on current user's role and current stage):**

For Head of Design (when design is submitted for review):
```
┌─────────────────────────────┐
│ YOUR ACTION REQUIRED        │
│ Design submitted by Rahim   │
│ Submitted: 10 Jan 2025      │
├─────────────────────────────┤
│ [✅ Accept Design         ] │
│ [↩ Request Correction     ] │
│ [🔍 Forward to Verify     ] │
└─────────────────────────────┘
```

For Designer (when assigned):
```
┌─────────────────────────────┐
│ YOUR ASSIGNMENT             │
│ Due: 12 Jan 2025 (3 days)   │
│ Priority: 🔴 Critical       │
├─────────────────────────────┤
│ [📤 Submit Completed Work ] │
│ [📎 Upload Files          ] │
└─────────────────────────────┘
```

**SLA Tracker Card:**
```
┌─────────────────────────────┐
│ SLA STATUS                  │
│ ████████████░░  80%         │
│ 8 of 10 days used           │
│ 🟡 Warning: 2 days left     │
└─────────────────────────────┘
```

**Time Breakdown Card:**
```
┌─────────────────────────────┐
│ TIME BREAKDOWN              │
│ Total elapsed:   10 days    │
│ Request → Assign: 1 day     │
│ Design time:     7 days     │
│ Review time:     2 days     │
│ Delay source:    Design     │
└─────────────────────────────┘
```

---

## SCREEN 07 — WORKFLOW BOARD (Kanban View)

**URL:** `/workflow/`

**Top Controls:**
```
Workflow Board         [🔍 Filter] [Project ▼] [Designer ▼] [Priority ▼]
```

**Kanban Columns (horizontal scroll):**
```
┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ...
│ NEW         │  │ ASSIGNED   │  │ IN PROGRESS│  │ REVIEW     │
│ (3)        │  │ (8)        │  │ (12)       │  │ (5)        │
├────────────┤  ├────────────┤  ├────────────┤  ├────────────┤
│ ┌────────┐ │  │ ┌────────┐ │  │ ┌────────┐ │  │ ┌────────┐ │
│ │SD-045  │ │  │ │ID-023  │ │  │ │DD-067  │ │  │ │SD-012  │ │
│ │Tower A │ │  │ │Mall B  │ │  │ │Office C│ │  │ │Tower A │ │
│ │🔴 Crit │ │  │ │🟡 High │ │  │ │🟢 Med  │ │  │ │🔴 Crit │ │
│ │Rahim   │ │  │ │Rafi    │ │  │ │Karim   │ │  │ │—       │ │
│ │2d left │ │  │ │5d left │ │  │ │Overdue!│ │  │ │1d left │ │
│ └────────┘ │  └─────────── │  └─────────── │  └─────────── │
└────────────┘  └────────────┘  └────────────┘  └────────────┘
```

Each card:
- Card bg: white, border: 1px solid #E2E8F0, border-radius 8px, padding 12px
- Priority indicator: 3px left border in priority color
- "Overdue" badge: red bg, white text, shown if past due date
- Designer avatar (24px circle) + name
- Hover: shadow-md

Full status columns:
1. New Request
2. Acknowledged  
3. Assigned
4. In Progress
5. Submitted
6. Under Review
7. Correction Required
8. Re-Submitted
9. Verification Pending
10. Verification Correction
11. Final Approval Pending
12. Approved
13. Completed

---

## SCREEN 08 — TEAM / USER MANAGEMENT

**URL:** `/admin/users/`

**Page Header:**
```
Team & Users                     [+ Add New User]
12 active members · 2 inactive
```

**Filter Tabs:**
```
[All (14)]  [Active (12)]  [Inactive (2)]  |  Role: [All ▼]
```

**User Cards Grid (3 columns):**
```
┌──────────────────────────────┐
│  [Avatar 56px]               │
│  Rahim Ahmed                 │
│  Senior Designer             │
│  🔵 Designer                 │  ← Role badge
│  ────────────────────────    │
│  📧 rahim@genesis.com        │
│  📱 +880 1711-XXXXXX         │
│  🗓 Joined: 01 Jan 2023      │
│  ────────────────────────    │
│  Tasks: 8 running · 2 OD    │
│  [Edit]           [Disable]  │
└──────────────────────────────┘
```

**Add/Edit User Modal:**
- Full Name, Employee ID, Email, Phone
- Designation, Department
- Role (dropdown: Admin / Head of Design / Designer / Verification Team / Design Requester)
- Reporting Manager (user search dropdown)
- Status toggle (Active/Inactive)

---

## SCREEN 09 — USER PROFILE & PERFORMANCE DASHBOARD

**URL:** `/users/rahim-ahmed/`

**Profile Header Card:**
```
┌────────────────────────────────────────────────────────────┐
│  [Avatar 80px]  Rahim Ahmed                   🟢 Active   │
│                 Senior Designer · Design Dept             │
│                 EMP-0042 · Joined 01 Jan 2023             │
│                 rahim@genesis.com · +880 1711-XXXXXX       │
│                                          [Edit Profile]    │
└────────────────────────────────────────────────────────────┘
```

**Stat Cards (4 across):**
- Total Assigned / Completed / Running / Overdue

**Two Column Layout:**

Left: Monthly Performance Bar Chart (Chart.js)
- X-axis: months, Y-axis: count
- Two bars per month: Assigned (blue) vs Completed (green)

Right: KPI Summary Table
```
┌─────────────────────────────────────────┐
│ KPI SUMMARY                             │
│ On-Time Completion Rate     87%  🟢     │
│ First-Time Approval Rate    72%  🟡     │
│ Average Completion Time     4.2 days    │
│ Total Corrections Received  14          │
│ Total Revisions             23          │
│ Monthly Output (this month) 8 designs   │
└─────────────────────────────────────────┘
```

**Current Task Queue Table:**
```
Drawing #  │ Project    │ Drawing Type │ Due Date   │ Status      │ Priority │ Action
───────────┼────────────┼──────────────┼────────────┼─────────────┼──────────┼────────
SD-045     │ Tower-A    │ Shop Drawing │ 16 Jun 25  │ In Progress │ 🔴 Crit  │ [Open]
DD-067     │ Mall-B     │ Detail Dwg   │ 20 Jun 25  │ Assigned    │ 🟡 High  │ [Open]
```

**Activity Timeline:**
```
● 10 Jun  Submitted SD-044 V3 — Accepted by Sarah
● 09 Jun  Received correction on SD-044 — "Scale issue"
● 08 Jun  Submitted SD-044 V2 — Correction Required
● 05 Jun  Assigned: SD-044 Shop Drawing, Tower-A
```

---

## SCREEN 10 — NOTIFICATIONS PAGE

**URL:** `/notifications/`

```
Notifications                            [Mark All Read]
─────────────────────────────────────────────────────────
🔵 NEW  [avatar] Sarah assigned you SD-045 Shop Drawing      2 min ago
        Project: Tower-A · Due: 16 Jun 2025                  [View →]
─────────────────────────────────────────────────────────
🟡      [avatar] Rahim submitted DD-023 for your review       1 hr ago
        Requires your action                                   [Review →]
─────────────────────────────────────────────────────────
🔴      SLA BREACH: SD-033 is 2 days overdue                  3 hr ago
        Designer: Rafi · Project: Office-C                    [View →]
─────────────────────────────────────────────────────────
        [avatar] Tower-A project progress updated              Yesterday
```
- Unread: bg white + blue left border 3px + bold text
- Read: bg slate-50 + gray left border + normal weight
- Action buttons per notification type

---

## SCREEN 11 — REPORTS PAGE

**URL:** `/reports/`

**Tab Navigation:**
```
[Performance]  [Project Report]  [SLA Compliance]  [Delay Analysis]  [Export]
```

### Tab: Performance

**Filter Row:**
```
[Date Range: This Month ▼]  [Designer: All ▼]  [Project: All ▼]  [Generate Report]
```

**Performance Table:**
```
Designer    │ Assigned │ Completed │ On-Time │ Rate  │ Avg Days │ Corrections │ Score
────────────┼──────────┼───────────┼─────────┼───────┼──────────┼─────────────┼───────
Rahim       │ 24       │ 22        │ 19      │ 86%   │ 4.2 days │ 8           │ ⭐ 88
Rafi        │ 18       │ 15        │ 11      │ 73%   │ 5.8 days │ 14          │ 🟡 71
Karim       │ 31       │ 30        │ 29      │ 97%   │ 3.1 days │ 2           │ 🏆 96
```

**Export buttons:** [📥 Download PDF] [📊 Download Excel] [📋 Copy CSV]

---

## SCREEN 12 — SETTINGS PAGE (Admin only)

**URL:** `/settings/`

**Left settings menu:**
```
⚙ General
📋 Drawing Types
⏱ SLA Configuration
🔔 Notification Settings
🏢 Company Info
👥 Role Permissions
```

**Drawing Types Section:**
```
Drawing Types                              [+ Add Type]
──────────────────────────────────────────────────────
Code │ Drawing Type Name          │ SLA   │ Status │ Action
─────┼────────────────────────────┼───────┼────────┼────────
ID   │ Initial Drawing            │ 3 days│ Active │ [Edit]
DD   │ Details Drawing            │ 5 days│ Active │ [Edit]
SD   │ Shop Drawing               │ 7 days│ Active │ [Edit]
AB   │ As Built Drawing           │ 4 days│ Active │ [Edit]
```

---

## DJANGO MODELS REQUIRED

```python
# Core Models

class Project(models.Model):
    name, code (unique), client_name, address
    start_date, expected_end_date, description
    status = [Active, On Hold, Completed, Cancelled]
    created_by (FK User), created_at

class DrawingType(models.Model):
    name, code (e.g. "ID", "SD"), sla_days, is_active

class DesignRequest(models.Model):
    project (FK), drawing_type (FK)
    design_number (auto-generated: PRJ-001-ID-001)
    priority = [Critical, High, Medium, Low]
    target_date, request_message
    status (15 statuses — see workflow)
    primary_status = [New, Running, Verification, Approved, Completed, Cancelled]
    requested_by (FK User), acknowledged_at
    assigned_to (FK User, nullable), assigned_by (FK User)
    assigned_at, due_date, assignment_instructions
    verified_by (FK User), verified_at
    approved_at, completed_at
    correction_count (int, default 0)
    sla_breached (bool)

class DesignRevision(models.Model):
    request (FK DesignRequest)
    version_number (int, auto-increment per request)
    submitted_by (FK User), submitted_at
    notes, status = [Pending, Accepted, Correction Required]
    correction_notes

class RequestAttachment(models.Model):
    request (FK), file, filename, uploaded_by, uploaded_at

class ActivityLog(models.Model):
    request (FK, nullable), project (FK, nullable)
    action_type, description
    actor (FK User), timestamp
    old_value, new_value (JSON fields for audit)

class Comment(models.Model):
    request (FK), author (FK User)
    content (with @mention parsing), created_at
    mentions (M2M User)

class Notification(models.Model):
    recipient (FK User), type, message
    related_request (FK, nullable)
    is_read, created_at

class UserProfile(models.Model):
    user (OneToOne)
    employee_id, designation, department
    phone, avatar, reporting_manager (FK User)
    role = [Admin, HeadOfDesign, Designer, VerificationTeam, DesignRequester]
```

---

## DJANGO VIEWS & URL STRUCTURE

```
/                           → redirect to /dashboard/
/login/                     → LoginView
/logout/                    → LogoutView
/dashboard/                 → DashboardView (role-aware)

/projects/                  → ProjectListView
/projects/new/              → ProjectCreateView
/projects/<pk>/             → ProjectDetailView (tabs: overview, requests, activity)
/projects/<pk>/edit/        → ProjectUpdateView

/requests/                  → DesignRequestListView (all requests, filterable)
/requests/<pk>/             → DesignRequestDetailView
/projects/<pk>/requests/new/→ DesignRequestCreateView

/workflow/                  → WorkflowBoardView (Kanban)
/my-tasks/                  → MyTasksView (current user's pending items)

/users/                     → UserListView
/users/<pk>/                → UserProfileView
/users/new/                 → UserCreateView (admin only)
/users/<pk>/edit/           → UserUpdateView (admin only)

/reports/                   → ReportsView
/settings/                  → SettingsView (admin only)
/settings/drawing-types/    → DrawingTypeListView
/notifications/             → NotificationListView

/api/requests/<pk>/acknowledge/  → POST
/api/requests/<pk>/assign/       → POST
/api/requests/<pk>/submit/       → POST
/api/requests/<pk>/review/       → POST  (accept or correction)
/api/requests/<pk>/verify/       → POST
/api/requests/<pk>/approve/      → POST
/api/requests/<pk>/complete/     → POST
/api/notifications/mark-read/    → POST
```

---

## WORKFLOW STATE MACHINE (implement as Django signals + service layer)

```
New Request Created
  └→ [Status: New] → Head of Design notified

Head of Design Acknowledges
  └→ [Status: Acknowledged] → SLA timer starts

Head of Design Assigns
  └→ [Status: Assigned] → Designer notified

Designer Acknowledges Assignment
  └→ [Status: In Progress]

Designer Submits Work
  └→ [Status: Submitted] → Head of Design notified

Head of Design Reviews:
  ├→ Correction Required → [Status: Correction Required] → correction_count++ → Designer notified
  └→ Accept → [Status: Under Review / Forward to Verification]

Verification Team Reviews:
  ├→ Correction → [Status: Verification Correction] → back to Designer
  └→ Approve → [Status: Final Approval Pending]

Head of Design Final Approval:
  └→ [Status: Approved]

Head of Design Marks Complete:
  └→ [Status: Completed] → completion_date = now → all parties notified
```

---

## DJANGO TEMPLATE STRUCTURE

```
templates/
  base.html                 ← sidebar + navbar + content block + JS/CSS
  components/
    sidebar.html
    navbar.html
    stat_card.html
    status_badge.html
    priority_badge.html
    activity_feed.html
    pagination.html
    empty_state.html        ← "No designs yet. Create your first request →"
  dashboard/
    index.html
  projects/
    list.html
    detail.html
    create.html
  requests/
    list.html
    detail.html
    create.html
  workflow/
    board.html
  users/
    list.html
    profile.html
    form.html
  reports/
    index.html
  settings/
    index.html
  notifications/
    index.html
```

---

## SPECIFIC UI RULES — MUST FOLLOW

1. **No raw HTML tables without styling.** Every table needs header bg (#F8FAFC), hover rows, proper padding.

2. **Every empty state needs a message.** Don't show empty tables. Show: icon + "No designs found" + CTA button.

3. **All forms need validation messages.** Red border + error text below the field.

4. **All action buttons must be contextual.** Only show actions the current user can perform at the current stage.

5. **Dates should be human-readable.** Show "Today", "Yesterday", "3 days ago" for recent, full date for older.

6. **All status changes must refresh.** Use HTMX or standard form POST. No raw page reloads without feedback.

7. **Loading states.** Show spinner on buttons when processing.

8. **Responsive.** Sidebar collapses to hamburger menu on mobile (<768px). Tables become card-style on mobile.

9. **Breadcrumbs** on all inner pages: `Home / Projects / Tower-A / SD-045`

10. **Confirmation dialogs** before destructive actions (Cancel request, Disable user). Use a modal, not browser `confirm()`.

11. **Auto-generate design number** on request creation: query last number for that project+type, increment.

12. **SLA visual** — show color-coded time remaining on every design card/row (green > 50%, yellow 20-50%, red < 20%).

---

## TAILWIND CONFIGURATION

Since Tailwind is via CDN, use the Play CDN script:
```html
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    theme: {
      extend: {
        colors: {
          primary: '#1A3C6E',
          'primary-light': '#2E75B6',
          'surface': '#F8FAFC',
        },
        fontFamily: {
          sans: ['Inter', 'sans-serif'],
        }
      }
    }
  }
</script>
```

---

## CDN IMPORTS (put in base.html `<head>`)

```html
<!-- Google Font -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

<!-- Tailwind Play CDN -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Alpine.js (for dropdowns, modals, tabs) -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<!-- Lucide Icons -->
<script src="https://unpkg.com/lucide@latest"></script>
```

After icon script, initialize with: `<script>lucide.createIcons();</script>` at body end.

Use icons like: `<i data-lucide="layout-dashboard" class="w-4 h-4"></i>`

---

## SAMPLE DATA TO SEED (create management command `seed_data`)

```python
# Users
Admin: admin@genesis.com / genesis123
Head of Design: sarah@genesis.com / genesis123
Designer 1: rahim@genesis.com / genesis123
Designer 2: rafi@genesis.com / genesis123
Verifier: karim.v@genesis.com / genesis123
Requester: karim@genesis.com / genesis123

# Projects (3)
- Tower A Residential Complex (Active, 12 requests)
- City Mall-B Commercial (Active, 8 requests)
- Office Tower-C (Completed, 5 requests)

# Design Requests
- Mix of all statuses so every screen has visible data
- At least 2 overdue designs
- At least 1 design with 3 revisions
```

---

## FINAL CHECKLIST FOR CURSOR AGENT

- [ ] All 5 user roles implemented with permission checks on every view
- [ ] Login/Logout working with Django auth
- [ ] Sidebar shows correct nav items per role
- [ ] Dashboard shows role-specific data
- [ ] Project CRUD working
- [ ] Design Request full workflow (New → Completed) working
- [ ] Workflow Board Kanban view with all 13+ columns
- [ ] User Profile with performance stats
- [ ] Notification system (in-app)
- [ ] SLA badge showing on all design cards
- [ ] Activity Log for every design and project
- [ ] Reports page with table view and export
- [ ] Settings page for Drawing Types and SLA
- [ ] Seed data command
- [ ] All tables styled (no raw HTML)
- [ ] Empty states on all list pages
- [ ] Mobile responsive sidebar
- [ ] Auto design number generation (PRJ-001-ID-001 format)
- [ ] Correction count tracking
- [ ] No hardcoded data — everything from database
```
