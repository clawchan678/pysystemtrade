# Phase 15 shared helper (scratch only). Builds the default chapter-15 system
# (systems/provided/futures_chapter15) on either the shipped CSVs or on copies of
# them truncated at a cutoff date. Truncated copies are written under
# scaffolding/home/p15data (git-ignored). No repository file is modified.
import os, shutil, copy, logging
from pathlib import Path
import pandas as pd

logging.disable(logging.CRITICAL)

REPO = Path(__file__).resolve().parents[2] / "repo"
FUT = REPO / "data" / "futures"
SCRATCH = Path(__file__).resolve().parents[1] / "home" / "p15data"
INSTRUMENTS = ["SOFR", "US10", "EUROSTX", "V2X", "MXP", "CORN"]


def _truncate_dir(src: Path, dst: Path, cutoff: pd.Timestamp, names=None):
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.csv"):
        if names is not None and f.stem not in names:
            continue
        df = pd.read_csv(f)
        dt = pd.to_datetime(df["DATETIME"])
        df[dt <= cutoff].to_csv(dst / f.name, index=False)


def csv_paths_for_cutoff(cutoff):
    """Return csv_data_paths dict for a cutoff (None = shipped data, untouched)."""
    if cutoff is None:
        return None
    cutoff = pd.Timestamp(cutoff) + pd.Timedelta(hours=23, minutes=59)
    tag = cutoff.strftime("%Y%m%d")
    root = SCRATCH / tag
    if not (root / "done").exists():
        if root.exists():
            shutil.rmtree(root)
        _truncate_dir(FUT / "adjusted_prices_csv", root / "adj", cutoff, INSTRUMENTS)
        _truncate_dir(FUT / "multiple_prices_csv", root / "mult", cutoff, INSTRUMENTS)
        _truncate_dir(FUT / "fx_prices_csv", root / "fx", cutoff)
        (root / "done").write_text("ok")
    return dict(
        csvFuturesAdjustedPricesData=str(root / "adj"),
        csvFuturesMultiplePricesData=str(root / "mult"),
        csvFxPricesData=str(root / "fx"),
    )


def build_system(cutoff=None, overrides: dict = None):
    from sysdata.config.configdata import Config
    from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
    from systems.provided.futures_chapter15.basesystem import futures_system

    config = Config("systems.provided.futures_chapter15.futuresconfig.yaml")
    for k, v in (overrides or {}).items():
        if isinstance(v, dict) and isinstance(getattr(config, k, None), dict):
            merged = copy.deepcopy(getattr(config, k))
            merged.update(v)
            setattr(config, k, merged)
        else:
            setattr(config, k, v)
    paths = csv_paths_for_cutoff(cutoff)
    data = csvFuturesSimData() if paths is None else csvFuturesSimData(csv_data_paths=paths)
    system = futures_system(data=data, config=config)
    return system


def maxabs(a: pd.Series, b: pd.Series):
    a, b = a.align(b, join="inner")
    d = (a - b).abs()
    return float(d.max()) if len(d.dropna()) else float("nan")


def n_diff(a, b, tol=1e-9):
    a, b = a.align(b, join="inner")
    both_nan = a.isna() & b.isna()
    d = ((a - b).abs() > tol) | (a.isna() != b.isna())
    return int((d & ~both_nan).sum()), int(len(a))
