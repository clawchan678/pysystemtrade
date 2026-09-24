# EXP-07 (Phase 15, PF-1). NON-DEFAULT: use_forecast_scale_estimates=True
# (forecast_scalar_estimate defaults: pooled, window 250000, min_periods 500, backfill True).
# Question: how many historical rows receive a forecast scalar built from later rows
#   (the bfill), and does that change forecasts, positions and P&L on those rows?
# Why static reading is not enough: §15.2 shows the bfill; it does not show which
#   rows/instruments are reached under pooling, nor the size of the effect.
# Smallest experiment:
#   (a) isolation: backfill True (baseline) vs backfill False, full data, all else equal.
#       With backfill False, every scalar at t uses only rows <= t (rolling mean of
#       rows <= t, same-date cross-sectional median), i.e. the causality-safe series.
#   (b) matched truncation control: backfill True, full data vs data truncated at
#       C=2019-12-31 (pre-declared); rows <= C should match if the warm-up bfill is
#       the only end/forward anchor in the scalar path.
# Expected evidence: (a) differences confined to the first ~500 pooled rows; (b) none.
# Stopping condition: these two comparisons only.
import pandas as pd, numpy as np
from p15_common import build_system, n_diff, maxabs, INSTRUMENTS
from exp06_pf2_cost_deflator import series, ann_sr

EST = dict(use_forecast_scale_estimates=True)


def scalars(system):
    out = {}
    for ins in INSTRUMENTS:
        for rule in system.combForecast.get_trading_rule_list(ins):
            out[(rule, ins)] = system.forecastScaleCap.get_forecast_scalar(ins, rule)
    return out


def diff_rows(a, b, tol=1e-9):
    a, b = a.align(b, join="outer")
    d = ((a - b).abs() > tol) | (a.isna() != b.isna())
    return a.index[d]


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    base = build_system(None, dict(EST))
    safe = build_system(None, dict(EST, forecast_scalar_estimate=dict(backfill=False)))
    sb, ss = scalars(base), scalars(safe)
    print("=== (a) backfill True vs False, full data ===")
    for k in sorted(sb):
        rows = diff_rows(sb[k], ss[k])
        if len(rows):
            print(f"scalar {k}: {len(rows)} rows differ, {rows.min().date()}..{rows.max().date()}; "
                  f"backfilled value={sb[k][rows].iloc[0]:.4f}")
        else:
            print(f"scalar {k}: 0 rows differ")
    B, S = series(base), series(safe)
    for key in B:
        rows = diff_rows(B[key], S[key])
        if len(rows) or key[1] == "PORT":
            extra = ""
            if key[0] in ("gross", "costs", "net"):
                extra = f" sum over differing rows: base={B[key].reindex(rows).sum():.2f} safe={S[key].reindex(rows).sum():.2f}"
            rng = f"{rows.min().date()}..{rows.max().date()}" if len(rows) else "-"
            print(f"{key}: {len(rows)} rows differ ({rng}){extra}")
    for k in ["gross", "net"]:
        print(f"PORT {k} SR full sample: base={ann_sr(B[(k,'PORT')]):.4f} safe={ann_sr(S[(k,'PORT')]):.4f}")

    print("\n=== (b) matched truncation control, backfill True, C=2019-12-31 ===")
    C = pd.Timestamp("2019-12-31 23:59")
    trunc = build_system("2019-12-31", dict(EST))
    st = scalars(trunc)
    tot = sum(n_diff(sb[k][:C], st[k][:C])[0] for k in sb)
    print(f"scalar rows differing at matched timestamps (all rules x instruments): {tot}")
    T = series(trunc)
    for key in B:
        nd, n = n_diff(B[key][:C], T[key][:C])
        if key[0] in ("fc", "pos") or nd:
            print(f"{key}: n_diff={nd} of {n}, maxabs={maxabs(B[key][:C], T[key][:C]):.3g}")
