"""Independent check of the reserve prior; does not run the legacy policy search."""
from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROBABILITY = "Шанс геологического успеха"
MU = "Параметр mu для извлекаемых запасов нефти"
SIGMA = "Параметр sigma для извлекаемых запасов нефти"
SHIFT = "Параметр смещение для извлекаемых запасов нефти"


def prior_moments(p: float, mu: float, sigma: float) -> tuple[float, float]:
    """Mean and variance of Bernoulli(p) * LogNormal(mu, sigma)."""
    if not np.isfinite([p, mu, sigma]).all() or not 0 <= p <= 1 or sigma < 0:
        raise ValueError("Require finite parameters, 0 <= p <= 1 and sigma >= 0")
    mean = p * np.exp(mu + sigma * sigma / 2)
    variance = p * np.exp(2 * mu + 2 * sigma * sigma) - mean * mean
    return float(mean), float(max(0.0, variance))


def sample_prior(rng: np.random.Generator, p: float, mu: float,
                 sigma: float, draws: int) -> np.ndarray:
    prior_moments(p, mu, sigma)
    if draws < 2:
        raise ValueError("At least two draws are required")
    success = rng.random(draws) < p
    return success * rng.lognormal(mu, sigma, draws)


def load_prospects(path: Path) -> pd.DataFrame:
    with ZipFile(path) as archive:
        is_ods = ("mimetype" in archive.namelist() and
                  archive.read("mimetype").strip() == b"application/vnd.oasis.opendocument.spreadsheet")
    frame = pd.read_excel(path, sheet_name="Геология", engine="odf" if is_ods else "openpyxl")
    required = [PROBABILITY, MU, SIGMA]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing reserve parameters: {sorted(missing)}")
    frame = frame.dropna(subset=required, how="all").copy()
    if frame.empty or frame[required].isna().any().any():
        raise ValueError("Reserve parameters must be present for every prospect")
    if SHIFT in frame and not (frame[SHIFT].fillna(0) == 0).all():
        raise ValueError("This checker supports only the zero-displacement prior")
    for row in frame.to_dict("records"):
        prior_moments(float(row[PROBABILITY]), float(row[MU]), float(row[SIGMA]))
    return frame


def audit(frame: pd.DataFrame, draws: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = []
    for index, row in enumerate(frame.to_dict("records"), start=1):
        p, mu, sigma = (float(row[key]) for key in [PROBABILITY, MU, SIGMA])
        mean, variance = prior_moments(p, mu, sigma)
        samples = sample_prior(rng, p, mu, sigma, draws)
        se = np.sqrt(variance / draws)
        sample_mean = float(samples.mean())
        records.append(dict(prospect=index, probability=p, mu=mu, sigma=sigma,
                            analytic_mean=mean, simulated_mean=sample_mean,
                            mc_standard_error=float(se),
                            standardised_error=float((sample_mean - mean) / se) if se else 0.0,
                            observed_failure_rate=float((samples == 0).mean()),
                            draws=draws, seed=seed))
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, default=ROOT / "Датасет.xlsx")
    parser.add_argument("--draws", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "reserve_audit.csv")
    args = parser.parse_args()
    if args.draws < 2:
        parser.error("--draws must be at least 2")
    result = audit(load_prospects(args.workbook), args.draws, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print("Independent reserve-prior check (not a legacy investment-policy run)")
    print(result[["prospect", "analytic_mean", "simulated_mean", "mc_standard_error",
                  "standardised_error"]].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"Saved {len(result)} prospects to {args.output}")
    print("Standard errors describe simulation noise with fixed parameters, not geological uncertainty.")


if __name__ == "__main__":
    main()
