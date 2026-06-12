# POC 4: Order-to-Approval Workflow — Findings

## What we built (Step 1 — 2026-06-12)

### Data layer
SQLite schema across 7 tables:

| Table | Purpose |
|-------|---------|
| `customers` | Account records; `internal_review_default` controls the IR gate |
| `approvers` | People authorised to approve proofs; `is_primary` + `active` flags |
| `logos` | Design files owned by a customer; `netsuite_file_cabinet_id` is the external key; all DST-parsed fields (`dst_stitch_count`, `dst_color_count`, `dst_width_mm/height_mm`, `dst_stop_count`, `dst_trim_count`) are nullable and populated by stub interface only |
| `color_ups` | Immutable versioned colour configurations — `(logo_id, style_number, color_code, version)` unique; `thread_sequence` stored as JSON; `approved_by_team_proxy` flag for proxy approvals |
| `orders` | NetSuite SO reference; deliberately **no `status` column** — status lives on line items |
| `order_line_items` | Per-line `status`; `size_quantities` JSON; `send_for_approval_override` flag |
| `status_history` | Immutable audit log with `actor`, `from_status`, `to_status`, `team_proxy`, `notes`, and `timestamp` |

Schema written migration-ready for PostgreSQL (comments inline in `schema.py` for every type mapping).

### State machine
12 states, explicitly enumerated transitions, no inferred edges:

```
New → Awaiting Logo → Color-Up In Progress → Internal Review ┐
                    └→ Production Ready   ←──────────────────┘→ Needs Approver → Sent for Approval
                                                                                 ↓         ↓         ↓
                                                                              Approved  Phone Call  Revision In Progress
                                                                                 ↓                      ↓
                                                                         Production Ready ←── Color-Up In Progress
                                                                                 ↓
                                                                           In Production → Complete
```

Every `transition()` call validates the edge and writes to `status_history`.  `bulk_transition()` skips items where the edge is invalid without raising.

### Match-key logic
`(logo_id, style_number, color_code)` — exact match only, per spec decision 2.  A colour code is not portable across styles (spec decision 2 rationale).

`resolve_logo_for_line_item()` handles the Awaiting Logo → fork:
- Approved exact match AND no override → Production Ready (auto-assigns color-up FK)
- No match OR override → Color-Up In Progress

`cascade_approval()` marks the color-up Approved and advances every line item referencing it from `Sent for Approval`, `Phone Call`, or `Needs Approver` through `Approved → Production Ready` in a single call.  Does not cross customers (each color-up belongs to one logo which belongs to one customer).

### Production batch query
`get_production_batches()` groups Production Ready line items by `(customer_id, logo_id, placement, thread_sequence_canonical)`.  Thread sequences are normalised with `sort_keys=True` so insertion-order differences don't create phantom splits.  Never crosses customers.  Excludes non-Approved color-ups even if the line item is Production Ready (defensive guard for data-integrity edge cases).

### DST / editor stubs
`dst_stub.py` exports `parse_dst()` and `open_color_up_editor()`, both raising `DSTNotAvailableError(NotImplementedError)`.  All tests that would require DST files or the POC 3 editor are in `test_dst_stub.py` and confirm the stub contract rather than skipping — no real DST files needed.

## Test results

```
65 passed in 0.24s
```

Coverage: state machine (pure + DB), CRUD for all entities, FK enforcement, match-key exact-match semantics, approval cascade, production batch grouping, and DST stub contract.

## What is stubbed / skipped and why

| Feature | Status | Reason |
|---------|--------|--------|
| DST file parse (POC 1) | Stubbed behind `DSTNotAvailableError` | DSTs are local-only; cloud sandbox has none |
| Color-up editor (POC 3) | Stubbed behind `DSTNotAvailableError` | POC 3 editor is local-only |
| FastAPI web layer | Not started | Step 2 scope |
| CSV/paste mass-import | Not started | Step 2 scope |
| Email / reminder logic | Not started | Step 5 scope |
| Production batch trim-sheet render | Not started | Step 6 scope |

## What we measured

Step 1 is pure data layer + logic; no UI performance measurements apply yet.

## Scorecards

### Data storage

| Option | R (reliability) | Q (query power) | S (simplicity) | F (future path) | Weighted |
|--------|----------------|-----------------|----------------|-----------------|----------|
| A. SQLite | ✓ | Good (JSON cols) | ✓ easy | Needs migration | **Strong for POC** |
| B. PostgreSQL | ✓ | Best (JSONB ops) | Needs Docker | ✓ prod-ready | Overkill for POC |
| C. JSON flat files | Fragile | None | Trivial | Throwaway | Not recommended |

SQLite wins for the POC; the schema is written to migrate with minimal changes (all comments in `schema.py`).

### Web framework

Not yet evaluated — Step 2 work.

## What we learned

1. The `(logo + style_number + color_code)` exact-match key is clean to implement; the immutable-version pattern for color-ups is straightforward with a UNIQUE constraint.
2. Per-line status + order-header rollup (`order_status_rollup()`) is simple and flexible for the partial-ship scenarios.
3. Approval cascade across all matching line items in a single call keeps the controller thin.
4. Python 3.12 `detect_types=sqlite3.PARSE_DECLTYPES` conflicts with ISO-8601 timestamps (T separator vs space); dropped in favour of TEXT columns, no loss of functionality.

## Recommendation if shipping for real

Keep SQLite for the POC through Step 4 (approval page).  Migrate to PostgreSQL before Step 5 (reminders + notifications) where concurrent writes from the daily digest job will matter.  The schema DDL is already annotated for the migration.

## Open questions / follow-ups

- NetSuite SO ↔ VRLink boundary: how does the SO number get into the system? (manual entry for POC, integration TBD)
- Non-DST production fields (stabilizer, runtime): are they hard must-haves before the floor will use trim sheets?
- `internal_review_default` is per-customer but some customers may want per-logo overrides — not modelled yet.
