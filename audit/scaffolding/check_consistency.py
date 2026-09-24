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
chk("last_phase in {5,6,7,8}", all(r["last_phase"] in ("5","6","7","8") for r in rows))
chk("swap_evidence as Phase 4 (A06 TESTED, A07 HYPOTHESIS, rest INFERRED/UNVERIFIED)", all(r["swap_evidence"]==({"A06_FORECAST_COMBINATION":"TESTED","A07_FORECAST_MAPPING":"HYPOTHESIS"}.get(r["component_id"], r["swap_evidence"] if r["swap_evidence"] in ("INFERRED","UNVERIFIED") else "X")) for r in rows))
chk("transfer labels NOT YET ASSESSED", all(r["swing_transfer_label"]==r["intraday_transfer_label"]=="NOT YET ASSESSED" for r in rows))
for k in ["DV7","DV8","DV9"]: chk(k+" in divergence register", ("| %s |"%k) in R)
chk("progress: Phase 5 COMPLETE", "P0 Phase 5 — Master inventory (tiers + Tier 1 cards) | COMPLETE" in P)
chk("progress: next task P1A (Phase 11 first)", "**Exact next task:** After operator approval, begin **P1A" in P and P.index("Phase 11 — Forecast") < P.index("Phase 12 — Cost") < P.index("Phase 9 — Simulation") < P.index("Phase 14 — Static"))
chk("progress: usage NOT RECORDED", "NOT RECORDED" in P)
chk("report status line P0 complete (Phases 1–8)", "P0 Phases 1–8 complete — P0 STOP" in R)
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
chk("CSV D01/P09/E05 still UNVERIFIED", all(byid[k]["impl_evidence"]=="UNVERIFIED" for k in ("D01","P09","E05")))
chk("E06 unchanged Tier2/VERIFIED", byid["E06"]["impl_evidence"]=="VERIFIED")
chk("last_phase 8 rows == 35 (Phase 8); 6 untouched rows keep earlier phase", sum(r["last_phase"]=="8" for r in rows)==35 and all(byid[k]["last_phase"]!="8" for k in ("C01","C02","C03","C04","SC","P09")))
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
chk("DISC-1/DISC-2 raised, earlier text not edited", "| DISC-1 |" in s9 and "| DISC-2 |" in s9 and "the only per-period loop is the buffer application" in R)
import re as _re2
es=R[R.index("## Executive Summary"):R.index("## 1. Audit Scope")]
chk("Executive Summary <= 20 numbered bullets", len(_re2.findall(r"^\d+\. \*\*", es, _re2.M))<=20)
chk("alpha_specific unchanged (only A03 = Y)", [r["component_id"].split("_")[0] for r in rows if r["alpha_specific"]=="Y"]==["A03"])
chk("progress: Phase 8 COMPLETE and P0 STOP", "P0 Phase 8 — Dependency / information flow | COMPLETE" in P and "COMPLETE — P0 STOP" in P)
chk("progress: $81 kept as remaining balance only", "REMAINING Claude Code credit balance: $81" in P and "NOT a consumed-cost figure" in P)
chk("progress: Phase 8 usage UNRECORDED", "Phase 8 (session 4): **UNRECORDED**" in P)
