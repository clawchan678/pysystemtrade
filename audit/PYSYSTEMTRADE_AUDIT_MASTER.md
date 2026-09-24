# PYSYSTEMTRADE — ARCHITECTURAL & METHODOLOGICAL AUDIT

## MASTER SPECIFICATION — CLAUDE CODE (BUDGET-OPTIMIZED FINAL)

---

## 0. PURPOSE

Perform a rigorous architectural and methodological audit of the public pysystemtrade repository.

The purpose is to determine:

- what the framework actually does,
- why its major layers exist,
- how information and state flow through the system,
- what assumptions each layer makes,
- where implementation differs from documentation,
- which components are specific to alpha generation,
- which components are structurally downstream of alpha,
- what the framework assumes about its trading-signal interface,
- which principles may be relevant to later swing and intraday futures analysis.

This is an AUDIT, not a development project.

Do NOT: optimize the framework; improve it; refactor it; redesign it; fix its bugs; optimize parameters; invent replacement methods; recommend adopting it; compare it with another trading architecture during P0/P1.

The final result must be an evidence-based baseline.

---

## 1. CENTRAL RESEARCH QUESTION

Answer:

> What research, estimation, portfolio, risk, execution, and validation framework does pysystemtrade actually contain beyond its individual trading rules, why does each layer exist, what assumptions does it make, what does the implementation actually do, where does implementation differ from documentation, and which underlying principles may be relevant to swing and intraday futures?

A key thought experiment:

> If the underlying trading signal were completely replaced with another signal, which parts of pysystemtrade would remain structurally usable?

This question MUST be evaluated relative to the Signal Contract established in Phase 4.

The signal-swap analysis is counterfactual. Do not treat a hypothetical signal replacement as an observed implementation fact.

Do not perform final transfer conclusions until P2.

---

## 2. AUDIT BOUNDARY

Audit pysystemtrade only.

Do not inspect or compare against: the user's private trading systems, another futures research repository, another trading architecture, prior user projects, or external implementations — unless explicitly instructed later.

The comparison against another futures architecture is a separate later task.

---

## 3. REPOSITORY TARGET AND PROVENANCE

Use this official repository URL:

https://github.com/pst-group/pysystemtrade

The current public repository is under the pst-group GitHub organization, and its README currently describes its history, including a January 2026 move to that organization. However, do NOT treat the repository location, default branch, or other repository metadata as an audit premise merely because this specification says so.

At the beginning of Phase 1, independently verify and record in `audit_progress.md`:

- the repository URL resolves to the intended public project,
- the default branch reported by Git/GitHub,
- the branch actually checked out,
- the repository HEAD SHA,
- the README's stated project history/location.

### Branch rule

This specification does NOT prescribe the branch. Use the repository's actual default branch as reported by Git/GitHub unless there is a documented reason to audit another branch.

- If the reported default branch conflicts with an operator-specified branch, STOP and ask the operator.
- If the README or repository identity materially conflicts with the intended audit target, STOP and ask the operator.
- Do not silently reconcile discrepancies.

### Version pinning

Once the target branch is verified: clone the repository into the scratch workspace, check out the verified audit branch, record the exact HEAD SHA and audit date/time, and pin the audit to that SHA.

Do not silently switch commits. If the branch advances during the audit, continue auditing the originally recorded SHA unless the operator explicitly authorizes a new audit revision.

---

## 4. FOUR-LAYER ARCHITECTURE

Classify major components into:

**ALPHA** — Components directly involved in generating or transforming trading forecasts/signals. Examples where present: trading rules, raw signals, forecast generation, forecast scaling, forecast caps, forecast combination.

IMPORTANT: The layer label records pipeline position. It does NOT by itself determine whether a component is signal-specific. For example, forecast scaling, caps, and combination may sit in the Alpha portion of the pipeline while still being structurally reusable when a replacement signal satisfies the required downstream contract. Do not infer signal independence from the layer label.

**RESEARCH** — Machinery used to estimate, calibrate, validate, or configure quantities. Examples: volatility estimation, correlations, forecast scalars, costs, historical statistics, parameter estimation.

**PORTFOLIO_RISK** — Machinery converting forecasts into portfolio exposure. Examples: position sizing, instrument weights, diversification, IDM, FDM, risk targeting, portfolio construction, buffering, capital allocation.

**EXECUTION** — Machinery converting portfolio decisions into trading activity. Examples: order generation, broker interaction, fills, costs, reconciliation, position state, live operation.

**CROSS_LAYER** — Use only where a component genuinely spans multiple layers. Explain why.

---

## 5. WORKING DEFINITIONS FOR FUTURE TRANSFER ANALYSIS

These definitions apply only to P2. They are not claims about any particular user's system.

**Swing** — Multi-day holding periods where decisions are made no more frequently than once per trading day using daily-or-slower decision data. Execution may use finer data.

**Intraday** — Positions normally opened and closed within a trading session, with decisions made on sub-daily data such as 1-minute to 5-minute bars or ticks for liquid futures such as ES/NQ/YM.

---

## 6. SOURCE OF TRUTH

The audited repository commit is the primary source of truth.

If documentation and implementation disagree: identify the documentation claim, identify the implementation, record the divergence, and do not silently reconcile them.

The repository's own `docs/` directory is a valid source for DOCUMENTED evidence. External documentation may be used only when explicitly necessary and must be clearly identified.

Do not treat remembered knowledge, prior conversations, blogs, books, or general knowledge as repository evidence.

---

## 7. WORKSPACE BOOTSTRAP

The operator creates the persistent audit workspace BEFORE launching Claude Code. The workspace already contains:

```
<workspace>/
├── PYSYSTEMTRADE_AUDIT_MASTER.md
└── CLAUDE.md
```

Claude Code must NOT create the master specification. Claude Code may create the remaining audit artifacts after startup.

Preferred final workspace:

```
<workspace>/
├── PYSYSTEMTRADE_AUDIT_MASTER.md
├── CLAUDE.md
├── repo/
├── venv/
├── scaffolding/
├── pysystemtrade_audit.md
├── audit_progress.md
└── pysystemtrade_framework_inventory.csv
```

---

## 8. PERSISTENCE MODE

The operator establishes the persistence mode before launching Claude Code.

- **MODE A — LOCAL TERMINAL:** the workspace exists on a persistent local filesystem.
- **MODE B — WEB / NON-PERSISTENT CLAUDE ENVIRONMENT:** the workspace must be backed by persistent storage or a private audit repository. The pysystemtrade clone should be gitignored inside the private audit repository unless explicitly intended otherwise.

Claude Code must NOT attempt to determine whether the environment will persist across future sessions. Persistence mode is an operator-controlled assumption.

---

## 9. ORIGINAL REPOSITORY SAFETY

If the user has no local pysystemtrade checkout, use the fresh clone created in the scratch workspace.

If a user-owned local checkout exists: treat it as read-only, do not modify it, do not install into it, do not run mutation commands against it.

The fresh audit clone is the authoritative source for this audit. Never modify a user-owned original checkout.

---

## 10. NO UNSAFE EXECUTION

Never: place live trades; submit broker orders; modify/cancel orders; connect to production trading accounts; use production credentials; connect to production databases; connect to live broker services.

Live architecture must be audited statically unless a safe isolated test is explicitly justified.

Any external service used for testing must be local or disposable, credential-free, and confined to the scratch environment.

If an empirical test requires an unsafe external dependency: `NOT TESTED — SAFETY`.

---

## 11. ENVIRONMENT SETUP

Create a scratch virtual environment if execution requires one.

Keep generated caches, logs, `.egg-info`, `.pytest_cache`, `__pycache__`, build artifacts, and temporary test files inside the scratch workspace.

Where appropriate, prefer `PYTHONDONTWRITEBYTECODE=1` and `pytest -p no:cacheprovider`.

For any scratch execution, set `HOME` (and any data or config environment variables identified in the repository docs) to a directory under `scaffolding/`, and record the variables used in `audit_progress.md`. This prevents the framework from writing config or data outside the workspace.

### Environment setup budget

Allow at most TWO meaningful environment-setup attempts. An attempt includes dependency installation or substantive environment repair. Do not repeatedly debug dependencies.

If the environment cannot be made usable after two attempts: record the failure; mark empirical phases `BLOCKED — ENVIRONMENT`; continue static analysis; do not repeatedly retry installation.

Static source analysis remains the priority.

---

## 12. EVIDENCE CATEGORIES

Use exactly these categories:

- **VERIFIED** — Confirmed by source code, controlled execution, tests, or reproducible inspection.
- **DOCUMENTED** — Explicitly stated in repository documentation actually inspected during this audit.
- **INFERRED** — Reasonable interpretation of verified implementation that is not explicitly established.
- **HYPOTHESIS** — Possible explanation or transfer idea that has not been demonstrated.
- **UNVERIFIED** — Evidence required to establish the claim is unavailable.

Never upgrade: HYPOTHESIS → VERIFIED; INFERRED → VERIFIED; remembered knowledge → DOCUMENTED.

---

## 13. COUNTERFACTUAL EVIDENCE

Signal-swap findings are counterfactual.

The fields `survives_if_contract_met` and `survives_if_contract_violated` describe what is inferred about a hypothetical replacement signal. They do NOT represent observed implementation evidence.

Their evidentiary status MUST be recorded separately in `swap_evidence`. Allowed values: `INFERRED`, `HYPOTHESIS`, `TESTED`, `UNVERIFIED`.

Use `TESTED` only when a controlled experiment actually evaluates the counterfactual. Do not label a hypothetical signal-swap conclusion VERIFIED merely because the underlying component itself is VERIFIED.

---

## 14. CLAIM DISCIPLINE

Do not describe anything as correct, robust, unbiased, look-ahead-free, production-equivalent, or statistically significant unless the evidence supports the claim.

Prefer "No causal violation was identified in the inspected implementation." over "The implementation is proven causal."

Do not confuse NO ISSUE IDENTIFIED with PROVEN CORRECT.

---

## 15. ABSENCE CLAIMS

Never conclude that a feature does not exist merely because it was not encountered.

For an absence claim, document: paths searched, symbols searched, documentation searched, relevant tests searched. If the search is insufficient: `UNVERIFIED`.

---

## 16. EVIDENCE FORMAT

Important findings should identify: file path; class/function/module; line range where practical; commit SHA; evidence category; brief explanation.

Preferred format:

```
path/to/file.py:120-168 @ abc1234
VERIFIED
```

Do not rely solely on class names, variable names, comments, or docstrings. Inspect implementation and relevant callers/callees where necessary.

---

## 17. RESOURCE AND TOKEN DISCIPLINE

This audit is conducted with a finite Claude Code budget. The goal is maximum methodological value per unit of compute and context.

Do not maximize the number of files inspected merely to appear comprehensive.

When resources are constrained: preserve architecture; preserve the Signal Contract; preserve state/estimation analysis; preserve forecast/portfolio/risk analysis; preserve critical causality work; reduce Tier 2 prose; cut optional phases before core methodology.

If a stage exceeds its operator-defined budget: stop expanding Tier 2 cards; mark remaining Tier 2 work `PARTIALLY AUDITED`; preserve Tier 1 analysis; continue only if the operator authorizes additional spend.

---

## 18. OPERATOR BUDGET PLAN

The operator should establish approximate budget ceilings before starting. Starting planning allocation (ceilings, not exact dollar predictions):

| Stage | Share |
|---|---|
| P0 | 35% |
| P1A | 40% |
| P1B | 15% |
| Reserve / contingency | 10% |

At every stage boundary: inspect available Claude Code usage/cost information; compare actual usage against the stage ceiling; record operator-reported usage in `audit_progress.md`; decide whether to continue, reduce scope, or stop.

Claude Code must NOT fabricate account-level dollar usage.

If the operator reports budget pressure: drop Tier 2 prose first. Do NOT sacrifice the Signal Contract, Tier 1 components, architecture, state/estimation analysis, or core portfolio methodology before reducing Tier 2 or optional work.

---

## 19. MODEL STRATEGY

Model selection is an operator decision. The operator should verify which models are available under the applicable credit/account.

General strategy: a cheaper capable model for reading-heavy repository mapping; a stronger model for difficult causal or architectural reasoning where necessary.

Do not hard-code a model name. Do not repeatedly switch models merely for experimentation.

---

## 20. READ-ONLY AND SCRATCH COMMAND DISCIPLINE

Prefer read-only repository inspection commands. Typical commands: `git status`, `git branch`, `git remote -v`, `git rev-parse HEAD`, `git symbolic-ref refs/remotes/origin/HEAD`, `git log`, `git show`, `git grep`, `rg`, `find`, `sed`, `head`, `tail`.

`git clone` and `git checkout` are permitted only to create and pin the scratch clone described in Section 3.

Controlled scratch execution may include `python` and `pytest`. These are NOT inherently read-only because they may write caches, artifacts, or files. Use them only inside the scratch environment with outputs confined to the scratch workspace.

Do not run destructive commands against the repository.

The operator may configure Claude Code permissions/allowlists in advance for common read-only commands and approved scratch commands. Do not modify permission settings automatically unless explicitly instructed.

---

## 21. SOURCE-INSPECTION STRATEGY

Prefer: repository tree; README; `docs/`; architecture documentation; entry points; symbol searches; callers/callees; targeted source ranges; relevant tests; execution only when execution adds evidence unavailable statically.

Avoid dumping entire large files into context when targeted ranges suffice. Do not repeatedly reread already-understood files unless resolving a contradiction. Do not run broad test suites merely to demonstrate activity.

---

## 22. EXPERIMENT DISCIPLINE

Before every empirical experiment, state: the exact methodological question; why static inspection cannot answer it; the smallest experiment capable of answering it; expected evidence; the stopping condition.

Prefer the smallest sufficient experiment. Do not run large historical backtests merely to confirm architecture. Do not perform parameter optimization or performance optimization.

---

## 23. PERSISTENT AUDIT FILES

Maintain exactly these three authoritative audit files:

- `pysystemtrade_audit.md`
- `audit_progress.md`
- `pysystemtrade_framework_inventory.csv`

Temporary scratch files may exist under `scaffolding/`. The three audit files are authoritative.

---

## 24. REPORT STRUCTURE

Create `pysystemtrade_audit.md` with these sections:

1. Audit Scope / Version / Provenance
2. Repository Architecture
3. System / Stage / Caching Architecture
4. Alpha / Research / Portfolio_Risk / Execution Decomposition
5. Signal Contract
6. Master Framework Inventory
7. pysystemtrade-Specific Framework Concepts
8. State and Estimation Audit
9. Dependency / Information Flow
10. Simulation / Backtest Architecture
11. Data / Contract / Roll Architecture
12. Forecast / Weight / Portfolio Methodology
13. Cost / Turnover / Buffering / Speed Limits
14. Configuration / Experiment Infrastructure
15. Static Causality / Look-Ahead Audit
16. Empirical Causality Testing
17. Position / Lag / P&L Timing
18. Degrees of Freedom / Research Safeguards
19. Testing / Validation Infrastructure
20. Live / Production Architecture
21. Swing Transfer Analysis
22. Intraday Transfer Analysis
23. Swing Operational Readiness
24. Master Inventory Views
25. Swing vs Intraday Transfer Matrix
26. Final Research Framework Synthesis
27. Open Questions / Evidence Gaps / Stage-2 Comparison Questions

Future sections may contain `NOT YET AUDITED`. Do not repeatedly rewrite untouched sections.

---

## 25. PROGRESS FILE

Maintain `audit_progress.md`. It must contain: workspace path; repository URL; verified repository identity; verified default branch; audited branch; repository commit; release/tag if applicable; audit date; persistence mode; environment status (including any environment variables set); completed phases; current phase; exact next task; unresolved issues; evidence gaps; empirical tests; estimation flags; scratch modifications; important findings; optional-phase status; operator-reported usage/cost when available; model used when useful.

This file is the authoritative resume state.

---

## 26. CLAUDE.MD

The workspace already contains a short `CLAUDE.md`. It should contain approximately:

```
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
```

CLAUDE.md is only a resume/behavior pointer. Do not duplicate this specification inside it. Do not instruct Claude Code to reread the entire master specification at every fresh session. If this specification is renumbered, update the section ranges in CLAUDE.md.

---

## 27. FRESH-CONTEXT WORKFLOW

At every major stage boundary: finish the stage; update all three authoritative audit files; verify the stage-end checklist; provide the stage summary; STOP.

Preferred workflow: start a fresh Claude Code context/session for the next stage. The new session must rediscover state from files rather than conversation history.

---

## 28. COMPONENT AUDIT TIERS

**TIER 1 — CORE COMPONENTS.** Approximately 15–20 components. Expected areas where present: System machinery; Stage machinery; caching/state machinery; trading-rule interface; forecast generation; forecast scaling; forecast cap; forecast combination; volatility estimation; correlation estimation; instrument weighting; FDM; IDM; position sizing; portfolio construction; risk targeting; buffering; transaction costs; speed limits; critical execution/position machinery. Tier 1 components receive a FULL COMPONENT CARD.

**TIER 2 — SECONDARY COMPONENTS.** All other components materially participating in the framework. For each: a CSV row; a two-to-four sentence note; an evidence reference; layer classification; alpha-specific status; a state/estimation flag where relevant.

**TIER 3 — PERIPHERAL COMPONENTS.** Utilities, wrappers, convenience helpers, or infrastructure that do not materially affect alpha, research, estimation, portfolio, risk, execution, or validation. Do not spend substantial budget on Tier 3.

---

## 29. FULL COMPONENT CARD

Only Tier 1 components require: component name; source path; class/function/module; layer; purpose; problem solved; failure mode prevented; inputs; outputs; mathematical formulation where applicable; configuration; update frequency; state; data dependencies; assumptions; alpha-specific status; signal-swap survivability; documented behavior; implemented behavior; documentation/implementation divergence; evidence.

For signal-swap survivability, also record: Case A reasoning; Case B reasoning; `swap_evidence`.

---

## 30. SIGNAL CONTRACT

This is a mandatory P0 finding.

Determine, entirely from pysystemtrade:

> What interface must a trading rule satisfy for forecast scaling, forecast combination, position sizing, and buffering to function?

Explicitly determine: object/data type; sign convention; numerical range where applicable; continuity/discreteness; timing; frequency; statefulness; missing-value behavior; index/time structure; instrument dimension; whether downstream stages expect forecasts or another object; assumptions imposed by downstream stages; whether forecasts are expected to be continuously available; how event-driven/discontinuous inputs would interact with downstream machinery.

The Signal Contract must be concrete. Avoid generic statements such as "the signal needs to be compatible with the system." Specify the observed contract as precisely as evidence allows.

Record it as "Signal Contract" in the report and inventory.

Do not compare it with an external system. Do not infer an external standard.

---

## 31. CONDITIONAL SIGNAL-SWAP ANALYSIS

Signal-swap survivability MUST be evaluated under two distinct hypothetical cases.

**CASE A — CONTRACT MET.** Replacement signal: a different signal that satisfies the observed pysystemtrade Signal Contract.

**CASE B — CONTRACT VIOLATED.** Replacement signal: a signal that violates the observed contract, such as a discrete, event-driven, path-dependent signal with its own entry/exit logic.

For every relevant component, in BOTH cases, determine whether it would: survive unchanged; survive with minor adaptation; survive partially; require redesign; become inapplicable; or remain unknown.

For both cases: state the reasoning; identify the dependency on the Signal Contract; distinguish implementation evidence from counterfactual inference; assign `swap_evidence`.

Do not present either case as an observed implementation. Do not label either case VERIFIED unless a controlled test actually evaluates the counterfactual.

---

## 32. MASTER INVENTORY

The canonical machine-readable inventory is `pysystemtrade_framework_inventory.csv`.

Schema:

| Field | Allowed Values |
|---|---|
| component_id | stable unique ID |
| path | source path/module/class/function |
| layer | ALPHA / RESEARCH / PORTFOLIO_RISK / EXECUTION / CROSS_LAYER |
| alpha_specific | Y / N / UNKNOWN |
| survives_if_contract_met | Y / N / PARTIAL / UNKNOWN |
| survives_if_contract_violated | Y / N / PARTIAL / UNKNOWN |
| contract_dependency | short text |
| swap_evidence | INFERRED / HYPOTHESIS / TESTED / UNVERIFIED |
| stateful | Y / N / UNKNOWN |
| doc_status | DOCUMENTED / NOT_DOCUMENTED / UNKNOWN |
| impl_evidence | VERIFIED / INFERRED / UNVERIFIED |
| divergence | Y / N / UNKNOWN |
| swing_transfer_label | approved vocabulary |
| intraday_transfer_label | approved vocabulary |
| last_phase | phase number |

`impl_evidence` describes the evidence for the actual component. `swap_evidence` describes the evidence for the counterfactual signal-swap conclusion. Do not use one as a substitute for the other.

**Mapping for `survives_if_contract_met` / `survives_if_contract_violated`** (from the six outcomes in Section 31):

- survive unchanged, or survive with minor adaptation → `Y`
- survive partially, or require redesign → `PARTIAL`
- become inapplicable → `N`
- cannot determine → `UNKNOWN`

Record the finer-grained verdict in `contract_dependency` or the component card.

Approved transfer vocabulary: `NOT YET ASSESSED`, `CONCEPTUALLY PORTABLE — UNTESTED`, `POTENTIALLY PORTABLE — REQUIRES REDESIGN`, `DAILY-DEPENDENT`, `TRANSFER NOT JUSTIFIED`.

Do not populate transfer labels before P2.

After each CSV update verify: the CSV parses; all rows have identical column counts; component IDs are unique; vocabulary values are valid.

---

## 33. P0 — FOUNDATION

P0 contains Phases 1–8. Phases 1–4 run first and end at the Phase 4 review gate (Section 34).

### PHASE 1 — PROVENANCE AND ENVIRONMENT

Record: repository URL; verified repository identity; default branch reported by Git/GitHub; audited branch; commit SHA; release/tag; Python version; relevant dependency versions; documentation version/date where identifiable; audit date; persistence mode; environment status.

Create: scratch repository; virtual environment if needed; report; progress file; CSV.

The master specification and CLAUDE.md already exist.

If environment setup fails after two attempts: `BLOCKED — ENVIRONMENT`. Continue static analysis where possible.

### PHASE 2 — REPOSITORY ARCHITECTURE

Map: data layer; ingestion; cleaning; price data; carry; FX; contracts; continuous futures; trading rules; raw forecasts; forecast scaling; forecast caps; forecast combination; volatility; position sizing; instrument weighting; portfolio construction; diversification; risk targeting; buffering; costs; accounting; P&L; simulation; backtesting; live architecture; broker integration; configuration; tests; logging; caching; persistence.

Identify: entry points; major data flows; strategy flow; simulation engine; portfolio engine; live engine; configuration system.

Use targeted inspection.

### PHASE 3 — SYSTEM / STAGE / CACHING

Determine: what a System represents; what a Stage represents; stage dependencies; information flow; lazy calculations; caching; cache invalidation; reproducibility implications; stale-state risks; research implications; live implications; reusable framework infrastructure.

This is Tier 1.

### PHASE 4 — FOUR-LAYER DECOMPOSITION + SIGNAL CONTRACT

Classify components into ALPHA, RESEARCH, PORTFOLIO_RISK, EXECUTION, CROSS_LAYER.

Then establish the Signal Contract (Section 30).

Then perform the conditional signal-swap analysis (Section 31): Case A (replacement satisfies the Signal Contract) and Case B (replacement violates it).

For each major component record: layer; alpha-specific status; contract dependency; `survives_if_contract_met`; `survives_if_contract_violated`; reasoning; `swap_evidence`; implementation evidence.

IMPORTANT: Layer position does not automatically determine signal dependence. A component can sit in the Alpha portion of the pipeline but be structurally reusable when a replacement signal satisfies the expected forecast contract.

---

## 34. MANDATORY PHASE 4 REVIEW STOP

Phase 4 is a hard review gate.

After Phase 4: update `pysystemtrade_audit.md`; update `audit_progress.md`; update and validate the CSV; verify the repository SHA; then summarize: the four-layer decomposition; the Signal Contract; Case A survivability; Case B survivability; major ambiguities; classification uncertainties; evidence quality.

Limit the gate summary to 20 bullets plus the layer table.

Then STOP. Do not begin Phase 5 until the operator explicitly reviews and approves the Phase 4 output.

### Operator review checklist

The operator should manually inspect three or four cited pieces of evidence and confirm:

- cited file/line ranges support the claims,
- the Signal Contract identifies concrete types/data structures,
- the Signal Contract identifies timing/frequency,
- Case B verdicts contain actual reasoning rather than labels,
- layer labels for forecast scaling, caps, and combination are defensible,
- counterfactual conclusions are not mislabeled as VERIFIED,
- `swap_evidence` is used correctly,
- actual Claude Code usage/cost is recorded.

If the Phase 4 output is materially wrong: correct the classification before continuing.

If budget usage is already high: reduce Tier 2 scope before approving Phase 5.

---

## 35. PHASE 5 — MASTER INVENTORY

After Phase 4 approval: populate the canonical CSV; assign component tiers; produce full cards only for Tier 1 components. Do not spend extensive prose on Tier 2/Tier 3 components.

If budget is constrained: reduce Tier 2 prose before reducing Tier 1 analysis.

---

## 36. PHASE 6 — PYSYSTEMTRADE-SPECIFIC FRAMEWORK CONCEPTS

Verify, rather than assume, the following where present: handcrafted vs optimized weights; pooling across instruments; forecast scalar / target / cap; FDM; IDM; volatility estimation and long-run blending; cost-based speed limits; buffering; integer/lumpy position handling; production overrides and limits.

For each: existence; location; function; documented behavior; implemented behavior; assumptions; evidence; component tier.

Deep causal testing belongs later.

---

## 37. PHASE 7 — STATE AND ESTIMATION

Identify important stateful/estimated quantities: volatility; correlations; weights; forecast scalars; forecast caps; FDM; IDM; costs; rolling statistics; expanding statistics; carry estimates; positions; account value; capital; buffers; risk estimates; execution state.

For important quantities record:

| Quantity | Source | Window | Update Frequency | Method | Available When | Rolling/Expanding/Fixed | OOS Behavior | Missing Data | Evidence |
|---|---|---|---|---|---|---|---|---|---|

Inspect: availability timing; future information; full-sample estimation; later recalculation; OOS contamination; warm-up; backfilling; adaptive degrees of freedom.

---

## 38. PHASE 8 — DEPENDENCY / INFORMATION FLOW

Trace:

```
DATA
→ DATA PROCESSING
→ TRADING RULE
→ RAW FORECAST
→ FORECAST SCALING
→ FORECAST CAP
→ FORECAST COMBINATION
→ VOLATILITY / RISK
→ INSTRUMENT WEIGHT
→ PORTFOLIO CONSTRUCTION
→ BUFFERING
→ COSTS
→ POSITION
→ EXECUTION
```

Correct the diagram wherever implementation differs.

For every major dependency determine: information passed; state passed; estimates passed; timing; causal availability; alpha-specific vs generic infrastructure.

### P0 STOP

Update all authoritative files. Validate the CSV. Verify the repository SHA. Provide a ≤20-bullet P0 summary. STOP.

---

## 39. P1A — CORE METHODOLOGY

P1A contains Phases 9–14. Priority order: Phase 11, Phase 12, Phase 9, Phase 14. Phase 10 is useful but lower priority.

### PHASE 9 — SIMULATION / BACKTEST ARCHITECTURE

Trace:

```
raw data → signal → forecast → portfolio → position → fill → cost → account → P&L → performance
```

Determine: time advancement; recalculation; caching; estimation; signal availability; position timing; fills; costs; account state; risk; P&L; reporting.

Classify the architecture: event-driven; daily-bar driven; vectorized; hybrid; stateful; stateless; other.

Identify assumptions relevant to higher-frequency transfer.

### PHASE 10 — DATA / CONTRACT / ROLL ARCHITECTURE

SECONDARY PRIORITY.

Inspect: data sources; continuous/adjusted data; multiple price series; roll calendars; contract handling; carry; FX; cleaning; missing data; instrument metadata; back-adjustment; roll effects on historical values.

Focus only on facts materially affecting causality, research, portfolio construction, execution, and transfer.

If budget becomes constrained, this is the FIRST P1A phase to reduce or skip. Record `SKIPPED — RESOURCE PRIORITY` if necessary.

### PHASE 11 — FORECAST / WEIGHT / PORTFOLIO METHODOLOGY

HIGH PRIORITY.

Deeply inspect: forecast generation; forecast scaling; forecast caps; forecast combination; FDM; position sizing; volatility targeting; instrument weights; IDM; correlations; portfolio construction.

For each major mechanism determine: formula; inputs; assumptions; estimation method; update frequency; rationale; documented behavior; implemented behavior; evidence.

Trace forecast → risk → position. Do not optimize.

### PHASE 12 — COST / TURNOVER / BUFFERING / SPEED LIMITS

HIGH PRIORITY.

Trace:

```
forecast/rule → desired position → turnover → transaction cost → portfolio decision
```

Determine: commissions; spread; slippage; market impact; instrument-specific costs; cost curves; cost influence; speed limits; buffering; turnover control; research/live consistency.

Identify assumptions that may change materially for intraday trading. Do not design replacements.

### PHASE 13 — CONFIGURATION / EXPERIMENT INFRASTRUCTURE

Determine: configurable components; strategy representation; instrument representation; portfolio representation; parameter storage; reproducibility; configuration versioning; code/config interaction; experiment comparison.

Keep targeted.

### PHASE 14 — STATIC CAUSALITY / LOOK-AHEAD

Inspect: future prices; same-day close leakage; volatility leakage; correlation leakage; weight leakage; forecast-scalar leakage; full-sample estimation; warm-up/backfill; OOS contamination; execution timing; cost timing; roll/back-adjustment effects.

Central question:

> If a position is established at time T, does any calculation determining it use information that becomes available only after T?

Classify each finding: `NO ISSUE IDENTIFIED`, `POSSIBLE ISSUE`, `CONFIRMED ISSUE`, `UNVERIFIED`. Use evidence.

Because Phase 15 empirical testing is optional, static findings must not be overstated. If only static evidence exists, distinguish NO ISSUE IDENTIFIED from VERIFIED CAUSAL.

### P1A STOP

Update the report, progress file, and CSV. Provide the stage summary. STOP.

---

## 40. P1B — VALIDATION

P1B contains Phases 15–19. It is lower priority than P0/P1A for the primary architectural objective.

If resources become constrained, cut in this order: Phase 19; Phase 10 if not already addressed; Phase 15 empirical depth; secondary validation. Preserve important static methodology findings.

### PHASE 15 — EMPIRICAL CAUSALITY

Attempt only where technically feasible and materially useful.

Before each test record: the exact question; why static inspection is insufficient; the smallest experiment; expected evidence. Confirm which estimation layers are enabled and record each relevant estimation flag (ON / OFF / UNKNOWN) in `audit_progress.md`.

Where appropriate perform: baseline determinism; small truncation tests; common cutoff tests; cross-sectional truncation tests. Where cross-sectional estimates exist, truncate all instruments at a common cutoff. Compare pre-cutoff outputs against full-history outputs.

Potential outputs: volatility; forecasts; scalars; caps; combinations; correlations; weights; FDM; IDM; positions; buffers.

Do not interpret every difference as leakage. Distinguish: legitimate rolling/expanding behavior; expected recalculation; methodological design; future-information leakage.

If environment setup is blocked: `BLOCKED — ENVIRONMENT`. Do not spend excessive budget forcing execution.

### PHASE 16 — POSITION / LAG / P&L TIMING

Trace a small representative sample. Prefer one ordinary date, one roll-related date if relevant, and one boundary condition if relevant.

Trace:

```
market data → signal → forecast → position → lag → fill → return → P&L
```

Determine: data timestamp; signal timestamp; position availability; lag; fill price; P&L price; same-day exposure; next-bar convention; documented vs implemented behavior.

Do not generalize beyond evidence.

### PHASE 17 — DEGREES OF FREEDOM / RESEARCH SAFEGUARDS

Inventory: trading-rule parameters; forecast parameters; scaling; caps; volatility windows; correlation windows; weighting; portfolio parameters; risk targets; buffering; costs; instrument selection; rule selection; adaptive behavior.

Classify each: fixed, estimated, optimized, heuristic, adaptive.

Inspect safeguards against: look-ahead; data snooping; repeated experimentation; parameter mining; strategy selection bias; instrument selection bias; date-range selection; regime selection; post-hoc methodology changes.

Inspect existing: sensitivity analysis; bootstrap; Monte Carlo; significance testing; robustness tooling.

Do not perform new optimization.

### PHASE 18 — TESTING / VALIDATION INFRASTRUCTURE

Inspect tests covering important: forecasts; volatility; weights; correlations; FDM; IDM; buffering; costs; data; rolls; simulation; configuration; live behavior; reproducibility; timing.

Run only safe and materially informative tests.

For important tests distinguish "What this proves" from "What this does not prove." Do not equate passing tests with methodological validity.

### PHASE 19 — LIVE / PRODUCTION ARCHITECTURE

OPTIONAL / LOW PRIORITY.

Perform static inspection only unless a safe isolated test is justified.

If resources are plentiful, inspect: research-to-live connection; shared/separate calculations; broker integration; order generation; position reconciliation; account state; persistence; restart behavior; monitoring; logging; overrides; limits; error handling.

If resources are constrained: `PARTIALLY AUDITED — RESOURCE PRIORITY`. Do not spend a large fraction of the audit budget recursively exploring large production subsystems.

### P1B STOP

Update the authoritative files. Provide the stage summary. STOP.

---

## 41. P2 — TRANSFER AND SYNTHESIS

P2 begins only after P0/P1 evidence is recorded.

P2 is primarily reasoning and synthesis over `pysystemtrade_audit.md`, `audit_progress.md`, and `pysystemtrade_framework_inventory.csv`.

P2 may be performed in a fresh Claude Code context, in another Claude session, or in another analytical environment.

Do not reopen large numbers of source files unless necessary to resolve a specific evidence gap. P2 is intentionally separable from Claude Code.

---

## 42. TRANSFER ANALYSIS RULE

For every transfer claim separate: PRINCIPLE; IMPLEMENTATION; ASSUMPTION; EVIDENCE; TRANSFER STATUS.

The existence of a concept in pysystemtrade does not prove that it should transfer. Do not turn transfer analysis into an endorsement.

---

## 43. APPROVED TRANSFER LABELS

Use only:

- **CONCEPTUALLY PORTABLE — UNTESTED** — The principle appears potentially independent of decision frequency, but transfer has not been demonstrated.
- **POTENTIALLY PORTABLE — REQUIRES REDESIGN** — The principle may transfer, but the existing implementation or assumptions require substantial modification.
- **DAILY-DEPENDENT** — The concept or implementation materially depends on daily/position-trading assumptions.
- **TRANSFER NOT JUSTIFIED** — Available evidence is insufficient to justify transfer.

These are classifications, not recommendations. Do not rank components.

---

## 44. PHASE 20 — SWING TRANSFER

For each major framework component determine: underlying principle; current implementation; assumptions; assumptions that survive swing frequency; assumptions that do not; evidence required.

Assign the approved swing transfer label.

---

## 45. PHASE 21 — INTRADAY TRANSFER

Separate:

- A. Timeframe-independent principles
- B. Daily-frequency assumptions
- C. Potentially portable but requiring redesign
- D. Transfer not justified

Inspect conceptually: volatility targeting; forecast scaling; forecast combination; correlation/diversification; signal vs position sizing; buffering; transaction costs; spread; slippage; market impact; latency; fill uncertainty; intrabar sequencing; partial fills; stops; targets; state requirements.

Do not design a replacement system.

---

## 46. PHASE 22 — SWING OPERATIONAL READINESS

Separate research/reference usability from live operational requirements.

Address: data; contracts; rolls; carry; FX; broker integration; instrument universe; diversification; capital; margin; micro contracts; leverage; storage; computation; monitoring; deployment.

Do not make adoption recommendations.

---

## 47. PHASE 23 — INVENTORY VIEWS

Generate views from the canonical CSV: Alpha-independent framework; Research/estimation framework; Portfolio/risk framework; Execution framework; Swing transfer; Intraday transfer.

For alpha-independent analysis explicitly perform the two signal replacement cases: Case A (replacement satisfies the Signal Contract) and Case B (replacement violates it). State why each component does or does not survive.

---

## 48. PHASE 24 — SWING VS INTRADAY MATRIX

Produce:

| Component | Current Implementation | Underlying Principle | Swing Transfer | Intraday Transfer | What Breaks | Evidence Needed |
|---|---|---|---|---|---|---|

Use only approved transfer labels. Do not rank.

---

## 49. PHASE 25 — FINAL SYNTHESIS

Answer, with evidence tags:

1. What is the actual conceptual architecture?
2. What is the alpha framework?
3. What is the research/estimation framework?
4. What is the portfolio/risk framework?
5. What is the execution framework?
6. What survives complete replacement of the trading signal when the replacement satisfies the Signal Contract?
7. What fails or changes when the replacement violates the Signal Contract?
8. What is daily/position-trading dependent?
9. What principles are conceptually portable to swing futures?
10. What principles are potentially portable to intraday futures?
11. Which implementations require redesign for intraday frequency?
12. Which assumptions are most important?
13. Which assumptions should not be transferred blindly?

Also produce:

| Framework Layer | Problem Solved | Failure Mode Prevented | Alpha-Specific? | Portfolio-Level? | Transferable Principle? | Evidence |
|---|---|---|---|---|---|---|

---

## 50. PHASE 26 — OPEN QUESTIONS

### Evidence Gaps

Classify unresolved questions as: unavailable source; unavailable data; unavailable dependency; untestable implementation; insufficient evidence; unresolved code ambiguity. Do not guess.

### Future Comparison Questions

Generate neutral questions that could later be asked of another futures research architecture. Example:

- Does the architecture have an equivalent of `<component>`?
- Where does it live?
- Is it separated from alpha generation?
- How is it estimated?
- When does the estimate become available?

Generate questions from the verified inventory. Do not inspect another system. Do not answer those questions.

---

## 51. EXECUTIVE SUMMARY

Maintain an Executive Summary in the report. Maximum 20 bullets.

Before P2, cover only: architecture; implementation; estimation; methodology; evidence gaps; documentation/implementation divergence; testing status.

Do not include transfer conclusions before P2. Update at stage boundaries.

---

## 52. STAGE-END CHECKLIST

Before stopping at a stage boundary verify:

- report updated,
- progress file updated with exact next task,
- CSV updated and validated,
- repository commit still matches,
- no unsafe/live action occurred.

---

## 53. STAGE-END RESPONSE

Provide no more than 20 bullets covering: completed stage; repository; verified branch; audited commit; version; major findings; major documentation/implementation divergences; important methodological findings; empirical tests completed; tests not completed and why; evidence gaps; current phase; exact next task; operator-reported usage/cost if available; absolute paths to `pysystemtrade_audit.md`, `audit_progress.md`, and `pysystemtrade_framework_inventory.csv`.

Then STOP. (The Phase 4 gate uses the format in Section 34.)

---

## 54. FINAL NON-NEGOTIABLE RULES

This is an evidence audit.

Do not: optimize pysystemtrade; optimize parameters; redesign the framework; fix repository bugs; invent evidence; use memory as repository evidence; claim absence without sufficient search; confuse no issue identified with proof; claim transferability without evidence; make performance claims about transfer; recommend adoption; rank components; invent trading rules; invent parameters.

If something cannot be established: `UNVERIFIED`.
If a test cannot be performed: `NOT TESTED — REASON`.
If environment setup fails after two attempts: `BLOCKED — ENVIRONMENT`.
If resources become constrained: preserve higher-value architectural work and explicitly mark lower-priority work incomplete.

---

## 55. PRIORITY IF THE $100 CREDIT BECOMES CONSTRAINED

**MUST COMPLETE:** Phase 1; Phase 2; Phase 3; Phase 4; Signal Contract; Case A signal-swap analysis; Case B signal-swap analysis; Phase 5; Phase 6; Phase 7; Phase 8; Phase 11; Phase 12.

**HIGH VALUE:** Phase 9; Phase 14; Phase 16; Phase 17; Phase 18.

**FIRST TO CUT:** Phase 19; Phase 10; deep Phase 15 empirical work; Tier 2 prose expansion; Tier 3 investigation.

If skipped: record `SKIPPED — RESOURCE PRIORITY` and what remains unverified.

P2 should primarily use the completed audit artifacts rather than spending large additional amounts of Claude Code budget reopening the repository.

---

## 56. SUCCESS CRITERION

The audit succeeds if it produces a reproducible, evidence-based baseline showing: what layers exist; what each layer does; why each layer exists; how the layers interact; what state and estimation mechanisms exist; what the Signal Contract is; how signal-swap survivability changes when the contract is met versus violated; what assumptions are made; where documentation and implementation diverge; which components are alpha-specific; which components survive signal replacement; how costs and buffering affect the framework; how causality is handled; what remains unverified; and what principles can later be evaluated for swing and intraday futures transfer.

The objective is understanding. Do not turn the audit into an optimization exercise, redesign exercise, or endorsement exercise.
