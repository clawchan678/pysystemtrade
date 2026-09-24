# PYSYSTEMTRADE AUDIT

Audit of the public pysystemtrade repository. The master spec controls methodology.

At the start of every session:
1. Read PYSYSTEMTRADE_AUDIT_MASTER.md sections 0-32 and 51-56 (global rules, schema, stage-end rules).
2. Read only the sections for the current stage: P0 = 33-38, P1A = 39, P1B = 40, P2 = 41-50.
3. If audit_progress.md exists, read it and resume from its exact Next task. If it does not exist, this is the first session: begin Phase 1.
4. Read only the relevant current sections of pysystemtrade_audit.md.
5. Verify the repo HEAD SHA matches the SHA recorded in audit_progress.md.
6. Do not redo completed work unless resolving a contradiction.
7. Persistent state: pysystemtrade_audit.md, audit_progress.md, pysystemtrade_framework_inventory.csv.
8. Stop at the defined stage boundary (Phase 4 gate, then end of P0, P1A, P1B).

Never optimize, redesign, fix, or recommend changes to pysystemtrade. All execution stays in the scratch environment.
