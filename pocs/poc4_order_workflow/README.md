# POC 4: Order-to-Approval Workflow

Spec: [../../POC_4_Order_Workflow.md](../../POC_4_Order_Workflow.md)

End-to-end local workflow: order entry → color-up → proof generation → approval page → status dashboard. No email integration, no NetSuite. Bake-offs on data storage (SQLite / Postgres / JSON files) and web framework (FastAPI + HTMX / FastAPI + React / Flask + Jinja).

**Status:** **blocked.** Depends on POC 3 (the editor is embedded in the workflow). When unblocking, write a `NEXT.md` defining the first task (likely: pick stack, scaffold web app, implement order entry page).
