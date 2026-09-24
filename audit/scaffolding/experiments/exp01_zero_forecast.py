# EXP-01: Does an exact-zero raw forecast propagate as zero, or as NaN then forward-filled?
import pandas as pd, numpy as np
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysdata.config.configdata import Config
from systems.basesystem import System
from systems.rawdata import RawData
from systems.forecasting import Rules
from systems.forecast_scale_cap import ForecastScaleCap
from systems.forecast_combine import ForecastCombine
from systems.positionsizing import PositionSizing
from systems.trading_rules import TradingRule

def event_rule(price):
    # +10 for first 40 business days of each quarter, else exactly 0 (flat)
    f = pd.Series(0.0, index=price.index)
    q = price.index.to_period("Q")
    first = pd.Series(price.index, index=price.index).groupby(q).transform("min")
    f[((price.index - first).dt.days < 60).values] = 10.0
    return f

data = csvFuturesSimData()
config = Config(dict(trading_rules=dict(ev=TradingRule(event_rule, data=["rawdata.get_daily_prices"])),
                     instruments=["SOFR"], forecast_scalars=dict(ev=1.0), forecast_weights=dict(ev=1.0),
                     forecast_div_multiplier=1.0, percentage_vol_target=16.0, notional_trading_capital=1e6))
system = System([RawData(), Rules(), ForecastScaleCap(), ForecastCombine(), PositionSizing()], data, config)
code = "SOFR"
raw_rule = event_rule(system.rawdata.get_daily_prices(code))
raw = system.rules.get_raw_forecast(code, "ev")
capped = system.forecastScaleCap.get_capped_forecast(code, "ev")
comb = system.combForecast.get_combined_forecast(code)
pos = system.positionSize.get_subsystem_position(code)
print("rule output zeros:", int((raw_rule == 0).sum()), "of", len(raw_rule))
print("raw forecast zeros:", int((raw == 0).sum()), " NaNs:", int(raw.isna().sum()))
print("capped NaNs:", int(capped.isna().sum()))
print("combined forecast zeros:", int((comb == 0).sum()), " NaNs:", int(comb.isna().sum()), " unique:", sorted(comb.dropna().unique())[:5])
print("subsystem position zeros:", int((pos == 0).sum()), " nonzero:", int((pos.fillna(0) != 0).sum()), " NaN:", int(pos.isna().sum()))
