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
chk("last_phase in {5,...,15} (session 8 adds 15)", all(r["last_phase"] in ("5","6","7","8","9","10","11","12","13","14","15") for r in rows))
chk("swap_evidence as Phase 4 (A06 TESTED, A07 HYPOTHESIS, rest INFERRED/UNVERIFIED)", all(r["swap_evidence"]==({"A06_FORECAST_COMBINATION":"TESTED","A07_FORECAST_MAPPING":"HYPOTHESIS"}.get(r["component_id"], r["swap_evidence"] if r["swap_evidence"] in ("INFERRED","UNVERIFIED") else "X")) for r in rows))
chk("transfer labels NOT YET ASSESSED", all(r["swing_transfer_label"]==r["intraday_transfer_label"]=="NOT YET ASSESSED" for r in rows))
for k in ["DV7","DV8","DV9"]: chk(k+" in divergence register", ("| %s |"%k) in R)
chk("progress: Phase 5 COMPLETE", "P0 Phase 5 — Master inventory (tiers + Tier 1 cards) | COMPLETE" in P)
NT=P[P.index("**Exact next task:**"):P.index("## Unresolved issues")]
chk("progress: next task = STOP / await operator authorization after Phase 15 (Phase 16 not started)", "**Exact next task:** **STOP. Await operator authorization** after Phase 15" in P and "Do not start Phase 16" in P)
chk("progress: usage NOT RECORDED", "NOT RECORDED" in P)
chk("report status line: P1A COMPLETE; Phase 15 COMPLETE — STOPPED BEFORE PHASE 16", "P1A COMPLETE — P1A STOP" in R[:2000] and "Phase 15 COMPLETE" in R[:2000] and "STOPPED BEFORE PHASE 16" in R[:2000])
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
chk("last_phase distribution matches session 8 (%s)"%DIST, DIST==[("10",2),("11",6),("12",2),("13",1),("14",19),("15",6),("5",1),("8",2),("9",2)])
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
chk("progress: Phases 9 and 10 COMPLETE; P1A STOP; Phase 10 not skipped", "P1A Phase 9 — Simulation / backtest architecture | COMPLETE" in P and "| P1A Phase 10 — Data / contract / roll architecture | COMPLETE" in P and "**P1A (Phases 9–14)** | **COMPLETE — P1A STOP**" in P and "SKIPPED" not in P[P.index("## Stage / phase status"):P.index("## Unresolved issues")])
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
chk("reclassifications recorded (PF-11, PF-15) with originals kept", "**changed → CONFIRMED ISSUE ONLY WHEN NON-DEFAULT OPTION ENABLED**" in s16 and "**changed → NO ISSUE IDENTIFIED** for positions and P&L" in s16)
chk("section 15 not edited: PF-11 and PF-15 still POSSIBLE there", "| PF-11 | Fit-period grid anchored to the sample end |" in s15 and "**POSSIBLE ISSUE** (post-T calendar information" in s15 and "**POSSIBLE ISSUE** (post-T values enter only" in s15)
chk("causal levels reported (L1-L4)", all(x in s16 for x in ["L1 internal calculation","L2 forecast","L3 position","L4 P&L"]))
chk("untested findings listed with reasons", "### 16.9 Findings not tested" in s16 and "O-P9-3" in s16 and "PF-8" in s16)
chk("no 'material' label applied", "The spec defines no threshold" in s16)
chk("CSV: exactly E02,R01,R05,R08,R09,P09 at last_phase 15", sorted(r["component_id"].split("_")[0] for r in rows if r["last_phase"]=="15")==["E02","P09","R01","R05","R08","R09"])
chk("CSV: U5 still holds (R03-R07, C04 INFERRED)", all(byid[i]["impl_evidence"]=="INFERRED" for i in ["R03","R04","R05","R06","R07","C04"]))
chk("progress: Phase 15 COMPLETE, stopped before Phase 16; usage UNRECORDED", "P1B Phase 15 — Empirical causality | COMPLETE" in P and "STOPPED BEFORE PHASE 16" in P and "Phase 15 (session 8): **UNRECORDED**" in P)
chk("progress: Phase 15 estimation flags per experiment", "**Phase 15 flags per experiment" in P)
chk("Executive Summary <= 20 bullets after Phase 15", len(__import__("re").findall(r"^\d+\. \*\*", R[R.index("## Executive Summary"):R.index("## 1. Audit Scope")], __import__("re").M))<=20)
