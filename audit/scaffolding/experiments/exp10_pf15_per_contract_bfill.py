# EXP-10 (Phase 15, PF-15). NON-DEFAULT: dynamic small-system optimisation (P09).
# System = chapter-15 stages + Risk + optimisedPositions + accountForOptimisedStage
# (the stage list of systems/provided/rob_system/run_system.py, with the chapter-15 rules,
# raw data, forecast scale/cap, config and shipped CSVs instead of the database and
# rob_system config). small_system settings: defaults.yaml.
# Question: Portfolios.get_per_contract_value_as_proportion_of_capital_df bfills each
#   instrument's first value into the rows before its data start (source: "slight
#   cheating"). Do those post-T values change any P09 position, or P&L?
# Why static reading is not enough: §15.2 left open whether the objective uses the value
#   of an instrument whose optimal position is not yet defined.
# Smallest experiment: baseline = code as shipped; variant = identical run where ONLY the
#   bfilled rows are set to 2x the bfilled value (in-process patch in this scratch script;
#   no repository file changed). If positions are identical, the post-T values do not
#   reach any decision. (Leaving them NaN was not used: NaN handling by the greedy
#   optimiser is outside Phase 15 scope and could fail for unrelated reasons.)
# Stopping condition: one comparison.
import time
import pandas as pd, numpy as np
from p15_common import build_system, INSTRUMENTS
from sysdata.config.configdata import Config
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from systems.basesystem import System
from systems.forecasting import Rules
from systems.forecast_combine import ForecastCombine
from systems.forecast_scale_cap import ForecastScaleCap
from systems.rawdata import RawData
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
from systems.risk import Risk
from systems.system_cache import diagnostic
from systems.provided.dynamic_small_system_optimise.optimised_positions_stage import optimisedPositions
from systems.provided.dynamic_small_system_optimise.accounts_stage import accountForOptimisedStage

_orig = Portfolios.get_per_contract_value_as_proportion_of_capital_df
PRESTART = {}


def _variant(self):
    instrument_list = self.get_instrument_list()
    values_as_pd = pd.DataFrame({i: self.get_per_contract_value_as_proportion_of_capital(i) for i in instrument_list})
    values_as_pd = values_as_pd.reindex(self.common_index()).ffill()
    mask = values_as_pd.isna()
    values_as_pd = values_as_pd.bfill()
    values_as_pd[mask] = values_as_pd[mask] * 2.0
    return values_as_pd


def p09_system():
    config = Config("systems.provided.futures_chapter15.futuresconfig.yaml")
    return System([Risk(), accountForOptimisedStage(), optimisedPositions(), Portfolios(), PositionSizing(),
                   RawData(), ForecastCombine(), ForecastScaleCap(), Rules()], csvFuturesSimData(), config)


def run():
    s = p09_system()
    t = time.time()
    pos = s.optimisedPositions.get_optimised_position_df()
    vals = s.portfolio.get_per_contract_value_as_proportion_of_capital_df()
    acc = s.accounts.optimised_portfolio()
    return dict(pos=pos, vals=vals, gross=acc.gross.as_ts, costs=acc.costs.as_ts, net=acc.net.as_ts, secs=time.time() - t)


if __name__ == "__main__":
    B = run()
    Portfolios.get_per_contract_value_as_proportion_of_capital_df = diagnostic()(_variant)
    V = run()
    Portfolios.get_per_contract_value_as_proportion_of_capital_df = _orig
    print(f"runtime baseline {B['secs']:.0f}s, variant {V['secs']:.0f}s; dates in loop: {len(B['pos'])}")
    for ins in B["vals"].columns:
        d = (B["vals"][ins] - V["vals"][ins]).abs() > 1e-15
        rows = B["vals"].index[d]
        rng = f"{rows.min().date()}..{rows.max().date()}" if len(rows) else "-"
        print(f"per-contract value rows changed by the variant {ins}: {int(d.sum())} ({rng})")
    dp = (B["pos"] - V["pos"]).abs()
    print("position rows differing per instrument:", {c: int((dp[c] > 0).sum()) for c in dp.columns},
          " maxabs:", float(np.nanmax(dp.values)))
    for k in ["gross", "costs", "net"]:
        a, b = B[k].align(V[k], join="outer")
        print(f"{k}: rows differing={int(((a - b).abs() > 1e-9).sum())}, sum B={a.sum():.2f} V={b.sum():.2f}")
    # descriptive: were the pre-start instruments given non-zero P09 positions before their start?
    for ins in B["vals"].columns:
        start = B["vals"][ins].index[(B["vals"][ins] - V["vals"][ins]).abs() > 1e-15]
        if len(start):
            pre = B["pos"][ins][: start.max()]
            print(f"{ins}: non-zero baseline P09 positions before data start: {int((pre.fillna(0) != 0).sum())}")
