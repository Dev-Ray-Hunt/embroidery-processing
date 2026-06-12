# POC 4 — Build Plan: Order-to-Production Workflow (full-workflow revision)

This supersedes the stripped-down five-state spec in root `POC_4_Order_Workflow.md`.
The authoritative process is the **"Workflow Confirmation & Refinements (2026-06-12)"**
section of `PRD_Coloring_Up_Order_Management.md` — read it first. It captures a
grilling session that confirmed the full production workflow and surfaced six
load-bearing changes the old spec didn't have.

## What changed vs. the old POC 4 spec

- **Status is per line item**, with a rollup summary at the order header (not order-level).
- **Color-up match key = `logo + style_number + color_code`, exact match only.**
- **Approval grain = the color-up proof**; approving cascades to every line item using it.
- **Repeat / exact-match lines skip _customer_ approval but pass a _production_ approval gate.**
- **Trim sheet = a Production Batch** — an on-demand view keyed on `logo + placement + thread choices`, approved-only, never crossing customers.
- **Internal Review = configurable gate** (customer default + order override).
- **New states:** `Awaiting Logo`, `Phone Call` (5 unanswered reminders), `Needs Approver`.
- **Satellite intake:** references the NetSuite SO; CSV/paste mass-import; logo auto-linked via the NetSuite file-cabinet logo id; DSTs added to an order *or* to the customer library.
- **Design data from the DST parse (POC 1), not Wilcom PDF parsing.**

## State machine (per line item)

```
New ─► Awaiting Logo ─►[logo linked via file-cabinet id, or triage]
        ├─ exact logo+style+color match ─► Production Approval ─► Production Ready ─► In Production ─► Complete
        └─ no match ─► Color-Up In Progress ─►(opt) Internal Review ─► Needs Approver? ─► Sent for Approval
                          ├─ Approved (cascades) ─► Production Approval ─► …
                          ├─ 5 unanswered reminders ─► Phone Call
                          └─ Changes Requested (comment) ─► Revision In Progress (new immutable version) ─┘
```

## Tech stack (default — bake-off scorecard is a Step 7 deliverable)

- **Backend:** Python 3.10+ / FastAPI (consistent with POC 2 step 3).
- **Frontend:** Jinja2 + HTMX (server-rendered, no build step).
- **Storage:** SQLite for the POC (schema written migration-ready for PostgreSQL).
- **DST parse:** reuse `pocs/poc1_dst_renderer`. **Color-up editor:** reuse `pocs/poc3_color_up_editor` (DST/editor work is local-only — see cloud note).

## Build steps

### Step 1 — Data layer + state machine  ← START HERE (cloud-friendly, no DST needed)
- SQLite schema: `customers`, `approvers`, `logos` (with `netsuite_file_cabinet_id`,
  parsed DST fields, optional stabilizer/runtime), `color_ups` (immutable versions,
  status, approved_by incl. team-proxy), `orders` (NetSuite SO ref, no status),
  `order_line_items` (**per-line `status`**, style/color/size grid, logo+colorup FKs,
  placement), `status_history` (actor, from/to, timestamp, team-proxy flag).
- State machine: all states above, transition validation, audit logging.
- Match-key logic (`logo + style_number + color_code`, exact) + approval **cascade**.
- Production-batch query: group ready line items by `logo + placement + thread-sequence`,
  approved-only, within a single customer.
- CRUD + a thorough pure-Python test suite (no DST, no network → runs in cloud).

### Step 2 — Intake + dashboard
- CSV/paste mass-import → orders + line items.
- Order entry form; NetSuite SO reference; file-cabinet-id → logo auto-link.
- `Awaiting Logo` triage queue; two DST entry points (to-order, to-library).
- Dashboard: per-line status badges + order-header rollup; filters/search.
- DST upload → parse via POC 1 *(DST-dependent: stub + skip in cloud)*.

### Step 3 — Color-up editor integration  *(POC 3 + DST dependent: local only)*
- Embed POC 3 editor; load order's logo/DST; wire save → state transitions.

### Step 4 — Proof + approval page
- Hosted approval page; approver selects name from customer's approver list (identity B).
- Per-color-up Approve / Request-Changes (+ comment); approval cascade; immutable versions.
- `Needs Approver` inline-add popup.

### Step 5 — Reminders + notifications
- Daily morning reminder digest per customer; cap 5 → `Phone Call` status.
- Customer response surfaces on assigned-artist **and** lead/manager dashboards.

### Step 6 — Production batch + trim sheet
- On-demand batch view (operator works by Order #, decides grouping at the queue).
- Trim sheet generation (design + thread sequence + garment run); `Production Approval`
  gate (incl. on zero-customer-touch repeats); one-click In Production / Complete.

### Step 7 — Testing + evaluation
- All test scenarios; storage + framework bake-off scorecards; design recommendation.

## Cloud-agent scope note

The cloud sandbox has **no real DSTs and no POC 3 editor** (local-only by policy, see
`CLOUD_AGENTS.md`). A cloud run should implement **Step 1** in full and the data-light
parts of **Step 2** (CSV import, models, dashboard skeleton). All DST/editor integration
must be stubbed behind interfaces, and DST-dependent tests should **skip** with a clear
reason — that's expected, not a failure.
