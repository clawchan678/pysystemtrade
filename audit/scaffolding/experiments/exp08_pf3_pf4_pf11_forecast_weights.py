# EXP-08 (Phase 15, PF-3 / PF-4 / PF-11). NON-DEFAULT: use_forecast_weight_estimates=True
# (forecast_weight_estimate defaults: handcraft, pooled gross returns, pooled turnover,
# cost_multiplier 2.0, expanding, weekly). In ALL arms vol_normalise_currency_costs=False,
# so PF-2 (EXP-06) cannot enter the P&L comparisons; forecast weights use SR costs only.
#
# Question A (PF-3/PF-4): with the refit grid held identical, does removing post-C data
#   change the forecast weights in force at dates <= C, and hence forecasts, positions, P&L?
# Question B (control): with SR costs removed from the optimiser (cost_multiplier=0.0)
#   and the grid held identical, is the difference zero? (If so, A's differences are
#   attributable to the cost inputs PF-3/PF-4 and nothing else.)
# Question C (PF-11): with costs removed, does a cutoff that moves the grid change
#   the weights in force at dates <= C?
# Why static reading is not enough: §15.2 shows the end anchors; not whether they move
#   any weight, forecast or position, nor by how much.
# Grid alignment: the full-data grid is 2024-03-31 - 365k days (+5us pooled offset).
#   A truncated run ends on a Sunday weekly label; the first Sunday grid point with all
#   six instruments live is 2017-04-02 (k=7) -> C_A = 2017-03-31 (Friday). Verified below
#   by comparing the two runs' period starts. C_M = 2019-12-31 (the cutoff pre-declared
#   in EXP-06/07; not grid-aligned: its end label 2020-01-05 is not a grid point).
# Stopping condition: the five runs below; no other cutoff or parameter.
import pandas as pd, numpy as np
from p15_common import build_system, n_diff, maxabs, INSTRUMENTS
from exp06_pf2_cost_deflator import series, ann_sr

C_A, C_M = "2017-03-31", "2019-12-31"


def cfg(cm):
    return dict(use_forecast_weight_estimates=True, vol_normalise_currency_costs=False,
                forecast_weight_estimate=dict(cost_multiplier=cm))


def collect(system):
    out = dict(series=series(system), raw={}, daily={}, starts=None, sr_cost={}, turnover={})
    for ins in INSTRUMENTS:
        opt = system.combForecast.calculation_of_raw_estimated_monthly_forecast_weights(ins)
        out["raw"][ins] = system.combForecast.get_raw_monthly_forecast_weights(ins)
        out["daily"][ins] = system.combForecast.get_forecast_weights(ins)
        if out["starts"] is None:
            out["starts"] = [p.period_start for p in opt.fit_dates]
        out["sr_cost"][ins] = system.accounts.get_SR_cost_per_trade_for_instrument(ins)
        for rule in system.combForecast.get_trading_rule_list(ins):
            out["turnover"][(ins, rule)] = system.accounts.forecast_turnover(ins, rule)
    return out


def frame_diff(a, b, C):
    a, b = a[:C], b[:C]
    a, b = a.align(b, join="inner")
    d = (a - b).abs()
    return float(np.nanmax(d.values)) if d.size else float("nan"), int((d > 1e-9).any(axis=1).sum()), len(d)


def report(name, X, Y, C):
    Cts = pd.Timestamp(C) + pd.Timedelta(hours=23, minutes=59)
    print(f"\n=== {name} (dates <= {C}) ===")
    sx = [s for s in X["starts"] if s <= Cts]
    sy = [s for s in Y["starts"] if s <= Cts]
    print(f"period starts <= C identical: {sx == sy} ({len(sx)} vs {len(sy)}); "
          f"last three: {[str(s) for s in sx[-3:]]} vs {[str(s) for s in sy[-3:]]}")
    for ins in INSTRUMENTS:
        mr, nr, lr = frame_diff(X["raw"][ins], Y["raw"][ins], Cts)
        md, nd, ld = frame_diff(X["daily"][ins], Y["daily"][ins], Cts)
        print(f"{ins:8s} raw weights: maxabs={mr:.4f} rows differing={nr}/{lr} | "
              f"daily weights: maxabs={md:.4f} rows differing={nd}/{ld}")
    for key in X["series"]:
        f, t = X["series"][key][:Cts], Y["series"][key][:Cts]
        nd, n = n_diff(f, t)
        extra = ""
        if key[0] in ("gross", "costs", "net"):
            extra = f" sum X={f.sum():.1f} Y={t.sum():.1f}"
        print(f"{key}: n_diff={nd}/{n} maxabs={maxabs(f, t):.4g}{extra}")
    for k in ["gross", "net"]:
        f, t = X["series"][(k, "PORT")][:Cts], Y["series"][(k, "PORT")][:Cts]
        print(f"PORT {k} SR <= C: X={ann_sr(f):.4f} Y={ann_sr(t):.4f}")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    F2 = collect(build_system(None, cfg(2.0)))
    A2 = collect(build_system(C_A, cfg(2.0)))
    print("=== Level-1 cost inputs, full (X) vs truncated at C_A (Y), cost_multiplier 2.0 ===")
    for ins in INSTRUMENTS:
        print(f"SR cost per trade {ins}: X={F2['sr_cost'][ins]:.6f} Y={A2['sr_cost'][ins]:.6f} "
              f"ratio={F2['sr_cost'][ins]/A2['sr_cost'][ins]:.4f}")
    for key in sorted(F2["turnover"]):
        print(f"turnover {key}: X={F2['turnover'][key]:.3f} Y={A2['turnover'][key]:.3f}")
    report("A: PF-3/PF-4, grid-aligned C_A, cost_multiplier 2.0 (X=full, Y=trunc)", F2, A2, C_A)
    del A2
    F0 = collect(build_system(None, cfg(0.0)))
    A0 = collect(build_system(C_A, cfg(0.0)))
    report("B: control, grid-aligned C_A, cost_multiplier 0.0 (X=full, Y=trunc)", F0, A0, C_A)
    del A0
    M0 = collect(build_system(C_M, cfg(0.0)))
    report("C: PF-11, non-aligned C_M, cost_multiplier 0.0 (X=full, Y=trunc)", F0, M0, C_M)
