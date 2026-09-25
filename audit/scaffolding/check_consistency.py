import csv,re
R=open("pysystemtrade_audit.md").read(); P=open("audit_progress.md").read()
rows=list(csv.DictReader(open("pysystemtrade_framework_inventory.csv")))
ids=[r["component_id"] for r in rows]; H=list(rows[0].keys())
def chk(name,ok): print(("OK  " if ok else "FAIL")+" "+name)
chk("no tier column in CSV", "tier" not in [h.lower() for h in H])
chk("CSV 41 rows (E06 added in Phase 6)", len(rows)==41)
chk("no stale 'Tier assignment ... NOT YET AUDITED'", "Tier assignment and full Tier 1 component cards: **NOT YET AUDITED**" not in R)
sec=R[R.index("### 6.2"):R.index("### 6.3")]
missing=[i for i in ids if i.split("_")[0] not in sec]
chk("all 40 IDs in 6.2 tier table (missing=%s)"%missing, not missing)
cards=re.findall(r"^#### Card (\d+) — (.*)$",R,re.M); chk("16 cards (found %d)"%len(cards), len(cards)==16)
t1=re.findall(r"\b([ACDEPR]\d\d|C0\d)\b", [l for l in sec.split("\n") if l.startswith("| **Tier 1** (")][0])
t1=sorted(set(t1)); chk("Tier 1 row covers 26 IDs (found %d)"%len(t1), len(t1)==26)
cardtxt=R[R.index("### 6.4"):R.index("### 6.5")]
nocard=[i for i in t1 if i not in cardtxt]; chk("every Tier 1 ID in a card (missing=%s)"%nocard, not nocard)
chk("Tier 2 + Tier 3 recorded", "**Tier 2**" in sec and "**Tier 3**" in sec)
t2=re.findall(r"\b([ACDEPR]\d\d)\b", [l for l in sec.split("\n") if l.startswith("| **Tier 2**")][0]); n3=[i for i in set(t2)]
chk("Tier2 IDs have 6.3 notes", all(("| %s "%i) in R[R.index("### 6.3"):R.index("### 6.4")] for i in set(t2)))
chk("Tier1(26)+SC+Tier2(%d)=41"%len(set(t2)), len(t1)+1+len(set(t2))==41)
for k in ["FDM split","buffered position is PORTFOLIO_RISK","Implementation-location caveat","**simulated**"]:
    chk("approved classification text: "+k, k in R)
byid={r["component_id"].split("_")[0]:r for r in rows}
exp={"R04":{"impl_evidence":"INFERRED"},"R07":{"impl_evidence":"INFERRED"},"P04":{"impl_evidence":"VERIFIED","stateful":"N","doc_status":"NOT_DOCUMENTED"},"E02":{"impl_evidence":"VERIFIED","divergence":"Y"},"R11":{"divergence":"Y"},"R03":{"impl_evidence":"INFERRED"},"R05":{"impl_evidence":"INFERRED"},"R06":{"impl_evidence":"INFERRED"}}
for i,d in exp.items():
    for k,v in d.items(): chk("CSV %s.%s == %s (is %s)"%(i,k,v,byid[i][k]), byid[i][k]==v)
chk("last_phase in {5,...,16} (session 8 adds 15, 16)", all(r["last_phase"] in ("5","6","7","8","9","10","11","12","13","14","15","16","17","18") for r in rows))
chk("swap_evidence as Phase 4 (A06 TESTED, A07 HYPOTHESIS, rest INFERRED/UNVERIFIED)", all(r["swap_evidence"]==({"A06_FORECAST_COMBINATION":"TESTED","A07_FORECAST_MAPPING":"HYPOTHESIS"}.get(r["component_id"], r["swap_evidence"] if r["swap_evidence"] in ("INFERRED","UNVERIFIED") else "X")) for r in rows))
TL={"CONCEPTUALLY PORTABLE — UNTESTED","POTENTIALLY PORTABLE — REQUIRES REDESIGN","DAILY-DEPENDENT","TRANSFER NOT JUSTIFIED"}
chk("transfer labels assessed (P2 Deliverable 1): no NOT YET ASSESSED; all in the four approved labels", all(r["swing_transfer_label"] in TL and r["intraday_transfer_label"] in TL for r in rows))
for k in ["DV7","DV8","DV9"]: chk(k+" in divergence register", ("| %s |"%k) in R)
chk("progress: Phase 5 COMPLETE", "P0 Phase 5 — Master inventory (tiers + Tier 1 cards) | COMPLETE" in P)
NT=P[P.index("**Exact next task:**"):P.index("## Unresolved issues")]
chk("progress: next task = STOP / await operator review of P2", "**Exact next task:** **STOP. Await operator review of P2**" in P)
chk("progress: usage NOT RECORDED", "NOT RECORDED" in P)
chk("report status line: P1A COMPLETE; P1B COMPLETE; Phase 19 skipped", "P1A COMPLETE" in R[:2000] and "Phase 15 §16" in R[:2000] and "Phase 18 §19" in R[:2000] and "P1B COMPLETE — P1B STOP" in R[:2000] and "Phase 19 SKIPPED — RESOURCE PRIORITY" in R[:2000])
chk("progress mentions 40 rows consistent", "16 cards / 26 IDs" in P)

chk("Card 6 swap_evidence matches CSV TESTED", "**swap_evidence:** **TESTED**" in R[R.index("#### Card 6"):R.index("#### Card 7")])
import re as _re
for i,card in (("R04","#### Card 8"),("R07","#### Card 11")):
    nxt="#### Card 9" if i=="R04" else "#### Card 12"
    c=R[R.index(card):R.index(nxt)]
    chk(i+" card says INFERRED, no residual VERIFIED claim for it", ("R04 **INFERRED**" in c if i=="R04" else "**impl_evidence:** **INFERRED**" in c) and "upgraded in Phase 5" not in c)
chk("no text still claims R04/R07 VERIFIED", not _re.search(r"(R04|R07)[^\n|]{0,40}\*\*VERIFIED\*\*", R) and "correlation sampling are now VERIFIED" not in P)
chk("U5 RESOLVED in progress", "U5: **RESOLVED**" in P)
chk("section 7 complete, no NOT YET AUDITED", "Phase 6 status: COMPLETE" in R and "NOT YET AUDITED (Phase 6)" not in R)
chk("section 7 has 10 concept subsections", all(("### 7.%d "%k) in R for k in range(1,11)))
chk("DV10 in register", "| DV10 |" in R)
chk("E06 in CSV, Tier 2 table and notes", "E06_PROD_OVERRIDES_LIMITS" in [r["component_id"] for r in rows] and "E06 (added in Phase 6)" in R and "| E06 Production overrides" in R)
chk("R03-R07 still INFERRED", all(byid[k]["impl_evidence"]=="INFERRED" for k in ("R03","R04","R05","R06","R07")))
chk("usage still unrecorded", "Phase 6 (session 2): not recorded" in P)
# ---- Phase 7 checks (session 3) ----
s8=R[R.index("## 8. State and Estimation Audit"):R.index("## 9. Dependency")]
chk("section 8 complete, no NOT YET AUDITED (Phase 7)", "Phase 7 status: COMPLETE" in s8 and "NOT YET AUDITED (Phase 7)" not in R)
chk("section 8 has 8.1-8.6", all(("### 8.%d "%k) in s8 for k in range(1,7)))
chk("spec 37 table header present", "| # | Quantity | Source | Window | Update Frequency | Method | Available When | R/E/F | OOS Behavior | Missing Data | Evidence |" in s8)
qrows=re.findall(r"^\| Q(\d+) \|", s8, re.M); chk("8.1 has Q1..Q20 (found %d)"%len(qrows), qrows==[str(i) for i in range(1,21)])
for q in ["volatility","Forecast correlations","Instrument correlations","Forecast weights","Instrument weights","Forecast scalar","cap","FDM","IDM","cost","Turnover","Carry","Buffer","Capital","Risk estimates","Execution state"]:
    chk("8.1 covers "+q, q.lower() in s8[s8.index("### 8.1"):s8.index("### 8.2")].lower())
chk("PF-1..PF-12 in register", all(("| PF-%d |"%k) in s8 for k in range(1,13)))
chk("pre-flags unclassified (no CONFIRMED/POSSIBLE ISSUE labels applied)", "CONFIRMED ISSUE |" not in s8 and "POSSIBLE ISSUE |" not in s8)
chk("CSV P07 VERIFIED (Phase 7, logged)", byid["P07"]["impl_evidence"]=="VERIFIED" and "P07_CAPITAL_MULTIPLIER | impl_evidence | UNVERIFIED → **VERIFIED**" in s8)
chk("CSV: E05 still UNVERIFIED; D01 VERIFIED since session 7 (§11.13); P09 VERIFIED since session 5 (§13.9)", byid["E05"]["impl_evidence"]=="UNVERIFIED" and byid["D01"]["impl_evidence"]=="VERIFIED" and byid["P09"]["impl_evidence"]=="VERIFIED" and "D01_PRICE_ROLL_DATA | impl_evidence | UNVERIFIED → **VERIFIED**" in R)
chk("E06 unchanged Tier2/VERIFIED", byid["E06"]["impl_evidence"]=="VERIFIED")
DIST=sorted(__import__("collections").Counter(r["last_phase"] for r in rows).items())
chk("last_phase distribution matches session 8 (%s)"%DIST, DIST==[("10",1),("11",5),("14",15),("15",1),("16",3),("17",6),("18",6),("5",1),("8",2),("9",1)])
es=R[R.index("## Executive Summary"):R.index("## 1. Audit Scope")]
nb=len(re.findall(r"^\d+\. ",es,re.M)); chk("Executive Summary <=20 bullets (%d)"%nb, nb<=20)
chk("progress: Phase 7 COMPLETE", "P0 Phase 7 — State and estimation | COMPLETE" in P)
chk("progress: Phase 7 usage UNRECORDED", "Phase 7 (session 3): **UNRECORDED**" in P)
chk("section 7.3 backfill correction logged", "Phase 7 correction (§8.6)" in R and "| §7.3" in s8)
chk("progress G8 recorded", "- G8 (Phase 7)" in P)

# ---- Phase 8 / P0 end checks ----
s9=R[R.index("## 9. Dependency / Information Flow"):R.index("## 10. Simulation")]
chk("section 9 complete, no NOT YET AUDITED (Phase 8)", "Phase 8 status: COMPLETE" in s9 and "NOT YET AUDITED (Phase 8)" not in R)
chk("section 9 has 9.1-9.9", all(("### 9.%d "%k) in s9 for k in range(1,10)))
chk("section 9 edge tables D1-D18, F1-F5, L1-L5", all(("| D%d |"%k) in s9 for k in range(1,19)) and all(("| F%d |"%k) in s9 for k in range(1,6)) and all(("| L%d |"%k) in s9 for k in range(1,6)))
chk("section 9 cites pre-flags but classifies none", "PF-" in s9 and "CONFIRMED ISSUE |" not in s9 and "POSSIBLE ISSUE |" not in s9)
chk("DV11 and DV12 in register", "| DV11 |" in R and "| DV12 |" in R)
chk("DISC-1/DISC-2 raised and (session 5, operator-approved) corrected with before/after log", "| DISC-1 |" in s9 and "| DISC-2 |" in s9 and "*(Corrected in session 5, DISC-1; see §13.9.)*" in R and "*(Corrected in session 5, DISC-2; see §13.9.)*" in R and "| §2 \"Engines\" (DISC-1) | There is no separate event loop; the only per-period loop is the buffer application" in R)
import re as _re2
es=R[R.index("## Executive Summary"):R.index("## 1. Audit Scope")]
chk("Executive Summary <= 20 numbered bullets", len(_re2.findall(r"^\d+\. \*\*", es, _re2.M))<=20)
chk("alpha_specific unchanged (only A03 = Y)", [r["component_id"].split("_")[0] for r in rows if r["alpha_specific"]=="Y"]==["A03"])
chk("progress: Phase 8 COMPLETE and P0 STOP", "P0 Phase 8 — Dependency / information flow | COMPLETE" in P and "COMPLETE — P0 STOP" in P)
chk("progress: $81 kept as remaining balance only", "REMAINING Claude Code credit balance: $81" in P and "NOT a consumed-cost figure" in P)
chk("progress: Phase 8 usage UNRECORDED", "Phase 8 (session 4): **UNRECORDED**" in P)

# ---- P1A Phases 11-12 (session 5) ----
s12=R[R.index("## 12. Forecast / Weight / Portfolio Methodology"):R.index("## 13. Cost / Turnover")]
s13=R[R.index("## 13. Cost / Turnover"):R.index("## 14. Configuration")]
chk("section 12 complete, placeholder gone", "Phase 11 status: COMPLETE" in s12 and "NOT YET AUDITED (P1A Phase 11)" not in R)
chk("section 13 complete, placeholder gone", "Phase 12 status: COMPLETE" in s13 and "NOT YET AUDITED (P1A Phase 12)" not in R)
chk("section 12 has 12.1-12.6", all(("### 12.%d "%k) in s12 for k in range(1,7)))
chk("section 13 has 13.1-13.9", all(("### 13.%d "%k) in s13 for k in range(1,10)))
chk("section 12 covers G1, G7 and P09", "G1:" in s12 and "G7:" in s12 and "P09 dynamic optimisation" in s12 and "PARTIALLY AUDITED — RESOURCE PRIORITY" in s12)
chk("section 13 absence claims record their searches", "market.?impact" in s13 and "cost.?curve" in s13 and "UNVERIFIED" in s13)
chk("section 13 research/live includes DV3", "**DV3**" in s13)
chk("DV13, UD3, UD4 in register", "| DV13 |" in R and "| UD3 |" in R and "| UD4 |" in R)
chk("P09 change logged; R03-R07 still INFERRED", byid["P09"]["impl_evidence"]=="VERIFIED" and "P09_DYNAMIC_OPTIMISATION | impl_evidence | UNVERIFIED → **VERIFIED**" in s13 and all(byid[k]["impl_evidence"]=="INFERRED" for k in ("R03","R04","R05","R06","R07")))
chk("pre-flags still unclassified in 12/13", "CONFIRMED ISSUE |" not in s12+s13 and "POSSIBLE ISSUE |" not in s12+s13)
chk("progress: Phase 11-12 usage UNRECORDED; $81 and $66 kept as remaining balances only", "Phase 11-12 (session 5): **UNRECORDED**" in P and "$66" in P and "REMAINING Claude Code credit balance: $81" in P)
chk("progress: session 5 intermediate stop still recorded in the session log", "**Intermediate stop (operator-chosen), not the P1A stop.**" in P)

# ---- P1A Phase 9 (session 6) ----
s10=R[R.index("## 10. Simulation / Backtest Architecture"):R.index("## 11. Data / Contract")]
chk("section 10 complete, placeholder gone", "Phase 9 status: COMPLETE" in s10 and "NOT YET AUDITED (P1A Phase 9)" not in R)
chk("section 10 has 10.1-10.9", all(("### 10.%d "%k) in s10 for k in range(1,10)))
chk("section 10 covers the spec 39 dimensions", all(k in s10 for k in ["Time advancement","Recalculation","Caching","Estimation","Signal availability","Position timing","Fills","Costs","Account state","Risk","P&L","Reporting"]))
chk("section 10 classifies the architecture and lists higher-frequency assumptions", "### 10.3 Architecture classification" in s10 and "### 10.6 Assumptions relevant to higher-frequency transfer" in s10)
chk("section 10 raises DISC-3 without editing earlier text; UD5 in register", "| DISC-3 |" in s10 and "| UD5 |" in R and "P06 is the only path-dependent step in the backtest" in R[R.index("## 4. Alpha"):R.index("## 5. Signal")])
chk("section 10 leaves pre-flags unclassified", "CONFIRMED ISSUE |" not in s10 and "POSSIBLE ISSUE |" not in s10)
chk("progress: Phases 9 and 10 COMPLETE; P1A STOP; Phase 10 not skipped", "P1A Phase 9 — Simulation / backtest architecture | COMPLETE" in P and "| P1A Phase 10 — Data / contract / roll architecture | COMPLETE" in P and "**P1A (Phases 9–14)** | **COMPLETE — P1A STOP**" in P and "SKIPPED" not in [l for l in P.split("\n") if l.startswith("| P1A Phase 10 ")][0])
chk("progress: session 6 setup attempt recorded", "Session 6: scratch clone and venv recreated in **setup attempt 1 of 2**" in P)

# ---- P1A Phase 14 (session 6) ----
s15=R[R.index("## 15. Static Causality / Look-Ahead Audit"):R.index("## 16. Empirical Causality")]
chk("section 15 complete, placeholder gone", "Phase 14 status: COMPLETE" in s15 and "NOT YET AUDITED (P1A Phase 14)" not in R)
chk("section 15 has 15.1-15.7", all(("### 15.%d "%k) in s15 for k in range(1,8)))
chk("section 15 answers the central question", "### 15.1 Central question" in s15 and "If a position is established at time T" in s15)
cls=("NO ISSUE IDENTIFIED","POSSIBLE ISSUE","CONFIRMED ISSUE","UNVERIFIED")
pf=s15[s15.index("### 15.2"):s15.index("### 15.3")]
rowsPF={k:[l for l in pf.split("\n") if l.startswith("| PF-%d "%k) or l.startswith("| PF-%d |"%k)] for k in range(1,16)}
chk("PF-1..PF-15 each classified in 15.2 with an allowed label", all(len(v)==1 and any(c in v[0] for c in cls) for v in rowsPF.values()))
chk("section 15 distinguishes NO ISSUE IDENTIFIED from verified causal", "not verified causal" in s15.lower() or "Not verified causal" in s15)
chk("section 15 covers the spec 39 inspection items", all(k in s15 for k in ["Future prices","Same-day close leakage","Volatility leakage","Correlation leakage","Weight","Full-sample estimation","Warm-up / backfill","OOS contamination","Execution timing","Cost timing","Roll / back-adjustment"]))
chk("EXP-04 recorded with the five spec 22 items and in progress", s15.count("*Question:*")==1 and "*Stopping condition:*" in s15 and "| EXP-04 |" in P)
chk("progress: Phase 14 COMPLETE", "P1A Phase 14 — Static causality / look-ahead | COMPLETE" in P)

# ---- P1A Phase 13 and session 6 stop ----
s14=R[R.index("## 14. Configuration / Experiment Infrastructure"):R.index("## 15. Static Causality")]
chk("section 14 complete, placeholder gone", "Phase 13 status: COMPLETE" in s14 and "NOT YET AUDITED (P1A Phase 13)" not in R)
chk("section 14 has 14.1-14.6", all(("### 14.%d "%k) in s14 for k in range(1,7)))
chk("section 14 covers the spec 39 items", all(k in s14 for k in ["Configurable components","Strategy representation","Instrument representation","Portfolio representation","Parameter storage","Reproducibility","Configuration versioning","Code / config interaction","Experiment comparison"]))
chk("DV14 and UD5 in register", "| DV14 |" in R and "| UD5 |" in R)
chk("sections 10, 11, 14, 15 complete; no Phase 10 placeholder", all(x in R for x in ["Phase 9 status: COMPLETE","Phase 10 status: COMPLETE","Phase 13 status: COMPLETE","Phase 14 status: COMPLETE"]) and "NOT YET AUDITED (P1A Phase 10)" not in R)
chk("progress: Phase 13 COMPLETE", "P1A Phase 13 — Configuration / experiment infrastructure | COMPLETE" in P)
chk("progress: Phase 10 decision taken (operator approved; session 7)", "operator approved Phase 10 after seeing the session-6 spend" in P)
chk("progress: session 6 usage UNRECORDED; earlier usage lines and $81/$66 kept", "Phases 9/14/13 (session 6): **UNRECORDED**" in P and "Phase 11-12 (session 5): **UNRECORDED**" in P and "$66" in P and "$81" in P)
chk("CSV: C04 and R03-R07 INFERRED; E05 UNVERIFIED (unchanged by session 7)", byid["C04"]["impl_evidence"]=="INFERRED" and byid["E05"]["impl_evidence"]=="UNVERIFIED")
chk("Executive Summary mentions Phases 9, 14 and 13", all(k in es for k in ["Phase 9, §10","Phase 14, §15","Phase 13, §14"]))

# ---- P1A Phase 10 (session 7) ----
s11=R[R.index("## 11. Data / Contract / Roll Architecture"):R.index("## 12. Forecast / Weight")]
chk("section 11 has 11.1-11.13", all(("### 11.%d "%k) in s11 for k in range(1,14)))
chk("PF-8 explicitly resolved (classification, evidence, path, decision impact, future info, uncertainty)", all(x in s11 for x in ["### 11.10 PF-8","**Classification:**","**Evidence:**","**Code path:**","**Can it affect a trading decision?**","**Is future information required?**","**Remaining uncertainty:**","**supersedes**"]))
chk("D01 explicitly resolved", all(x in s11 for x in ["### 11.11 D01","**What D01 asked:**","**Phase 10 evidence:**","**Classification:**","**Remaining uncertainty (UNVERIFIED):**"]))
chk("EXP-05 recorded (report + progress)", "EXP-05" in s11 and "| EXP-05 |" in P)
s15=R[R.index("## 15."):R.index("## 16.")]
chk("section 15 not edited: PF-8 there still reads UNVERIFIED", "| PF-8 | Carry / roll data |" in s15 and "**UNVERIFIED**" in s15[s15.index("| PF-8 | Carry / roll data |"):s15.index("| PF-8 | Carry / roll data |")+900])
chk("progress: Phase 10 usage UNRECORDED; $81/$66 kept as balances", "Phase 10 (session 7): **UNRECORDED**" in P and "REMAINING Claude Code credit balance: $81" in P and "$66" in P)
chk("Executive Summary still <= 20 bullets after Phase 10", len(__import__("re").findall(r"^\d+\. \*\*", R[R.index("## Executive Summary"):R.index("## 1. Audit Scope")], __import__("re").M))<=20)

# ---- P1B Phase 15 (session 8) ----
s16=R[R.index("## 16. Empirical Causality Testing"):R.index("## 17. Position / Lag")]
chk("section 16 complete, placeholder gone", "Phase 15 status: COMPLETE" in s16 and "NOT YET AUDITED (P1B Phase 15)" not in R)
chk("section 16 has 16.1-16.11", all(("### 16.%d "%k) in s16 for k in range(1,12)))
chk("each EXP-06..11 section has the five spec 22 items", (s16.count("*Question:*")+s16.count("*Questions:*"))==6 and s16.count("*Why static inspection is insufficient:*")==6 and s16.count("*Smallest experiment:*")==6 and s16.count("*Stopping condition:*")>=5)
chk("EXP-06..11 in progress table", all(("| EXP-%02d |"%k) in P for k in range(6,12)))
for k in ["exp06_pf2_cost_deflator.py","exp07_pf1_scalar_backfill.py","exp08_pf3_pf4_pf11_forecast_weights.py","exp08b_pf11_breakdown.py","exp09_op11_1_years_of_data.py","exp10_pf15_per_contract_bfill.py","exp11_op9_limit_fill_accounting.py"]:
    chk("script exists: "+k, __import__("os").path.exists("scaffolding/experiments/"+k) and __import__("os").path.exists("scaffolding/experiments/"+k.split("_")[0]+"_output.txt"))
chk("PF-15 reclassification recorded", "**changed → NO ISSUE IDENTIFIED** for positions and P&L" in s16)
# ---- Phase 15 correction (session 8, operator-authorised) ----
c16=s16[:s16.index("### 16.12")]
chk("PF-11 label is POSSIBLE ISSUE in 16.2, 16.5 and 16.10 (outside the 16.12 history)", "| PF-11 end-anchored fit grid |" in c16 and "**POSSIBLE ISSUE** (unchanged from §15" in c16 and "**Causality label:** **POSSIBLE ISSUE**, unchanged from §15" in c16 and "| **POSSIBLE ISSUE**, unchanged (the interim CONFIRMED relabel was reverted" in c16 and "changed → CONFIRMED" not in c16)
chk("PF-11 separate lines: design property TESTED L1-L4; future market data NO ISSUE IDENTIFIED", "**Sample-end → refit-date dependency:** TESTED, **L1–L4**" in c16 and "**design property**" in c16 and "**Future market data entering estimates:** **NO ISSUE IDENTIFIED**" in c16)
chk("16.12 keeps the interim text verbatim and the section 15 original", "### 16.12 Phase 15 correction" in s16 and "**changed → CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED** (calendar-only post-T input)" in s16[s16.index("### 16.12"):] and "Reclassified to **CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED**" in s16[s16.index("### 16.12"):])
chk("Executive Summary: PF-11 stays POSSIBLE", "**PF-11 stays POSSIBLE ISSUE**" in es and "PF-11 POSSIBLE → CONFIRMED" not in R[R.index("## Executive Summary"):R.index("## 1. Audit Scope")])
chk("O-P9-1 accounting-valuation sentence present", "is an accounting-valuation effect" in s16 and "It is not evidence of future information." in s16)
chk("progress: F45 PF-11 POSSIBLE with interim kept; L-P15-1 limitation recorded", "PF-11 stays **POSSIBLE ISSUE**" in P and "Interim wording, superseded" in P and "L-P15-1 (documented limitation, Phase 15)" in P)
chk("section 15 not edited: PF-11 and PF-15 still POSSIBLE there", "| PF-11 | Fit-period grid anchored to the sample end |" in s15 and "**POSSIBLE ISSUE** (post-T calendar information" in s15 and "**POSSIBLE ISSUE** (post-T values enter only" in s15)
chk("causal levels reported (L1-L4)", all(x in s16 for x in ["L1 internal calculation","L2 forecast","L3 position","L4 P&L"]))
chk("untested findings listed with reasons", "### 16.9 Findings not tested" in s16 and "O-P9-3" in s16 and "PF-8" in s16)
chk("no 'material' label applied", "The spec defines no threshold" in s16)
chk("CSV: R05 at last_phase 15 (E02, R01, R08, R09, P09 moved on in Phases 16/18)", sorted(r["component_id"].split("_")[0] for r in rows if r["last_phase"]=="15")==["R05"])
chk("CSV: U5 still holds (R03-R07, C04 INFERRED)", all(byid[i]["impl_evidence"]=="INFERRED" for i in ["R03","R04","R05","R06","R07","C04"]))
chk("progress: Phase 15 COMPLETE, stopped before Phase 16; usage UNRECORDED", "P1B Phase 15 — Empirical causality | COMPLETE" in P and "STOPPED BEFORE PHASE 16" in P and "Phase 15 (session 8): **UNRECORDED**" in P)
chk("progress: Phase 15 estimation flags per experiment", "**Phase 15 flags per experiment" in P)
chk("Executive Summary <= 20 bullets after Phase 15", len(__import__("re").findall(r"^\d+\. \*\*", R[R.index("## Executive Summary"):R.index("## 1. Audit Scope")], __import__("re").M))<=20)

# ---- P1B Phase 16 (session 8) ----
s17=R[R.index("## 17. Position / Lag / P&L Timing"):R.index("## 18. Degrees of Freedom")]
chk("section 17 complete, placeholder gone", "Phase 16 status: COMPLETE" in s17 and "NOT YET AUDITED (P1B Phase 16)" not in R)
chk("section 17 has 17.1-17.7", all(("### 17.%d "%k) in s17 for k in range(1,8)))
chk("three traced dates with rule-based selection stated in advance", all(x in s17 for x in ["**2023-02-28**","**2023-02-09**","**2024-03-28**","stated before running"]))
chk("trace tables A/B/C carry the required fields", all(s17.count(x)>=3 for x in ["| Market data |","| Signal / forecast |","| Position available |","| Lag applied |","| Fill |","| Return / P&L price |","| Same-day exposure |","| Next-bar convention |"]))
chk("documented vs implemented table present", "### 17.4 Documented vs implemented" in s17 and "docs/backtesting.md:2738" in s17)
chk("EXP-12/12b scripts, outputs and progress rows", all(__import__("os").path.exists("scaffolding/experiments/"+f) for f in ["exp12_timing_trace.py","exp12_output.txt","exp12b_roll_day_source.py","exp12b_output.txt"]) and "| EXP-12 |" in P and "| EXP-12b |" in P)
chk("CSV: D01,E01,P06 at last_phase 16 (E02 moved on to 18)", sorted(r["component_id"].split("_")[0] for r in rows if r["last_phase"]=="16")==["D01","E01","P06"])
chk("progress: Phase 16 COMPLETE, stopped before 17; usage UNRECORDED", "P1B Phase 16 — Position / lag / P&L timing | COMPLETE" in P and "Phase 16 (session 8): **UNRECORDED**" in P)
chk("Executive Summary <= 20 bullets after Phase 16", len(__import__("re").findall(r"^\d+\. \*\*", R[R.index("## Executive Summary"):R.index("## 1. Audit Scope")], __import__("re").M))<=20)

# ---- P1B Phase 17 (session 8) ----
s18=R[R.index("## 18. Degrees of Freedom / Research Safeguards"):R.index("## 19. Testing / Validation Infrastructure")]
chk("section 18 complete, placeholder gone", "Phase 17 status: COMPLETE" in s18 and "NOT YET AUDITED (P1B Phase 17)" not in R)
chk("section 18 has 18.1-18.6", all(("### 18.%d "%k) in s18 for k in range(1,7)))
chk("parameter inventory covers every requested area", all(("| "+a+" |") in s18 for a in ["Trading-rule parameters","Forecast parameters","Forecast scaling","Forecast caps","Volatility windows","Correlation windows","Instrument weighting","Portfolio parameters","Risk targets","Buffering","Costs","Instrument selection","Rule selection","Adaptive behaviour (other)"]))
chk("safeguards inventory covers every requested risk", all(("| "+a+" |") in s18 for a in ["Look-ahead","Data snooping","Repeated experimentation","Parameter mining","Strategy selection bias","Instrument selection bias","Date-range selection","Regime selection","Post-hoc methodology changes"]))
chk("tooling inventory covers sensitivity, bootstrap, Monte Carlo, significance, robustness", all(("| "+a+" |") in s18 for a in ["Sensitivity analysis","Bootstrap","Monte Carlo","Significance testing","Robustness checks"]))
chk("O-P16-2 status formalised: report-only, not a CSV row, VERIFIED", "**report-only prose; not a CSV row.**" in R and "O-P16-2 status" in P)
chk("CSV: exactly A04,A05,C04,P01,P05,R02 at last_phase 17; C04 still INFERRED", sorted(r["component_id"].split("_")[0] for r in rows if r["last_phase"]=="17")==["A04","A05","C04","P01","P05","R02"] and byid["C04"]["impl_evidence"]=="INFERRED")
chk("progress: Phase 17 COMPLETE, stopped before 18; usage UNRECORDED", "P1B Phase 17 — Degrees of freedom / research safeguards | COMPLETE" in P and "STOPPED BEFORE PHASE 18" in P and "Phase 17 (session 8): **UNRECORDED**" in P)
chk("Executive Summary <= 20 bullets after Phase 17", len(__import__("re").findall(r"^\d+\. \*\*", R[R.index("## Executive Summary"):R.index("## 1. Audit Scope")], __import__("re").M))<=20)

# ---- P1B Phase 18 (session 8) ----
s19=R[R.index("## 19. Testing / Validation Infrastructure"):R.index("## 20. Live / Production Architecture")]
chk("section 19 complete, placeholder gone", "Phase 18 status: COMPLETE" in s19 and "NOT YET AUDITED (P1B Phase 18)" not in R)
chk("section 19 has 19.1-19.5", all(("### 19.%d "%k) in s19 for k in range(1,6)))
chk("coverage inventory covers all 15 requested areas", all(("| "+a+" |") in s19 for a in ["Forecasts","Volatility","Weights","Correlations","FDM","IDM","Buffering","Costs","Data","Rolls","Simulation","Configuration","Live behaviour","Reproducibility","Timing"]))
chk("five-finding coverage check present (PF-1, PF-2, PF-3/PF-4, PF-11, PF-15)", all(("| **"+f+"**") in s19 for f in ["PF-1","PF-2","PF-3/PF-4","PF-11","PF-15"]))
chk("proves / does not prove recorded", "### 19.4 What important tests prove vs. do not prove" in s19 and s19.count("do not prove")+s19.count("does not prove")>=5)
chk("run results and collection evidence files present", all(__import__("os").path.exists("scaffolding/phase18/"+f) for f in ["pytest_quick_outcomes.txt","pytest_slow_outcomes.txt","test_file_collection.txt"]) and "101 passed, 40 skipped, 3 xfailed" in s19 and "**17 passed**" in s19)
chk("CSV: exactly C03,E02,P09,R01,R08,R09 at last_phase 18", sorted(r["component_id"].split("_")[0] for r in rows if r["last_phase"]=="18")==["C03","E02","P09","R01","R08","R09"])
chk("progress: Phase 18 COMPLETE, stopped before 19; usage UNRECORDED; TEST-RUN rows", "P1B Phase 18 — Testing / validation infrastructure | COMPLETE" in P and "STOPPED BEFORE PHASE 19" in P and "Phase 18 (session 8): **UNRECORDED**" in P and "| TEST-RUN-1 |" in P and "| TEST-RUN-2 |" in P)
chk("Executive Summary <= 20 bullets after Phase 18", len(__import__("re").findall(r"^\d+\. \*\*", R[R.index("## Executive Summary"):R.index("## 1. Audit Scope")], __import__("re").M))<=20)

# ---- P1B close (session 8) ----
SK="Phase 19 — SKIPPED — RESOURCE PRIORITY. Static review of the research-to-live connection, broker integration, order generation, position reconciliation, account state, persistence, restart behavior, monitoring, logging, overrides, limits, and error handling was not performed. This is a known gap, not a finding of NO ISSUE IDENTIFIED."
s20=R[R.index("## 20. Live / Production Architecture"):R.index("## 21")]
chk("Phase 19 skip text recorded verbatim in report section 20 and progress file", SK in s20 and SK in P and "NOT YET AUDITED (P1B Phase 19" not in R)
chk("progress: P1B COMPLETE — P1B STOP; P2 COMPLETE", "**P1B (Phases 15–19)** | **COMPLETE — P1B STOP**" in P and "| P2 (Phases 20–26) | **COMPLETE** (session 9)" in P)
chk("report: sections 21-27 written, no Deliverable 2 placeholder", all(("## %d. "%n) in R for n in range(21,28)) and "NOT YET AUDITED (Deliverable 2 pending)" not in R and "Comparison questions: NOT YET AUDITED (P2)" not in R)
chk("O-P18-3 recorded: repo-code property, VERIFIED here, INFERRED version-independent", "**O-P18-3" in R and "**VERIFIED** on this environment" in R and "**INFERRED** to reproduce on other Python 3 versions" in R and "O-P18-3" in P)
chk("P1B close usage UNRECORDED", "P1B close (session 8): **UNRECORDED**" in P)
