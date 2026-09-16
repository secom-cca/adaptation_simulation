"""Read-only score, policy, climate, and ecosystem sensitivity verification."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from config import DEFAULT_PARAMS, rcp_climate_params  # noqa: E402
from simulation import POLICY_KEYS, calculate_budget_components, simulate_year  # noqa: E402
from scenario_factory import INITIAL_VALUES  # noqa: E402

PERIODS = ((2050, 2026, 2050), (2075, 2051, 2075), (2100, 2076, 2100))
TURN_STARTS = (2026, 2051, 2076)
ZERO_POLICY = {key: 0.0 for key in POLICY_KEYS}
POLICY_CASES = {
    "No Policy": None, "Forest": "planting_trees_amount",
    "Levee": "dam_levee_construction_cost", "Paddy Dam": "paddy_dam_construction_cost",
    "Relocation": "house_migration_amount", "Preparedness": "capacity_building_cost",
    "Agri R&D": "agricultural_RnD_cost", "Balanced": "balanced",
}


def make_params(rcp: float, overrides: dict[str, float] | None = None) -> dict:
    params = deepcopy(DEFAULT_PARAMS)
    params.update(rcp_climate_params[rcp])
    params.update(overrides or {})
    return params


def allowed(key: str, available: float, cumulative: dict[str, float], params: dict) -> float:
    rule = params["POLICY_MANA_RULES"].get(key, {})
    amount = max(0.0, available)
    if rule.get("max_mana_per_turn") is not None:
        amount = min(amount, float(rule["max_mana_per_turn"]))
    if rule.get("cumulative_mana_cap") is not None:
        amount = min(amount, max(0.0, float(rule["cumulative_mana_cap"]) - cumulative[key]))
    minimum = rule.get("min_mana_per_use")
    return amount if minimum is None or amount >= float(minimum) else 0.0


def turn_policy(strategy: str | None, available: float, cumulative: dict[str, float], params: dict) -> dict[str, float]:
    decision = dict(ZERO_POLICY)
    if strategy is None:
        return decision
    if strategy != "balanced":
        decision[strategy] = allowed(strategy, available, cumulative, params)
        return decision
    remaining = max(0.0, available)
    minimums = {
        key: float(params["POLICY_MANA_RULES"].get(key, {}).get("min_mana_per_use") or 0.0)
        for key in POLICY_KEYS
    }
    eligible = [key for key in POLICY_KEYS if allowed(key, available, cumulative, params) > 0]
    if sum(minimums[key] for key in eligible) <= remaining:
        for key in eligible:
            decision[key] = minimums[key]
            remaining -= minimums[key]
    else:
        eligible = [key for key in eligible if minimums[key] <= remaining / max(len(eligible), 1)]
    active = eligible
    while active and remaining > 1e-9:
        share, spent, next_active = remaining / len(active), 0.0, []
        for key in active:
            room = allowed(key, available, cumulative, params) - decision[key]
            add = min(share, max(0.0, room))
            decision[key] += add
            spent += add
            if room > add + 1e-9:
                next_active.append(key)
        if spent <= 1e-9:
            break
        remaining -= spent
        active = next_active
    for key in POLICY_KEYS:
        minimum = params["POLICY_MANA_RULES"].get(key, {}).get("min_mana_per_use")
        if minimum is not None and 0 < decision[key] < float(minimum):
            decision[key] = 0.0
    return decision


def run(rcp: float, strategy: str | None, overrides: dict[str, float] | None = None) -> list[dict]:
    params, state, rows = make_params(rcp, overrides), deepcopy(INITIAL_VALUES), []
    cumulative = {key: 0.0 for key in POLICY_KEYS}
    previous_turn_avg_flood = 0.0
    for turn_start in TURN_STARTS:
        state["last_25y_avg_flood_damage_jpy"] = previous_turn_avg_flood
        available = calculate_budget_components(turn_start, state, params)["available_budget_mana"]
        decision = turn_policy(strategy, available, cumulative, params)
        for key in POLICY_KEYS:
            cumulative[key] += decision[key]
        turn_rows = []
        for year in range(turn_start, min(turn_start + 25, 2101)):
            state["last_25y_avg_flood_damage_jpy"] = previous_turn_avg_flood
            values = {**decision, "year": year, "cp_climate_params": rcp, "transportation_invest": 0.0}
            state, output = simulate_year(year, state, values, params, fixed_seed=True)
            rows.append(output)
            turn_rows.append(output)
        previous_turn_avg_flood = sum(float(row["Flood Damage JPY"]) for row in turn_rows) / len(turn_rows)
    return rows


def aggregate(rows: list[dict], start: int, end: int) -> dict[str, float]:
    selected = [row for row in rows if start <= int(row["Year"]) <= end]
    average = lambda key: sum(float(row[key]) for row in selected) / len(selected)
    return {"flood": sum(float(row["Flood Damage JPY"]) for row in selected),
            "crop": average("Crop Yield"), "ecosystem": average("Ecosystem Level")}


def index_score(actual: float, reference: float, lower_is_better: bool) -> float:
    if lower_is_better:
        if actual == 0:
            return 100.0 if reference == 0 else float("inf")
        return 100.0 * reference / actual
    if reference == 0:
        return 100.0 if actual == 0 else float("inf")
    return 100.0 * actual / reference


def summarize(rows: list[dict], reference: dict[int, dict[str, float]]) -> dict[int, dict[str, float]]:
    result = {}
    for target, start, end in PERIODS:
        raw = aggregate(rows, start, end)
        scores = {key: index_score(raw[key], reference[target][key], key == "flood") for key in raw}
        result[target] = {**raw, **{f"{key}_score": value for key, value in scores.items()},
                          "mean_score": sum(scores.values()) / 3}
    return result


def print_rows(title: str, cases: dict[str, dict[int, dict[str, float]]], raw: bool = True) -> None:
    print(f"\n## {title}")
    print("case | year | " + ("flood_raw | " if raw else "") + "flood_score | "
          + ("crop_raw | " if raw else "") + "crop_score | "
          + ("ecosystem_raw | " if raw else "") + "ecosystem_score | mean_score")
    for name, periods in cases.items():
        for year, row in periods.items():
            values = [name, str(year)]
            for key in ("flood", "crop", "ecosystem"):
                if raw:
                    values.append(f"{row[key]:.3f}")
                values.append(f"{row[key + '_score']:.3f}")
            values.append(f"{row['mean_score']:.3f}")
            print(" | ".join(values))


def main() -> None:
    reference_rows = run(0.0, None)
    reference = {year: aggregate(reference_rows, start, end) for year, start, end in PERIODS}
    climate = {name: summarize(run(rcp, None), reference) for name, rcp in
               (("Current", 0.0), ("RCP1.9", 1.9), ("RCP4.5", 4.5), ("RCP8.5", 8.5))}
    print_rows("Climate scenarios (same no-policy strategy and seed)", climate)
    policies = {name: summarize(run(4.5, strategy), reference) for name, strategy in POLICY_CASES.items()}
    print_rows("RCP4.5 policy scenarios", policies, raw=False)

    specs = {"ecosystem_threshold": "ecosystem_threshold",
             "forest_degradation_rate_base": "forest_degradation_rate",
             "levee_ecosystem_damage_coef": "levee_ecosystem_damage_coef",
             "forest_ecosystem_boost_coef": "forest_ecosystem_boost_coef"}
    print("\n## Ecosystem OAT sensitivity (RCP4.5 Balanced)")
    print("parameter | multiplier | year | ecosystem_raw | ecosystem_score")
    for label, key in specs.items():
        base = float(DEFAULT_PARAMS[key])
        for multiplier in (0.75, 1.0, 1.25):
            periods = summarize(run(4.5, "balanced", {key: base * multiplier}), reference)
            for year, row in periods.items():
                print(f"{label} | {multiplier:.2f} | {year} | {row['ecosystem']:.3f} | {row['ecosystem_score']:.3f}")


if __name__ == "__main__":
    main()
