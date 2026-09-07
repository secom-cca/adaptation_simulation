from __future__ import annotations

import argparse
import csv
from pathlib import Path
import statistics
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parent))

from scenario_factory import make_params, run_all_full_mana
from seed_search import summarize_result


SEVERE_CANDIDATES = [300_000_000, 330_000_000, 350_000_000, 400_000_000]
RESIDENT_CANDIDATES = [0.05, 0.10, 0.15, 0.20]
HOUSE_CANDIDATES = [8000, 8500, 9000]
PADDY_COEFS = [10.0, 12.5, 15.0]


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = (len(values) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    frac = index - lower
    return values[lower] * (1 - frac) + values[upper] * frac


def distribution_rows(seed_max: int, rcp: float) -> tuple[list[dict], list[dict]]:
    max_rows = []
    summaries = []
    for seed in range(seed_max + 1):
        results = run_all_full_mana(make_params(rcp, seed))
        for result in results:
            summary = summarize_result(result)
            summaries.append({"seed": seed, **summary})
            max_rows.append({
                "seed": seed,
                "scenario": result["scenario"],
                "label": result["label"],
                "max_flood_damage_jpy": summary["max_flood_damage_jpy"],
                "max_flood_2050_2055": summary["max_flood_2050_2055"],
                "max_flood_2065_2075": summary["max_flood_2065_2075"],
                "max_flood_2080_2100": summary["max_flood_2080_2100"],
            })
    return max_rows, summaries


def threshold_rows(summaries: list[dict]) -> list[dict]:
    rows = []
    target_scenarios = ["01_no_policy", "06_balanced", "02_hard_infra", "09_flood_neglect", "03_nature_based", "04_agri_rnd"]
    for threshold in SEVERE_CANDIDATES:
        for scenario in target_scenarios:
            scenario_rows = [row for row in summaries if row["scenario"] == scenario]
            rate = sum(1 for row in scenario_rows if row["max_flood_damage_jpy"] >= threshold) / max(len(scenario_rows), 1)
            rows.append({"metric": "severe_flood_threshold", "candidate": threshold, "scenario": scenario, "fire_rate": round(rate, 3)})
    for threshold in RESIDENT_CANDIDATES:
        for scenario in ["01_no_policy", "06_balanced", "05_relocation_capacity", "07_late_response"]:
            scenario_rows = [row for row in summaries if row["scenario"] == scenario]
            rate = sum(1 for row in scenario_rows if row["resident_capacity_low_t2"]) / max(len(scenario_rows), 1)
            rows.append({"metric": "resident_capacity_low_threshold_current_logic", "candidate": threshold, "scenario": scenario, "fire_rate": round(rate, 3)})
    for threshold in HOUSE_CANDIDATES:
        for scenario in ["01_no_policy", "06_balanced", "05_relocation_capacity", "09_flood_neglect"]:
            scenario_rows = [row for row in summaries if row["scenario"] == scenario]
            rate = sum(1 for row in scenario_rows if row["high_risk_houses_t2"]) / max(len(scenario_rows), 1)
            rows.append({"metric": "high_risk_houses_threshold_current_logic", "candidate": threshold, "scenario": scenario, "fire_rate": round(rate, 3)})
    return rows


def flood_distribution_summary(max_rows: list[dict]) -> list[dict]:
    rows = []
    for scenario in ["01_no_policy", "06_balanced", "02_hard_infra", "09_flood_neglect"]:
        values = [row["max_flood_damage_jpy"] for row in max_rows if row["scenario"] == scenario]
        rows.append({
            "scenario": scenario,
            "median": round(statistics.median(values), 1),
            "p75": round(percentile(values, 0.75), 1),
            "p90": round(percentile(values, 0.90), 1),
            "p95": round(percentile(values, 0.95), 1),
        })
    return rows


def paddy_rows(seed: int, rcp: float) -> list[dict]:
    rows = []
    for coef in PADDY_COEFS:
        for result in run_all_full_mana(make_params(rcp, seed, paddy_coef=coef)):
            if result["scenario"] not in {"03_nature_based", "06_balanced", "02_hard_infra"}:
                continue
            summary = summarize_result(result)
            rows.append({
                "seed": seed,
                "paddy_dam_flood_coef": coef,
                "scenario": result["scenario"],
                "label": result["label"],
                "max_flood_damage_jpy": summary["max_flood_damage_jpy"],
                "severe_flood_count": summary["severe_flood_count"],
                "major_flood_count": summary["major_flood_count"],
                "final_ecosystem_level": summary["final_ecosystem_level"],
                "paddy_dam_5mm_year": min((e["year"] for e in result["event_log"] if e["id"] == "paddy_dam_5mm"), default=None),
                "paddy_dam_full_year": min((e["year"] for e in result["event_log"] if e["id"] == "paddy_dam_full"), default=None),
            })
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-max", type=int, default=999)
    parser.add_argument("--seed", type=int, default=4)
    parser.add_argument("--rcp", type=float, default=4.5)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    max_rows, summaries = distribution_rows(args.seed_max, args.rcp)
    write_csv(args.output_dir / "flood_damage_distribution.csv", max_rows)
    write_csv(args.output_dir / "flood_damage_distribution_summary.csv", flood_distribution_summary(max_rows))
    write_csv(args.output_dir / "threshold_sensitivity_summary.csv", threshold_rows(summaries))
    write_csv(args.output_dir / "paddy_dam_coef_comparison.csv", paddy_rows(args.seed, args.rcp))


if __name__ == "__main__":
    main()
