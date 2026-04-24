# POC 8: Lightweight Order Workflow

## Proof of Concept — Project Requirements Document

---

## Objective

Prove that the embroidery engine can be wrapped in a basic order-driven workflow: receive an order with artwork, generate a proof, email it for approval, and track the approval status.

## Why This Is Last

This is the lowest-risk POC — it's standard web application development. The business logic is straightforward. But it validates that the technical engine can be embedded in a production business workflow.

---

## Global Constraints

| Constraint | Value |
|-----------|-------|
| **Builder** | Brandon + Claude/AI agents |
| **Primary language** | Python 3.10+ (backend/engine) |
| **Frontend** | HTML/CSS/JS (where visualization is needed) |
| **Target machine** | Barudan embroidery machines via BNet software |
| **Evaluation priority** | 1. Reliability → 2. Quality → 3. Speed → 4. Flexibility |

### Evaluation Scoring Framework

Every bake-off option is scored on four dimensions using a 1-5 scale:

| Score | Reliability | Quality | Speed | Flexibility |
|-------|------------|---------|-------|-------------|
| **5** | Works 100% of the time, no edge-case failures | Indistinguishable from hand-digitized | < 5 seconds | Every parameter is tunable |
| **4** | Works 95%+ with known, manageable edge cases | Professional quality, minor imperfections | 5-30 seconds | Most parameters tunable |
| **3** | Works 80%+ with occasional failures | Acceptable for production, noticeable vs hand-digitized | 30s - 2 min | Key parameters tunable |
| **2** | Works 50-80%, frequent failures need workarounds | Functional but visibly automated | 2-10 min | Limited tunability |
| **1** | Unreliable, < 50% success rate | Not production-worthy | > 10 min | Essentially fixed |

**Weighted score formula:** `(Reliability × 4) + (Quality × 3) + (Speed × 2) + (Flexibility × 1)`

Maximum possible score: 50. Minimum viable for MVP selection: 30.

---

## What To Build

A simple web application with:

1. **Order entry form** — Customer name, order number, product type, artwork upload, placement instructions
2. **Auto-generation trigger** — On upload, run the embroidery pipeline (POC 7) to generate DST + preview
3. **Team review page** — Show generated preview, allow region adjustments, approve for customer
4. **Proof email** — Send proof image to customer email with approve/reject links
5. **Approval tracking** — Dashboard showing order status (pending / approved / rejected / in production)

---

## Bake-Off: Email/Notification Approach

| Option | Description |
|--------|-------------|
| **A. SMTP direct** | Send emails directly via Python `smtplib` |
| **B. SendGrid/Mailgun API** | Transactional email service for reliable delivery |
| **C. Microsoft Graph API** | Send via Outlook (aligns with existing Microsoft stack) |

## Bake-Off: Data Storage

| Option | Description |
|--------|-------------|
| **A. SQLite** | Simplest, file-based, zero setup. Good for POC. |
| **B. PostgreSQL** | Production-grade, ready for MVP without migration |
| **C. JSON flat files** | Absolute simplest for POC. Not scalable. |

---

## Future Integration Notes (Not POC Scope)

- **NetSuite integration:** Orders currently live in NetSuite. Future MVP will pull order data from NetSuite API or push approval status back. For the POC, order data is entered manually.
- **BNet dispatch:** Future MVP will send approved DSTs to BNet for machine dispatch. For POC, DST is downloaded manually and loaded via BNet's normal workflow.

---

## Pass/Fail Criteria

- [ ] Team member can enter an order and upload artwork
- [ ] System auto-generates preview and DST within 2 minutes
- [ ] Proof email is delivered to a test email address with preview image
- [ ] Customer can click "approve" in email and status updates in the dashboard
- [ ] Dashboard correctly shows all orders and their current status
- [ ] At least 5 test orders can be processed without data corruption

---

## Deliverables

1. Web application (Flask/FastAPI backend + simple HTML frontend)
2. Demo with 5 test orders through the complete workflow
3. Email template for customer proof approval
4. Comparison scorecard for email and storage approaches
5. **Design recommendation:** Tech stack for MVP workflow layer

---

## Estimated Effort

2-3 sessions with Claude

## Dependencies

- **POC 7 (End-to-End Integration)** must be complete — integrated pipeline

## Risk

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Email deliverability issues | **Low** — workaround with manual proof sending | Low | Tests multiple email approaches in bake-off |

---

## Reference Documents

- [Embroidery File Generation Deep Research Brief](./Embroidery_File_Generation_Deep_Research.md)
- [POC 7: End-to-End Integration](./POC_7_End_to_End_Integration.md) — prerequisite
