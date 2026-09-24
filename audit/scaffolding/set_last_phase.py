# Set last_phase for the given component-ID prefixes; preserves CRLF and minimal quoting.
import csv,sys
phase=sys.argv[1]; ids=set(sys.argv[2:])
rows=list(csv.reader(open("pysystemtrade_framework_inventory.csv",newline="")))
lp=rows[0].index("last_phase")
for r in rows[1:]:
    if r[0].split("_")[0] in ids: r[lp]=phase
csv.writer(open("pysystemtrade_framework_inventory.csv","w",newline=""),lineterminator="\r\n").writerows(rows)
