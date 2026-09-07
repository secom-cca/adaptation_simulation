from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parent))

from scenario_factory import SCENARIO_LABELS, make_params, run_all_full_mana


def event_years(events, prefix: str) -> list[int]:
    return [int(event["year"]) for event in events if str(event.get("id", "")).startswith(prefix)]


def first_year(events, prefixes: tuple[str, ...]):
    years = [int(event["year"]) for event in events if str(event.get("id", "")).startswith(prefixes)]
    return min(years) if years else None


def summarize_result(result: dict) -> dict:
    events = result["event_log"]
    rows = result["rows"]
    rain_events = [
        (int(event["year"]), float(event.get("value") or 0.0))
        for event in events
        if str(event.get("id", "")).startswith(("heavy_rain_", "extreme_rain_", "extreme_rain_record_"))
    ]
    return {
        "scenario": result["scenario"],
        "label": result["label"],
        "rain_events": rain_events,
        "severe_flood_count": len(event_years(events, "severe_flood_damage_")),
        "major_flood_count": len(event_years(events, "major_flood_damage_")),
        "flood_notice_count": len(event_years(events, "flood_damage_")),
        "severe_flood_years": ",".join(map(str, event_years(events, "severe_flood_damage_"))),
        "major_flood_years": ",".join(map(str, event_years(events, "major_flood_damage_"))),
        "crop_low_year": first_year(events, ("crop_production_low",)),
        "ecosystem_low_year": first_year(events, ("ecosystem_low",)),
        "ecosystem_critical_year": first_year(events, ("ecosystem_critical",)),
        "resident_capacity_low_t2": first_year(events, ("resident_capacity_low_turn2_summary",)),
        "high_risk_houses_t2": first_year(events, ("high_risk_houses_unmanaged_turn2_summary",)),
        "max_flood_damage_jpy": round(result["max_flood_damage_jpy"], 1),
        "max_flood_2050_2055": round(max((row.get("Flood Damage JPY", 0.0) for row in rows if 2050 <= row.get("Year") <= 2055), default=0.0), 1),
        "max_flood_2065_2075": round(max((row.get("Flood Damage JPY", 0.0) for row in rows if 2065 <= row.get("Year") <= 2075), default=0.0), 1),
        "max_flood_2080_2100": round(max((row.get("Flood Damage JPY", 0.0) for row in rows if 2080 <= row.get("Year") <= 2100), default=0.0), 1),
        "final_available_budget_mana": round(result["final_available_budget_mana"], 3),
        "final_crop_yield": round(result["final_crop_yield"], 1),
        "final_ecosystem_level": round(result["final_ecosystem_level"], 2),
        "final_risky_houses": round(result["final_risky_houses"], 1),
        "final_resident_capacity": round(result["final_resident_capacity"], 3),
    }


def score_seed(summaries: list[dict]) -> tuple[int, dict]:
    by_name = {row["scenario"]: row for row in summaries}
    rain_events = by_name["01_no_policy"]["rain_events"]
    rain_count = len(rain_events)
    score = 0
    reasons = {}
    turn_counts = [
        sum(1 for year, _ in rain_events if 2026 <= year <= 2050),
        sum(1 for year, _ in rain_events if 2051 <= year <= 2075),
        sum(1 for year, _ in rain_events if 2076 <= year <= 2100),
    ]
    checks = {
        "shock_2050_2055": any(2050 <= year <= 2055 and rain >= 250 for year, rain in rain_events),
        "shock_2065_2075": any(2065 <= year <= 2075 and rain >= 210 for year, rain in rain_events),
        "shock_2080_2100": any(2080 <= year <= 2100 and rain >= 220 for year, rain in rain_events),
        "rain_count_good": 6 <= rain_count <= 14,
        "rain_counts_increase": turn_counts[0] <= turn_counts[1] <= turn_counts[2],
        "no_policy_severe": by_name["01_no_policy"]["severe_flood_count"] >= 1,
        "neglect_or_agri_severe": max(by_name["09_flood_neglect"]["severe_flood_count"], by_name["04_agri_rnd"]["severe_flood_count"], by_name["03_nature_based"]["severe_flood_count"]) >= 1,
        "balanced_avoids_severe": by_name["06_balanced"]["severe_flood_count"] == 0,
        "hard_less_than_no_policy": by_name["02_hard_infra"]["severe_flood_count"] < by_name["01_no_policy"]["severe_flood_count"],
        "resident_prompt_no_policy": bool(by_name["01_no_policy"]["resident_capacity_low_t2"]),
        "housing_prompt_no_policy": bool(by_name["01_no_policy"]["high_risk_houses_t2"]),
        "balanced_no_resident_prompt": not by_name["06_balanced"]["resident_capacity_low_t2"] and not by_name["06_balanced"]["high_risk_houses_t2"],
        "relocation_no_resident_prompt": not by_name["05_relocation_capacity"]["resident_capacity_low_t2"] and not by_name["05_relocation_capacity"]["high_risk_houses_t2"],
        "rnd_delays_crop": (by_name["04_agri_rnd"]["crop_low_year"] or 9999) > (by_name["01_no_policy"]["crop_low_year"] or 9999),
        "infra_ecosystem_worse": (by_name["02_hard_infra"]["ecosystem_low_year"] or 9999) < (by_name["03_nature_based"]["ecosystem_low_year"] or 9999),
    }
    weights = {
        "shock_2050_2055": 20, "shock_2065_2075": 20, "shock_2080_2100": 10,
        "rain_count_good": 10, "rain_counts_increase": 20,
        "no_policy_severe": 20, "neglect_or_agri_severe": 20, "balanced_avoids_severe": 20,
        "hard_less_than_no_policy": 20, "resident_prompt_no_policy": 15,
        "housing_prompt_no_policy": 15, "balanced_no_resident_prompt": 15,
        "relocation_no_resident_prompt": 15, "rnd_delays_crop": 10,
        "infra_ecosystem_worse": 10,
    }
    for key, ok in checks.items():
        if ok:
            score += weights[key]
    severe_counts = [row["severe_flood_count"] for row in summaries]
    if sum(1 for count in severe_counts if count > 0) >= len(severe_counts) - 1:
        score -= 20
    if sum(severe_counts) == 0:
        score -= 20
    if rain_count > 18:
        score -= 10
    if rain_count < 4:
        score -= 10
    reasons.update(checks)
    reasons["rain_count"] = rain_count
    reasons["turn_rain_counts"] = turn_counts
    return score, reasons


def run_search(seed_max: int, rcp: float, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ranked = []
    scenario_rows = []
    budget_rows = []
    for seed in range(seed_max + 1):
        params = make_params(rcp, seed)
        results = run_all_full_mana(params)
        summaries = [summarize_result(result) for result in results]
        score, reasons = score_seed(summaries)
        no_policy_rain = summaries[0]["rain_events"]
        ranked.append({
            "seed": seed,
            "score": score,
            "rain_events": json.dumps(no_policy_rain, ensure_ascii=False),
            "rain_count": reasons["rain_count"],
            "turn_rain_counts": json.dumps(reasons["turn_rain_counts"]),
            **{key: value for key, value in reasons.items() if isinstance(value, bool)},
        })
        if seed < 100 or score >= 130:
            for summary in summaries:
                scenario_rows.append({"seed": seed, **{k: v for k, v in summary.items() if k != "rain_events"}, "rain_events": json.dumps(summary["rain_events"], ensure_ascii=False)})
            for result in results:
                for row in result["budget_log"]:
                    budget_rows.append({"seed": seed, "scenario": result["scenario"], "label": result["label"], **row})

    ranked.sort(key=lambda row: row["score"], reverse=True)
    write_csv(output_dir / "seed_search_results.csv", ranked)
    top_seeds = {row["seed"] for row in ranked[:20]}
    write_csv(output_dir / "top_seed_event_summary.csv", [row for row in scenario_rows if row["seed"] in top_seeds])
    write_csv(output_dir / "full_mana_scenario_results.csv", [row for row in budget_rows if row["seed"] in top_seeds])


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
    parser.add_argument("--rcp", type=float, default=4.5)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    run_search(args.seed_max, args.rcp, args.output_dir)


if __name__ == "__main__":
    main()
