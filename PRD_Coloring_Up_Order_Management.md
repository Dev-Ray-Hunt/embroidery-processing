# Coloring Up: Order Management & Approval System

## Product Requirements Document — Phase 1

---

## Executive Summary

This document defines the requirements for building a **Coloring Up order management and approval system** for Straight Down's embroidery operation. The system manages the workflow from receiving an embroidery order through color selection, internal review, customer proof approval, and production release.

**Scope clarification:** This system does **not** generate embroidery files (DST/stitch files). Embroidery digitizing remains a separate process handled by existing tools and/or third-party digitizers. This system focuses entirely on the **order lifecycle** — managing the coloring-up process, generating visual proofs, obtaining approvals, and tracking orders through to production.

**Problem Statement:** Today, the coloring-up process at Straight Down involves manual coordination — tracking which orders need color selection, which proofs have been sent, which customers have approved, and which are ready for production. This creates bottlenecks, lost context, and delays. This system replaces that with a structured, trackable workflow.

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Primary language** | Python 3.10+ (backend) |
| **Frontend** | HTML/CSS/JS (web-based interface) |
| **Thread brand** | Madeira (Classic Rayon 40, Polyneon) |
| **Target machines** | Barudan embroidery machines via BNet software |
| **Existing systems** | NetSuite (order management), Microsoft stack (email/calendar) |
| **Priority** | 1. Reliability → 2. Usability → 3. Speed → 4. Flexibility |

---

## Core Workflow

The system supports the following end-to-end workflow:

```
Order Received → Color-Up Assignment → Thread Color Selection → Internal Review
    → Trim Sheet Generation → Proof Generation → Customer Approval → Production Release
```

### Workflow States

| State | Description | Who Acts |
|-------|-------------|----------|
| **New** | Order entered into the system with artwork/design reference | System / Operator |
| **Color-Up In Progress** | Team member is selecting thread colors for each design region | Embroidery Team |
| **Internal Review** | Color-up complete, awaiting internal sign-off before sending to customer | Team Lead / Manager |
| **Proof Sent** | Visual proof emailed to customer for approval | System (automated) |
| **Customer Approved** | Customer has approved the proof | Customer |
| **Customer Rejected** | Customer has rejected the proof with feedback | Customer |
| **Revision In Progress** | Team is revising the color-up based on customer feedback | Embroidery Team |
| **Production Ready** | Approved and queued for production | System |
| **In Production** | Currently being stitched | Operator |
| **Complete** | Order finished | Operator |

---

## Module 1: Order Management

### What It Does

Central hub for all embroidery orders. Captures order details, tracks status, and provides a dashboard view of the entire pipeline.

### Requirements

**Order Entry:**
- Select an existing customer or create a new one
- Enter order/PO number and link to NetSuite sales order (optional)
- Add line items — each line item is a garment style (style number, name, color, size quantities)
- Assign a logo + color-up to each line item (or group of line items). A single order may have multiple logos (e.g., left chest logo + sleeve logo) and each logo may need a different color-up depending on the garment color
- If an approved color-up exists for the logo/product combination, auto-select it; if not, flag the line item as needing a new color-up
- Enter placement, special instructions, due date, and priority

**Order Dashboard:**
- View all orders filtered by status, customer, date range, or assigned team member
- At-a-glance status indicators showing where each order sits in the workflow
- Priority flagging for rush orders
- Search by order number, customer name, or PO number

**Order History:**
- Full audit trail of status changes with timestamps and who made the change
- Attached files versioned (original artwork, revised proofs, etc.)
- Notes/comments thread per order for internal team communication

### Data Model

The data model is built around a key hierarchy: **Customers own Logos, Logos have approved Color-Ups per Product, and Orders reference all three.** This means once a logo is colored up and approved for a specific product (e.g., "Alpha Omega logo on a black polo"), that approved color-up is reusable on future orders — no need to re-do the color selection work.

```
Customer
  ├── Approvers (people who can approve proofs for this customer)
  ├── Logo A
  │     ├── Approved Color-Up: Black Polo (thread sequence for dark garments)
  │     ├── Approved Color-Up: White Polo (thread sequence for light garments)
  │     └── Approved Color-Up: Navy Hat (thread sequence for caps)
  └── Logo B
        └── Approved Color-Up: Black Jacket
```

**Customer**

| Field | Type | Notes |
|-------|------|-------|
| `customer_id` | Auto-generated | Internal unique ID |
| `customer_name` | String | Account name (e.g., "Alpha Omega Winery") |
| `netsuite_account_id` | String (optional) | Link to NetSuite customer record |
| `address` | Text | Ship-to / primary address |
| `notes` | Text | General notes about this customer's preferences |
| `created_at` | Datetime | When the customer was added |

**Customer Approver** (people authorized to approve proofs for a customer)

| Field | Type | Notes |
|-------|------|-------|
| `approver_id` | Auto-generated | Internal unique ID |
| `customer_id` | FK → Customer | Which customer this approver belongs to |
| `name` | String | Approver's name |
| `email` | String | For proof delivery |
| `phone` | String (optional) | Contact phone |
| `is_primary` | Boolean | Primary contact gets proofs by default |
| `active` | Boolean | Can be deactivated without deleting |

**Logo** (a design/artwork file belonging to a customer)

| Field | Type | Notes |
|-------|------|-------|
| `logo_id` | Auto-generated | Internal unique ID |
| `customer_id` | FK → Customer | Which customer owns this logo |
| `design_number` | String | e.g., "000001767-091" — the Wilcom/digitizer file reference |
| `logo_name` | String | Friendly name (e.g., "Alpha Omega Main Logo", "AO Text Only") |
| `artwork_files` | File[] | Original artwork (PNG, JPG, SVG, PDF) |
| `dst_files` | File[] | Digitized embroidery files |
| `wilcom_data` | JSON (optional) | Parsed Wilcom production worksheet data (stitch count, dimensions, stops, etc.) |
| `placement_default` | Enum (optional) | Default placement if this logo is almost always in the same spot |
| `notes` | Text | Notes about this logo (e.g., "Customer is picky about the gold shade") |
| `active` | Boolean | Logos can be retired without deleting |
| `created_at` | Datetime | When the logo was added |

**Color-Up** (an approved thread color configuration for a logo on a specific product)

| Field | Type | Notes |
|-------|------|-------|
| `colorup_id` | Auto-generated | Internal unique ID |
| `logo_id` | FK → Logo | Which logo this color-up is for |
| `product_type` | String | Product this color-up applies to (e.g., "Black Polo", "White Jacket", "Navy Hat") |
| `thread_sequence[]` | JSON | Ordered list: stop #, needle #, thread code, thread name, chart/brand |
| `status` | Enum | Draft, Pending Approval, Approved, Retired |
| `approved_by` | String (optional) | Who approved this color-up (customer approver name) |
| `approved_at` | Datetime (optional) | When it was approved |
| `version` | Integer | Version number (increments on revision) |
| `notes` | Text | Notes specific to this color-up (e.g., "Customer wanted darker gold than standard") |
| `created_at` | Datetime | When this color-up was created |

**Order** (a specific sales order that references a customer, logo, and color-up)

| Field | Type | Notes |
|-------|------|-------|
| `order_id` | Auto-generated | Internal unique ID |
| `customer_id` | FK → Customer | Which customer placed this order |
| `netsuite_order_number` | String (optional) | Link to NetSuite SO |
| `customer_po` | String | Customer PO number |
| `status` | Enum | See workflow states above |
| `priority` | Enum | Normal, Rush |
| `assigned_to` | String | Team member doing the color-up |
| `order_date` | Date | When the order was placed |
| `due_date` | Date (optional) | When the order needs to ship |
| `special_instructions` | Text | Free-form notes from customer or sales |
| `created_at` | Datetime | Order entry timestamp |

**Order Line Item** (garment styles with assigned logos and color-ups)

| Field | Type | Notes |
|-------|------|-------|
| `line_item_id` | Auto-generated | Internal unique ID |
| `order_id` | FK → Order | Which order this line belongs to |
| `style_number` | String | e.g., "14728-BLK" |
| `style_name` | String | e.g., "Olympic Polo" |
| `garment_color` | String | e.g., "Black" |
| `size_quantities` | JSON | Size grid: `{"S": 0, "M": 12, "L": 12, "XL": 0, ...}` |
| `total_units` | Integer (calculated) | Sum of all sizes for this line |
| `logo_id` | FK → Logo | Which logo is being embroidered on this line item |
| `colorup_id` | FK → Color-Up (optional) | Which approved color-up to use — null if new color-up needed |
| `placement` | Enum | Left Chest, Cap Front, Right Sleeve, etc. |

Note: Multiple line items can share the same logo and color-up (e.g., five different black garment styles all getting the same logo in the same colors). Line items can also have different logos (e.g., a left chest logo and a separate sleeve logo would be separate line item groupings).

### Key Workflow Implications

**New customer, new logo:** Full workflow — create customer, add approvers, upload logo, create color-up from scratch, get approval.

**Existing customer, new logo:** Create the logo under the existing customer, create a new color-up, get approval.

**Existing customer, existing logo, new product color:** The logo is already on file but needs a different color-up for a new garment color. Create a new color-up for that product, get approval.

**Repeat order:** Customer, logo, and approved color-up all exist. The order's line items get the existing approved color-up auto-assigned and can go straight to production — no color selection or approval needed. This is the speed win.

**Mixed order:** One order with multiple garment styles. Some line items (e.g., black polos) already have an approved color-up, others (e.g., white jackets, first time in white) need a new color-up. The system should handle both on the same order — approved lines move forward while new color-up lines go through the approval workflow.

---

## Module 2: Coloring Up Tool

### What It Does

The core of the system. Allows a team member to take a design and select specific Madeira thread colors for each region/element of the embroidery. This is where the creative and technical color decisions happen.

### Requirements

**Design Region Management:**
- Display the reference artwork/design for the order
- Allow the team member to define or identify distinct regions of the design (e.g., "text," "logo icon," "border," "background fill")
- Each region gets a thread color assignment

**Thread Color Selection:**
- Searchable Madeira thread catalogue (Classic Rayon 40 and Polyneon lines)
- Search by: color name, catalog number, or visual color browsing
- Color swatch display showing the selected thread color next to the design region
- Support for common color scenarios: match to PMS color, match to customer-provided color spec
- Track which thread colors are currently in stock / on the machines (future enhancement)

**Color-Up Sheet:**
- Summary view showing the full design with all regions and their assigned thread colors
- Printable/exportable format that can be used on the production floor
- Includes: Madeira catalog number, color name, and swatch for each region
- Machine setup reference: thread position assignments for the Barudan

**Thread Catalogue Database:**
- Madeira Classic Rayon 40 and Polyneon thread lines
- Fields: catalog number, color name, RGB value, color family/group
- Ability to mark threads as "in stock" or "frequently used"
- Ability to add custom/special order threads

---

## Module 3: Proof Generation & Approval

### What It Does

Generates a visual proof document showing the customer what their embroidery will look like, delivers it for approval, and tracks the response.

### Requirements

**Proof Document:**
- Combines the design artwork with the selected thread colors into a clear visual proof
- Shows: design preview, thread color callouts (Madeira number + color name + swatch), placement on garment, size reference
- Professional layout suitable for emailing to customers
- Generated as PDF or high-quality image (PNG)

**Proof Delivery:**
- Email proof to customer with approve/reject options
- Support for multiple approval contacts per order
- Customizable email template with Straight Down branding
- Track email delivery status (sent, opened if possible)

**Customer Response:**
- Simple approve/reject mechanism (email link or web page)
- If rejected: capture customer feedback/comments about what to change
- Rejection triggers the order back to "Revision In Progress" status
- Support for multiple revision rounds with version tracking

**Approval Tracking:**
- Dashboard view of all proofs awaiting customer response
- Age tracking: how long has each proof been waiting?
- Reminder capability: re-send proof or follow-up email after N days
- Approval history: who approved, when, which version

---

## Module 4: Trim Sheet Generation

### What It Does

Generates a consolidated **Trim Sheet** — the single production document that operators use on the floor. Today this information lives across two separate documents: a Wilcom Production Worksheet (design technical specs) and a Compact Trim Sheet from the existing system (order details, garment breakdown, thread sequence). This module combines both into one unified, printable document.

### Current State (What Exists Today)

Two separate documents are produced manually:

**Document 1 — Wilcom Production Worksheet** (generated from Wilcom EmbroideryStudio):
- Design number and barcode
- Design preview image (actual stitch rendering)
- Stitch count, dimensions (H × W), color count
- Machine format (Tajima), color changes, stops, trims
- Stabilizer requirements (topping/backing)
- Design extents (left/right/up/down in mm)
- Stitch statistics (max/min stitch, max jump, total thread/bobbin length)
- Stop sequence table: needle position, stitch count per stop, thread code, thread name, thread chart
- Estimated machine runtime

**Document 2 — Compact Trim Sheet** (generated from current VRLink/NetSuite system):
- Sales order number, customer name and address
- PO number, order date, ship date
- Design number and tape reference
- Design dimensions (H × W) and stitch count
- Thread color sequence (by stop number and thread code)
- Special instructions (placement, logo notes)
- Garment line items: style number, style name, color, sizes, and quantities per size
- Total unit count

### Requirements

**Combined Trim Sheet Template:**
- Single-page (or minimal pages) PDF that merges all critical info from both sources
- Header section: SO number, customer name, PO, order date, ship date
- Design section: design number, preview image, dimensions, stitch count, color count
- Thread sequence section: stop-by-stop thread assignment with Madeira catalog number, color name, and color swatch
- Production specs: machine format, stops, trims, stabilizer requirements, estimated runtime
- Garment breakdown: style number, style name, color, size grid with quantities, total units
- Special instructions: placement location, logo notes, any custom notes
- Footer: barcode for the design number, date generated, page count

**Data Sources:**
- Order data comes from Module 1 (order management)
- Thread color assignments come from Module 2 (coloring up tool)
- Design technical data is imported from Wilcom Production Worksheet (parsed from PDF or exported data)
- Garment/SKU line items come from the sales order (manual entry initially, NetSuite integration later)

**Template Configurability:**
- Configurable layout — the team should be able to adjust what sections appear and in what order
- Support for different trim sheet variants (e.g., compact vs. detailed)
- Straight Down branding (logo, fonts, colors)
- Printable on standard letter paper (8.5" × 11")

**Garment Line Item Management:**
- Enter garment styles with: style number, style name, color, and per-size quantities
- Size grid supports standard apparel sizes (XS, S, M, L, XL, 2X, 3X, etc.)
- Auto-calculate total units across all styles and sizes
- Support multiple garment styles per order (as shown in the current trim sheet — e.g., polos, jackets, vests on one order)

**Wilcom Data Import:**
- Parse Wilcom Production Worksheet PDFs to extract: stitch count, dimensions, stop sequence, thread codes, runtime, stabilizer info
- Alternatively, accept manual entry of these fields if PDF parsing proves unreliable
- Store parsed design data so it doesn't need to be re-imported for repeat designs

### Trim Sheet Data Model

| Field | Source | Notes |
|-------|--------|-------|
| `so_number` | Order / NetSuite | Sales order number |
| `customer_name` | Order | Account name |
| `customer_address` | Order | Ship-to address |
| `po_number` | Order | Customer PO |
| `order_date` | Order | Date order placed |
| `ship_date` | Order | Required ship date |
| `design_number` | Design file | e.g., 000001767-091 |
| `design_preview` | Wilcom / uploaded image | Visual of the design |
| `height` | Wilcom | Design height in inches |
| `width` | Wilcom | Design width in inches |
| `stitch_count` | Wilcom | Total stitches |
| `color_count` | Wilcom | Number of thread colors |
| `machine_format` | Wilcom | e.g., Tajima |
| `stops` | Wilcom | Number of stops |
| `trims` | Wilcom | Number of trims |
| `stabilizer_topping` | Wilcom | Topping type |
| `stabilizer_backing` | Wilcom | Backing type (e.g., Tear Away x 2) |
| `machine_runtime` | Wilcom | Estimated runtime (hr:min:sec) |
| `thread_sequence[]` | Color-up / Wilcom | Ordered list: stop #, needle #, stitch count, thread code, thread name, chart |
| `special_instructions` | Order | Placement, logo notes, custom instructions |
| `garment_lines[]` | Order / NetSuite | Style #, name, color, size quantities |
| `total_units` | Calculated | Sum of all garment quantities |

---

## Module 5: Production Handoff

### What It Does

Once approved, prepares the order for production by packaging all the information the machine operator needs — centered around the Trim Sheet.

### Requirements

**Production Packet:**
- Generated Trim Sheet (Module 4) — the primary production document
- Approved proof document (if applicable)
- DST file reference (if managed in the system)

**Production Queue:**
- View of all approved orders ready for production
- Sort/filter by due date, priority, customer
- Ability to mark orders as "In Production" and "Complete"
- One-click Trim Sheet print from the queue
- Basic production scheduling (assign to a machine or time slot — future enhancement)

**Completion Tracking:**
- Mark orders complete with optional notes
- Track completion date for reporting
- Close the loop on the order lifecycle

---

## Technical Architecture

### Recommended Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Backend** | Python + FastAPI | Fast to build, async support, good ecosystem |
| **Database** | SQLite (POC) → PostgreSQL (production) | Start simple, migrate when needed |
| **Frontend** | HTML + Tailwind CSS + Alpine.js or HTMX | Lightweight, no build step, fast to iterate |
| **Email** | Microsoft Graph API | Aligns with existing Microsoft stack |
| **File Storage** | Local filesystem (POC) → Cloud storage (production) | Start simple |
| **Auth** | Simple session-based (POC) → SSO (production) | Don't over-engineer early |

### API Structure

```
/api/orders          — CRUD for orders
/api/orders/{id}/colorup  — Color-up data for an order
/api/orders/{id}/proof    — Proof generation and delivery
/api/orders/{id}/approve  — Customer approval endpoint
/api/threads         — Thread catalogue management
/api/dashboard       — Dashboard/reporting data
```

---

## Build Phases

### Phase 1A: Foundation (Build First)

**Goal:** Get the core data model and order tracking working.

- Order CRUD (create, read, update, list)
- Basic dashboard with status filtering
- File upload for artwork and DST files
- Workflow state machine (status transitions with validation)
- Thread catalogue database (import Madeira data)
- Garment line item entry (style, color, size grid, quantities)

### Phase 1B: Coloring Up (Build Second)

**Goal:** The actual color selection workflow.

- Thread color search and selection UI
- Design region definition and color assignment
- Color-up sheet generation (printable summary)
- Internal review workflow

### Phase 1C: Trim Sheet Generation (Build Third)

**Goal:** The consolidated production document.

- Wilcom Production Worksheet PDF parser (extract design specs, stop sequence, runtime)
- Combined trim sheet template (order info + design specs + thread sequence + garment breakdown)
- Configurable template layout
- PDF generation with design preview image, color swatches, and size grids
- Print-ready output (8.5" × 11")

### Phase 1D: Proof & Approval (Build Fourth)

**Goal:** Customer-facing proof workflow.

- Proof document generation (PDF/image)
- Email delivery via Microsoft Graph API
- Customer approve/reject web page
- Approval tracking dashboard
- Revision round management

### Phase 1E: Production Handoff (Build Fifth)

**Goal:** Close the loop from approval to production floor.

- Production queue with one-click trim sheet printing
- Completion tracking
- Basic reporting (orders completed, average turnaround time)

---

## Future Enhancements (Out of Scope for Phase 1)

These are documented for context but are **not** part of the initial build:

- **NetSuite integration** — Pull order data automatically, push status updates back
- **Embroidery file generation** — Auto-generate DST files from artwork (see Blue Sky Archive for original POC plans)
- **Stitch preview rendering** — Realistic thread-level preview of what the embroidery will look like
- **BNet integration** — Send approved DSTs directly to Barudan machines
- **Inventory tracking** — Track thread inventory and flag when colors are running low
- **Customer portal** — Self-service portal where customers can view all their orders and proofs
- **Analytics/reporting** — Detailed production metrics, turnaround time trends, rejection rate analysis
- **Multi-location support** — If embroidery operations expand to multiple facilities

---

## Success Criteria

The Phase 1 build is successful if:

1. **Orders are trackable** — Every embroidery order has a clear status visible on the dashboard
2. **Color-up is documented** — Thread color selections are recorded with Madeira catalog numbers, not just verbal/memory
3. **Trim sheets are generated** — A single consolidated trim sheet replaces the current two-document workflow (Wilcom worksheet + VRLink trim sheet)
4. **Proofs reach customers** — Visual proofs are generated and emailed without manual document assembly
5. **Approvals are tracked** — Clear record of who approved what and when, no more chasing approvals verbally
6. **Production has what it needs** — Machine operators have a complete, printed trim sheet for every order
6. **Team adoption** — The embroidery team actually uses the system for daily work within 2 weeks of launch

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Thread catalogue RGB data inaccurate | Medium — color swatches misleading | Medium | Validate against physical spools, allow manual correction |
| Team doesn't adopt the tool | High — system becomes shelfware | Medium | Build with the team, keep it simple, make it faster than current process |
| Email deliverability issues | Medium — proofs don't reach customers | Low | Use Microsoft Graph (existing infrastructure), test thoroughly |
| Proof document quality insufficient | Medium — unprofessional customer experience | Low-Medium | Iterate on template design with team feedback |
| Wilcom PDF parsing unreliable | Medium — manual data entry fallback | Medium | Build manual entry as primary, PDF parsing as convenience; test against variety of Wilcom exports |
| Scope creep into file generation | Medium — delays core delivery | Medium | Strict Phase 1 boundary, Blue Sky Archive preserves future plans |

---

## Appendix: Relationship to Blue Sky Archive

The `Blue Sky Archive/` folder contains the original PRD and POC documents for a more ambitious system that included automated embroidery file generation (DST creation from artwork). That work remains valuable for future phases but was descoped to focus on the most immediate business need: managing the coloring-up workflow and approval process.

Key archived documents:
- `POC_PRD_Embroidery_Engine.md` — Original full-scope PRD
- `POC_1` through `POC_8` — Individual proof-of-concept specifications
- `Embroidery_File_Generation_Deep_Research.md` — Technical research on embroidery file formats and algorithms
