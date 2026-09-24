# EXP-09 (Phase 15, O-P11-1). NON-DEFAULT: use_forecast_weight_estimates=True (all other
# settings as shipped/defaults; handcraft, pooled gross returns, equalise_SR False, so the
# top-level SR tilt is active). Full data in both arms.
# Question: the handcraft SR tilt's years_of_data = rows of the STACKED pooled returns /
#   52 (≈ n_pooled x calendar years). Does that definition change fitted weights,
#   forecasts, positions, P&L - or nothing observable?
# Why static reading is not enough: Phase 11 (§12.2) could only infer the tilt strength.
# Smallest experiment: baseline = code as shipped; variant = the same run with
#   portfolioOptimiser.data_length_for_period divided by the pooled count
#   (net_returns.pooled_length), i.e. calendar years, applied as an in-process patch in
#   this scratch script only (no repository file changed). data_length has one consumer
#   on this path: handcraft years_of_data -> SR tilt (git grep data_length, §12.2).
#   This is a measurement counterfactual, not a proposed change.
# Stopping condition: one comparison; no other definition tried.
import pandas as pd, numpy as np
from p15_common import build_system, n_diff, maxabs, INSTRUMENTS
from exp06_pf2_cost_deflator import series, ann_sr
from sysquant.optimisation import portfolio_optimiser as po

EST = dict(use_forecast_weight_estimates=True)
_orig = po.portfolioOptimiser.data_length_for_period


def _calendar_length(self, fit_period):
    return _orig(self, fit_period) / self.length_adjustment


def collect(system):
    out = dict(series=series(system), raw={}, daily={})
    for ins in INSTRUMENTS:
        out["raw"][ins] = system.combForecast.get_raw_monthly_forecast_weights(ins)
        out["daily"][ins] = system.combForecast.get_forecast_weights(ins)
    opt = system.combForecast.calculation_of_raw_estimated_monthly_forecast_weights("CORN").optimiser
    fds = [p for p in opt.fit_dates if not p.no_data]
    last = fds[-1]
    out["len_last"] = (opt.optimiser.data_length_for_period(last), opt.optimiser.length_adjustment, str(last.fit_end.date()))
    return out


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    B = collect(build_system(None, dict(EST)))
    po.portfolioOptimiser.data_length_for_period = _calendar_length
    V = collect(build_system(None, dict(EST)))
    po.portfolioOptimiser.data_length_for_period = _orig
    for name, R in [("baseline", B), ("variant", V)]:
        dl, pl, fe = R["len_last"]
        print(f"{name}: last fit (fit_end {fe}) data_length={dl:.1f} rows -> years_of_data={dl/52:.1f} (pooled_length={pl})")
    for ins in INSTRUMENTS:
        rb, rv = B["raw"][ins].align(V["raw"][ins], join="inner")
        d = (rb - rv).abs()
        db, dv = B["daily"][ins].align(V["daily"][ins], join="inner")
        dd = (db - dv).abs().max(axis=1)
        print(f"{ins:8s} raw weights: maxabs={np.nanmax(d.values):.4f}, periods differing={int((d>1e-9).any(axis=1).sum())}/{len(d)}; "
              f"daily weights maxabs={dd.max():.4f}")
        last = rb.index[-1]
        print("   last period raw weights baseline:", {k: round(v, 3) for k, v in rb.loc[last].items()})
        print("   last period raw weights variant :", {k: round(v, 3) for k, v in rv.loc[last].items()})
    for key in B["series"]:
        f, t = B["series"][key], V["series"][key]
        nd, n = n_diff(f, t)
        extra = f" sum B={f.sum():.1f} V={t.sum():.1f}" if key[0] in ("gross", "costs", "net") else ""
        print(f"{key}: n_diff={nd}/{n} maxabs={maxabs(f, t):.4g}{extra}")
    for k in ["gross", "net"]:
        print(f"PORT {k} SR full sample: B={ann_sr(B['series'][(k,'PORT')]):.4f} V={ann_sr(V['series'][(k,'PORT')]):.4f}")
