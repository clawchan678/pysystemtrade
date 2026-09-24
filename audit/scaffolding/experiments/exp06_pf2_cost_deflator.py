# EXP-06 (Phase 15, PF-2). Default chapter-15 system, all estimation OFF.
# Question: does removing post-C observations change historical (<= C) forecasts,
#   positions, gross P&L, costs or net P&L, and by how much?
# Why static reading is not enough: §15.2 shows the deflator formula
#   vol(t)/vol(last row); it does not give the size of the effect on the sample.
# Smallest experiment: the shipped default system on full data vs the same system
#   on data truncated at C (pre-declared C in {2009-12-31, 2019-12-31}; 2009-12-31
#   could not run: EUROSTX (starts 2014-03-13) has no data -> missingData; replaced
#   by 2016-12-30, the first year end after all six instruments have data; no other
#   cutoff tried). Control: the same pair with vol_normalise_currency_costs=False.
# Expected evidence: forecasts/positions/gross identical <= C; costs differ by the
#   per-instrument ratio vol(end)/vol(C) if PF-2 is the only end anchor.
# Stopping condition: one table per cutoff; no further cutoffs or parameters.
import pandas as pd, numpy as np
from p15_common import build_system, n_diff, maxabs, INSTRUMENTS

CUTOFFS = ["2016-12-30", "2019-12-31"]


def series(system):
    out = {}
    for ins in INSTRUMENTS:
        out[("fc", ins)] = system.combForecast.get_combined_forecast(ins)
        out[("pos", ins)] = system.accounts.get_buffered_position(ins, roundpositions=True)
        acc = system.accounts.pandl_for_instrument(ins)
        out[("gross", ins)] = acc.gross.as_ts
        out[("costs", ins)] = acc.costs.as_ts
        out[("net", ins)] = acc.net.as_ts
    port = system.accounts.portfolio()
    out[("gross", "PORT")] = port.gross.as_ts
    out[("costs", "PORT")] = port.costs.as_ts
    out[("net", "PORT")] = port.net.as_ts
    return out


def ann_sr(x):
    x = x.dropna()
    return float(x.mean() / x.std() * np.sqrt(256)) if x.std() > 0 else float("nan")


def compare(full, trunc, C):
    C = pd.Timestamp(C) + pd.Timedelta(hours=23, minutes=59)
    rows = []
    for key in full:
        f, t = full[key][:C], trunc[key][:C]
        nd, n = n_diff(f, t)
        rows.append(dict(item=key[0], ins=key[1], n_diff=nd, n=n, maxabs=maxabs(f, t),
                         sum_full=float(f.sum()), sum_trunc=float(t.sum())))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    for norm in [True, False]:
        ov = dict(vol_normalise_currency_costs=norm)
        full = series(build_system(None, ov))
        for C in CUTOFFS:
            trunc = series(build_system(C, ov))
            df = compare(full, trunc, C)
            print(f"\n=== vol_normalise_currency_costs={norm}  cutoff={C} ===")
            print(df.to_string(index=False, float_format=lambda v: f"{v:.6g}"))
            Cts = pd.Timestamp(C) + pd.Timedelta(hours=23, minutes=59)
            for k in ["gross", "net"]:
                f, t = full[(k, "PORT")][:Cts], trunc[(k, "PORT")][:Cts]
                print(f"PORT {k}: SR full={ann_sr(f):.4f} trunc={ann_sr(t):.4f}")
            cf, ct = full[("costs", "PORT")][:Cts].sum(), trunc[("costs", "PORT")][:Cts].sum()
            gf = full[("gross", "PORT")][:Cts].sum()
            for ins in INSTRUMENTS:
                a, b = full[("costs", ins)][:Cts].align(trunc[("costs", ins)][:Cts], join="inner")
                m = (a.abs() > 1e-9) & (b.abs() > 1e-9)
                r = a[m] / b[m]
                print(f"  cost ratio full/trunc {ins}: min={r.min():.6f} max={r.max():.6f} (n={int(m.sum())})")
            print("  index rows in full[:C] absent from trunc: ",
                  {ins: [str(d.date()) for d in full[("fc", ins)][:Cts].index.difference(trunc[("fc", ins)].index)]
                   for ins in INSTRUMENTS})
            print(f"PORT costs full={cf:.2f} trunc={ct:.2f} ratio={cf/ct if ct else float('nan'):.4f}; "
                  f"costs as % of gross: full={100*cf/gf:.2f}% trunc={100*ct/gf:.2f}%")
