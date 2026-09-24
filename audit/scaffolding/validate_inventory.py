import csv,sys
V={"layer":{"ALPHA","RESEARCH","PORTFOLIO_RISK","EXECUTION","CROSS_LAYER"},"alpha_specific":{"Y","N","UNKNOWN"},
"survives_if_contract_met":{"Y","N","PARTIAL","UNKNOWN"},"survives_if_contract_violated":{"Y","N","PARTIAL","UNKNOWN"},
"swap_evidence":{"INFERRED","HYPOTHESIS","TESTED","UNVERIFIED"},"stateful":{"Y","N","UNKNOWN"},"doc_status":{"DOCUMENTED","NOT_DOCUMENTED","UNKNOWN"},
"impl_evidence":{"VERIFIED","INFERRED","UNVERIFIED"},"divergence":{"Y","N","UNKNOWN"}}
T={"NOT YET ASSESSED","CONCEPTUALLY PORTABLE — UNTESTED","POTENTIALLY PORTABLE — REQUIRES REDESIGN","DAILY-DEPENDENT","TRANSFER NOT JUSTIFIED"}
rows=list(csv.reader(open(sys.argv[1]))); h=rows[0]; ok=True
if len({len(r) for r in rows})!=1: ok=False; print("column count mismatch")
ids=[r[0] for r in rows[1:]]
if len(ids)!=len(set(ids)): ok=False; print("dup ids")
for r in rows[1:]:
    d=dict(zip(h,r))
    for k,s in V.items():
        if d[k] not in s: ok=False; print("bad",k,d[k],r[0])
    for k in ("swing_transfer_label","intraday_transfer_label"):
        if d[k] not in T: ok=False; print("bad",k,r[0])
print("rows",len(rows)-1,"cols",len(h),"VALID" if ok else "INVALID")
