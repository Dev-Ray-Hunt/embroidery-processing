# POC 4: Order-to-Approval Workflow

## Proof of Concept — Project Document

---

## Objective

Prove the full order workflow end-to-end: an order comes in with a DST file, a team member creates a color-up using the editor, a proof is generated, the proof is presented for approval on a local approval page, and the order status is tracked through to "approved." All local — no email, no NetSuite, no external integrations. This validates that the tools from POCs 1-3 can be assembled into a working production workflow.

## Why This Is Last

This is the lowest technical risk POC — it's standard web application development. But it's the most important validation: can the DST renderer, thread catalogue, and color-up editor actually work together as a cohesive production tool? It also establishes the data model, state machine, and UI patterns that the full application will build on.

---

## Background

### The Workflow This POC Simulates

Today at Straight Down, when an embroidery order comes in:

1. **Order arrives** — A sales order in NetSuite includes embroidery requirements (logo, placement, garment styles)
2. **Design is identified** — The team finds or creates the DST file for the customer's logo
3. **Color-up happens** — A team member selects thread colors based on the garment color and customer preferences
4. **Proof is created** — A visual showing what the embroidery will look like is assembled for the customer
5. **Customer approves** — The customer reviews and signs off (or requests changes)
6. **Production** — The approved trim sheet goes to the machine operators

This POC simulates steps 1-5 in a single local web application. The goal is to prove the tools work together — not to build the production-grade system (that comes in the full app build).

### What's Local vs. What Comes Later

| This POC (Local) | Full App (Later) |
|-------------------|------------------|
| Manual order entry form | NetSuite integration, customer management |
| Single DST file per order | Customer logo library with multiple logos |
| Color-up saved per order | Reusable approved color-ups per logo/product |
| Local approval page | Email delivery via Microsoft Graph |
| Simple order list | Full dashboard with filters, search, reporting |
| No authentication | User auth and roles |
| SQLite or flat files | PostgreSQL |

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Backend** | Python 3.10+ |
| **Frontend** | HTML/CSS/JS |
| **Rendering** | Winning approach from POC 1 |
| **Thread data** | Catalogue from POC 2 |
| **Color-up editor** | Winning approach from POC 3 |
| **Evaluation priority** | 1. Reliability → 2. Usability → 3. Speed → 4. Flexibility |

---

## What To Build

A lightweight web application with five pages/views:

### Page 1: Order Entry

A form to create a new order. Fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Customer name | Text | Yes | Free text for POC |
| Order / PO number | Text | Yes | Free text |
| Garment type | Dropdown | Yes | Polo, Hat, Jacket, Vest, Bag, Other |
| Garment color | Text | Yes | e.g., "Black", "Navy", "White" |
| Placement | Dropdown | Yes | Left Chest, Cap Front, Right Sleeve, Back, etc. |
| Quantity | Number | Yes | Total pieces |
| DST file | File upload | Yes | The embroidery design file |
| Special instructions | Text area | No | Free text notes |

On submit:
- Order is created with status **"New"**
- DST file is stored and parsed (stitch count, stop count validated)
- User is redirected to the order dashboard

### Page 2: Order Dashboard

A list of all orders showing:

| Column | Source |
|--------|--------|
| Order # / PO | From order entry |
| Customer | From order entry |
| Design | DST file name + stitch count |
| Status | Current workflow state (color-coded) |
| Garment | Type + color |
| Created | Date/time |
| Actions | Buttons based on current status |

**Status indicators** (color-coded badges):

| Status | Color | Available Actions |
|--------|-------|-------------------|
| **New** | Gray | "Start Color-Up" → opens editor |
| **Color-Up In Progress** | Blue | "Continue Color-Up" → opens editor |
| **Proof Ready** | Yellow | "View Proof", "Send for Approval" |
| **Sent for Approval** | Orange | "View Approval Page" |
| **Approved** | Green | "View Details" |
| **Rejected** | Red | "View Feedback", "Revise Color-Up" |

Sorting: by status (active first), then by creation date (newest first).

### Page 3: Color-Up Editor (Embedded)

The interactive color-up editor from POC 3, embedded in the workflow context:

- Loads the order's DST file automatically
- Shows order context at the top (customer, garment type/color, placement, instructions)
- Full POC 3 editor functionality: region selection, thread picker, preview, summary
- **"Save & Mark Proof Ready"** button — saves the color-up and advances order status to "Proof Ready"
- **"Save Draft"** button — saves progress without advancing status

### Page 4: Proof Preview

Displays the generated proof for internal review before sending for approval:

- Rendered design with assigned thread colors (using POC 1 renderer) — large, high-quality image
- Order details sidebar: customer, PO, garment, placement, quantity
- Color-up summary: stop-by-stop thread list with swatches, catalog numbers, thread names
- Special instructions displayed prominently
- **"Send for Approval"** button — advances status to "Sent for Approval" and generates the approval page link
- **"Back to Editor"** button — return to color-up for adjustments

### Page 5: Approval Page

A standalone page simulating what a customer would see. Clean, simple, professional:

- Straight Down header/branding (simple — logo + company name)
- Large rendered proof image of the design
- Order reference: PO number, design name
- Thread colors used (catalog numbers + swatches)
- Placement note (e.g., "Left Chest")
- **"Approve"** button — marks the order as approved, shows confirmation
- **"Request Changes"** button — opens a text area for feedback, submits rejection with comments

On approve:
- Order status → **"Approved"**
- Approval timestamp recorded

On reject:
- Order status → **"Rejected"**
- Feedback text stored with the order
- Dashboard shows "Revise Color-Up" action, which reopens the editor

---

## Workflow State Machine

```
                    ┌─────────────────────────────────┐
                    │                                 │
                    ▼                                 │
New ──► Color-Up In Progress ──► Proof Ready ──► Sent for Approval ──► Approved
                    ▲                                 │
                    │                                 │
                    └──── Rejected ◄──────────────────┘
                         (with feedback)
```

**State transition rules:**
- New → Color-Up In Progress: when user clicks "Start Color-Up"
- Color-Up In Progress → Proof Ready: when user saves a complete color-up (all stops assigned)
- Proof Ready → Sent for Approval: when user clicks "Send for Approval" on the proof preview
- Sent for Approval → Approved: when approval page "Approve" is clicked
- Sent for Approval → Rejected: when approval page "Request Changes" is clicked
- Rejected → Color-Up In Progress: when user clicks "Revise Color-Up"
- Proof Ready → Color-Up In Progress: when user clicks "Back to Editor" (optional, for internal revisions)

**Audit trail:** Every state transition records: previous state, new state, timestamp, and who triggered it.

---

## Bake-Off: Data Storage

### Option A: SQLite

**Description:** File-based relational database. Zero setup, SQL queries, easy to inspect with DB Browser for SQLite.

**Schema:**
```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_name TEXT,
    po_number TEXT,
    garment_type TEXT,
    garment_color TEXT,
    placement TEXT,
    quantity INTEGER,
    special_instructions TEXT,
    dst_filename TEXT,
    dst_stitch_count INTEGER,
    dst_stop_count INTEGER,
    status TEXT DEFAULT 'new',
    colorup_data JSON,
    proof_image_path TEXT,
    approval_feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_history (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    from_status TEXT,
    to_status TEXT,
    changed_by TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Pros:** Zero setup, SQL is well-known, easy to migrate to PostgreSQL later.
**Cons:** No concurrent write safety (fine for POC with one user).

---

### Option B: PostgreSQL

**Description:** Production-grade relational database. Same SQL, but with concurrency, JSON operators, and full production readiness.

**Pros:** No migration needed when building the full app. Concurrent access from day one.
**Cons:** Requires running a PostgreSQL server (Docker or local install). Overkill for a POC.

---

### Option C: JSON Flat Files

**Description:** Each order is a JSON file on disk. Simplest possible storage.

**Pros:** Zero dependencies, human-readable, trivial to debug.
**Cons:** No querying, no relationships, no concurrent safety. Would need complete replacement for the full app.

---

## Bake-Off: Web Framework

### Option A: FastAPI + HTMX

**Description:** Python FastAPI backend serving HTML pages via Jinja2 templates. HTMX for dynamic updates without a full JavaScript framework — partial page swaps via HTML fragments over HTTP.

**Pros:** Minimal JavaScript, server-rendered HTML is simple, HTMX handles interactivity (status updates, form submissions) cleanly. Fast to build.
**Cons:** Less rich interactivity than a React SPA. HTMX is newer and less documented.

---

### Option B: FastAPI + React

**Description:** FastAPI serves a JSON API. Separate React SPA frontend. Richer client-side interactivity.

**Pros:** Rich UI, natural fit if POC 3 editor is React-based. Clean API separation.
**Cons:** More code, build step required, two separate codebases to maintain.

---

### Option C: Flask + Jinja2

**Description:** Classic Python web app. Flask routes serve Jinja2 templates. Traditional server-rendered multi-page app.

**Pros:** Extremely well-documented, simple mental model, fast to build.
**Cons:** Less interactive without additional JS. Flask is slightly less performant than FastAPI for async operations.

---

## What's NOT in This POC

These are explicitly out of scope — saved for the full application build:

- **Customer management** — Customers with approvers, logos, reusable color-ups. POC uses free-text customer name.
- **NetSuite integration** — Orders entered manually, not pulled from NetSuite.
- **Email delivery** — Approval happens on a local web page, not via emailed proofs.
- **Trim sheet generation** — The combined production document. POC exports a color-up sheet only.
- **Line items with size grids** — POC handles one garment type/color per order.
- **Multi-user auth** — No login, single-user POC.
- **Production tracking** — POC ends at "Approved." Production queue and completion tracking come later.

See [PRD_Coloring_Up_Order_Management.md](./PRD_Coloring_Up_Order_Management.md) for the full application scope.

---

## Pass/Fail Criteria

- [ ] Team member can create an order and upload a DST file via the order entry form
- [ ] Order appears on the dashboard with correct status ("New")
- [ ] Clicking "Start Color-Up" opens the editor with the order's DST file loaded
- [ ] Color-up editor allows full thread assignment for all regions (POC 3 functionality)
- [ ] Saving a complete color-up advances status to "Proof Ready"
- [ ] Proof preview page shows the rendered design with assigned colors and order details
- [ ] "Send for Approval" generates a working approval page link
- [ ] Approval page displays the proof professionally with Approve / Request Changes options
- [ ] Approving updates the order status to "Approved" on the dashboard
- [ ] Rejecting captures feedback text and resets status for revision
- [ ] At least 5 test orders can be processed through the full workflow without data loss or broken states
- [ ] Audit trail correctly records all state transitions with timestamps

---

## Measurements To Record

| Measurement | How |
|-------------|-----|
| Order creation time | Time from starting the form to order saved |
| Color-up time | Time from opening editor to saving a complete color-up |
| Proof generation time | Time from "Save & Mark Proof Ready" to proof image displayed |
| End-to-end time | Total time from order entry to approval (for a simple 4-stop design) |
| Click count | Number of clicks/interactions for the complete workflow |
| Data integrity | Do all 5 test orders maintain correct state through all transitions? |
| Rejection round-trip | Time to: reject → revise color-up → re-generate proof → re-approve |
| Team feedback | Overall workflow impression from embroidery team (informal testing) |
| Bottleneck | Which step is slowest or most awkward? |

---

## Test Scenarios

### Scenario 1: Happy Path
Simple 2-color logo on a black polo. Create order → color-up → proof → approve. Should be straightforward.

### Scenario 2: Multi-Color Design
4+ color logo on a white polo. More stops to assign, tests editor with more complex designs.

### Scenario 3: Rejection & Revision
Create order → color-up → proof → reject with feedback ("gold needs to be darker") → revise color-up → new proof → approve. Tests the rejection loop.

### Scenario 4: Save Draft & Resume
Start a color-up, save as draft (partially complete), close the browser, reopen, continue the color-up. Tests data persistence.

### Scenario 5: Five Orders in Flight
Create 5 orders at different stages simultaneously. Verify the dashboard correctly shows all statuses and no data cross-contamination.

---

## Implementation Plan

### Step 1: Data Layer
- Choose storage approach (evaluate during build, recommend in deliverables)
- Set up database schema / file structure
- Build order CRUD functions
- Build state machine with transition validation and audit logging

### Step 2: Order Entry & Dashboard
- Order entry form (HTML form or HTMX-powered)
- DST file upload with parse validation (verify it's a valid DST, extract metadata)
- Dashboard page with status badges and action buttons
- File storage for uploaded DSTs

### Step 3: Integrate Color-Up Editor
- Embed POC 3 editor within the workflow
- Pass order context (customer, garment, instructions) to the editor
- Wire "Save & Mark Proof Ready" to the state machine
- Wire "Save Draft" to persist in-progress color-ups

### Step 4: Proof Preview Page
- Generate proof image using POC 1 renderer with POC 3's assigned colors
- Build the proof preview layout (design image + order details + thread summary)
- Wire "Send for Approval" to state transition and approval link generation

### Step 5: Approval Page
- Build the standalone approval page (clean, professional layout)
- Implement approve action (state → Approved)
- Implement reject action (capture feedback text, state → Rejected)
- Wire rejection back to "Revise Color-Up" on dashboard

### Step 6: Testing & Evaluation
- Run all 5 test scenarios
- Record measurements
- Get team feedback
- Write framework/storage comparison
- Write design recommendation

---

## Deliverables

1. Web application with all 5 pages/views functional
2. Demo walkthrough of 5 test orders through the complete workflow
3. Framework comparison scorecard (FastAPI+HTMX vs. FastAPI+React vs. Flask)
4. Storage comparison scorecard (SQLite vs. PostgreSQL vs. JSON)
5. Audit trail sample showing state transitions for test orders
6. Team feedback notes
7. **Design recommendation document:** Tech stack, architecture patterns, and data model for the full application build

---

## Estimated Effort

2-3 sessions with Claude

## Dependencies

- **POC 1 (DST Renderer)** — Need the winning rendering approach for proof generation
- **POC 2 (Thread Catalogue)** — Need the Madeira catalogue for the color picker
- **POC 3 (Color-Up Editor)** — Need the working editor to embed in the workflow

## Risk

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Integration friction between POC 1/2/3 components | **Medium** — delays assembly | Medium | Standardize on JSON data formats between components from the start |
| Workflow state bugs (stuck orders, lost data) | **Medium** — unreliable system | Low | State machine with validation + audit trail catches issues early |
| Proof image quality not professional enough | **Medium** — approval page looks amateur | Medium | Focus on clean layout; the design rendering quality was validated in POC 1 |
| Team finds the workflow adds steps vs. current process | **High** — adoption concern | Medium | Identify where the tool saves time (color-up record, reusability) vs. where it adds steps; optimize in full app |

---

## Reference Documents

- [POC PRD: Coloring Up Engine](./POC_PRD_Coloring_Up_Engine.md) — Parent PRD
- [POC 1: DST Renderer](./POC_1_DST_Renderer.md) — Prerequisite
- [POC 2: Thread Catalogue](./POC_2_Thread_Catalogue.md) — Prerequisite
- [POC 3: Color-Up Editor](./POC_3_Color_Up_Editor.md) — Prerequisite
- [PRD: Coloring Up Order Management](./PRD_Coloring_Up_Order_Management.md) — Full application scope (post-POC)
- [Trim Sheet Examples/](./Trim Sheet Examples/) — Current production documents for reference
