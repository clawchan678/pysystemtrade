# EXP-02: Does base_system_cache key System.get_instrument_list on its arguments?
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysdata.config.configdata import Config
from systems.basesystem import System
data = csvFuturesSimData()
cfg = Config(dict(instruments=["SOFR", "US10", "CORN"]))
s1 = System([], data, cfg)
a = s1.get_instrument_list()
b = s1.get_instrument_list(force_to_passed_list=["SOFR"])
s2 = System([], data, cfg)
c = s2.get_instrument_list(force_to_passed_list=["SOFR"])
print("default:", a, "| forced after default (same system):", b, "| forced on fresh system:", c)
print("cache refs:", s1.cache.get_items_with_data())
