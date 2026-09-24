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
chk("last_phase in {5,6}", all(r["last_phase"] in ("5","6") for r in rows))
chk("swap_evidence as Phase 4 (A06 TESTED, A07 HYPOTHESIS, rest INFERRED/UNVERIFIED)", all(r["swap_evidence"]==({"A06_FORECAST_COMBINATION":"TESTED","A07_FORECAST_MAPPING":"HYPOTHESIS"}.get(r["component_id"], r["swap_evidence"] if r["swap_evidence"] in ("INFERRED","UNVERIFIED") else "X")) for r in rows))
chk("transfer labels NOT YET ASSESSED", all(r["swing_transfer_label"]==r["intraday_transfer_label"]=="NOT YET ASSESSED" for r in rows))
for k in ["DV7","DV8","DV9"]: chk(k+" in divergence register", ("| %s |"%k) in R)
chk("progress: Phase 5 COMPLETE", "P0 Phase 5 — Master inventory (tiers + Tier 1 cards) | COMPLETE" in P)
chk("progress: next task Phase 7", "**Exact next task:** Begin **Phase 7" in P)
chk("progress: usage NOT RECORDED", "NOT RECORDED" in P)
chk("report status line Phase 6", "P0 Phases 1–6 complete" in R)
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
