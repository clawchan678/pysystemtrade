# EXP-11 (Phase 15, O-P9-1 / O-P9-2). NON-DEFAULT: the provided hourly example
# (systems/provided/example/hourly_with_order_simulation.py, use_limit_orders=True, its own
# yaml unchanged) on the shipped CSVs instead of the database; instrument US10 only.
# Question O-P9-1: gross P&L is computed from fill-implied positions against the
#   simulator price series, not the fill prices. For limit fills (fill at the order-time
#   price, only if the next price is strictly better) how large is the gap between the
#   framework's gross P&L and the same trades valued at their fill prices?
#   Identity used (positions start at 0): sum_t pos_{t-1}(P_t-P_{t-1}) = pos_T P_T - sum_i q_i P(fill row i);
#   valued at fill prices: pos_T P_T - sum_i q_i f_i; gap = sum_i q_i (f_i - P(fill row i)).
# Question O-P9-2: cost per fill by side (buy fills carry price_requires_slippage_adjustment=False).
# Why static reading is not enough: the size/sign of the gap and cost split need data.
# Smallest experiment: one instrument, one run, no parameter changes.
# Stopping condition: one run.
import pandas as pd, numpy as np
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from systems.provided.example.hourly_with_order_simulation import futures_system

s = futures_system(sim_data=csvFuturesSimData(), use_limit_orders=True)
calc = s.accounts._pandl_calculator_for_instrument_with_cash_costs("US10")
sim = s.accounts.get_order_simulator("US10", is_subsystem=False)
fills = [f for f in sim.list_of_fills() if f.qty != 0]
prices = sim.prices()
vpp = calc.value_per_point
gross_fw = calc.pandl_in_instrument_currency()
q = np.array([f.qty for f in fills], dtype=float)
fp = np.array([f.price for f in fills], dtype=float)
pr = np.array([prices[f.date] for f in fills], dtype=float)
posT = q.sum()
P_T = prices.iloc[-1]
recon_sim = (posT * P_T - (q * pr).sum()) * vpp
recon_fill = (posT * P_T - (q * fp).sum()) * vpp
print(f"price rows {len(prices)} ({prices.index[0]} .. {prices.index[-1]}); non-zero fills {len(fills)} "
      f"(buys {int((q>0).sum())}, sells {int((q<0).sum())}); value per point {vpp}")
print(f"framework gross P&L total (USD): {gross_fw.sum():.2f}")
print(f"reconstruction at simulator prices: {recon_sim:.2f}  (should equal framework total)")
print(f"same trades valued at fill prices : {recon_fill:.2f}")
print(f"gap (fill-price valuation - framework): {recon_fill - recon_sim:.2f} USD "
      f"= {100*(recon_fill-recon_sim)/abs(recon_sim):.1f}% of framework gross")
better = np.where(q > 0, fp > pr, fp < pr)
print(f"fills where fill price is worse for the trader than the fill-row price: {int(better.sum())}/{len(fills)}")
costs = np.array([calc.calculate_cost_instrument_currency_for_a_fill(f) for f in fills])
flag = np.array([f.price_requires_slippage_adjustment for f in fills])
for side, m in [("buy", q > 0), ("sell", q < 0)]:
    print(f"{side}: fills={int(m.sum())}, slippage flag True={int(flag[m].sum())}, "
          f"raw cost per contract mean={np.mean(costs[m]/np.abs(q[m])):.4f} USD")
print(f"framework total costs (instrument ccy, before normalisation): {calc.costs_from_trading_in_instrument_currency_as_series().sum():.2f}")
