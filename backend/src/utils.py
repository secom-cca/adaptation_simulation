import numpy as np
import pandas as pd


BENCHMARK = {
    "収量": dict(best=10_000, worst=0, invert=False),
    "洪水被害": dict(best=0, worst=200_000_000, invert=True),
    "生態系": dict(best=100, worst=0, invert=False),
    "予算": dict(best=0, worst=1_000_000_000, invert=True),
    "森林面積": dict(best=10_000, worst=0, invert=False),
    "住民負担": dict(best=0, worst=100_000, invert=True),
}

BLOCKS = [
    (2026, 2050, "2026-2050"),
    (2051, 2075, "2051-2075"),
    (2076, 2100, "2076-2100"),
]


def calculate_scenario_indicators(df: pd.DataFrame) -> dict:
    last_ecosystem = df.loc[df["Year"] == 2100, "Ecosystem Level"]
    ecosystem_level_end = (
        last_ecosystem.values[0] if not last_ecosystem.empty else float("nan")
    )
    return {
        "収量": df["Crop Yield"].sum(),
        "洪水被害": df["Flood Damage"].sum(),
        "生態系": ecosystem_level_end,
        "森林面積": df["Forest Area"].mean(),
        "予算": df["Municipal Cost"].sum(),
        "住民負担": df["Resident Burden"].sum(),
    }


def aggregate_blocks(df: pd.DataFrame) -> list[dict]:
    records = []
    for start, end, label in BLOCKS:
        mask = (df["Year"] >= start) & (df["Year"] <= end)
        if df.loc[mask].empty:
            continue
        raw = _raw_values(df, start, end)
        score = {key: _scale_to_100(value, key) for key, value in raw.items()}
        total = float(np.mean(list(score.values())))
        records.append(
            dict(period=label, raw=raw, score=score, total_score=total)
        )
    return records


def _scale_to_100(raw_val: float, metric: str) -> float:
    benchmark = BENCHMARK[metric]
    if benchmark["worst"] < benchmark["best"]:
        value = np.clip(raw_val, benchmark["worst"], benchmark["best"])
    else:
        value = np.clip(raw_val, benchmark["best"], benchmark["worst"])
    if benchmark["invert"]:
        score = 100 * (benchmark["worst"] - value) / (
            benchmark["worst"] - benchmark["best"]
        )
    else:
        score = 100 * (value - benchmark["worst"]) / (
            benchmark["best"] - benchmark["worst"]
        )
    return float(np.round(score, 1))


def _raw_values(df: pd.DataFrame, start: int, end: int) -> dict:
    mask = (df["Year"] >= start) & (df["Year"] <= end)
    return {
        "収量": df.loc[mask, "Crop Yield"].sum(),
        "洪水被害": df.loc[mask, "Flood Damage"].sum(),
        "予算": df.loc[mask, "Municipal Cost"].sum(),
        "住民負担": df.loc[mask, "Resident Burden"].sum(),
        "生態系": df.loc[mask, "Ecosystem Level"].mean(),
        "森林面積": df.loc[mask, "Forest Area"].mean(),
    }


def estimate_rice_yield_loss(
    temp_mean_annual: float,
    high_temp_tolerance_level: float,
    base_min_temp: float = 20.0,
    base_opt_temp: float = 22.0,
    base_turn_point_temp: float = 30.0,
    irrigation_mm: float = 0.0,
    I50: float = 200.0,
    k_cool: float = 0.004,
    water_supply_ratio: float = 1.0,
    cooling_cap_degC: float = 2.0,
):
    """実効登熟期温度から、収量損失率と冷却の発動率を計算する。"""
    temp_ripening = temp_mean_annual + 6.0
    opt_temp = base_opt_temp + high_temp_tolerance_level
    turn_point_temp = base_turn_point_temp + high_temp_tolerance_level

    if temp_ripening <= opt_temp:
        activation = 0.0
    elif temp_ripening >= turn_point_temp:
        activation = 1.0
    else:
        activation = (temp_ripening - opt_temp) / max(
            1e-9, turn_point_temp - opt_temp
        )

    if irrigation_mm > 0 and water_supply_ratio > 0 and activation > 0:
        saturation = irrigation_mm / (irrigation_mm + I50)
        cooling = (
            k_cool
            * saturation
            * max(0.0, min(1.0, water_supply_ratio))
            * activation
        )
        cooling = max(0.0, min(cooling, cooling_cap_degC))
    else:
        cooling = 0.0

    effective_temp = temp_ripening - cooling
    if effective_temp <= base_min_temp:
        loss = (base_min_temp - effective_temp) * 0.10
    elif effective_temp <= opt_temp:
        loss = 0.0
    elif effective_temp <= turn_point_temp:
        loss = (effective_temp - opt_temp) * 0.04
    else:
        loss = (turn_point_temp - opt_temp) * 0.04 + (
            effective_temp - turn_point_temp
        ) * 0.10

    return max(0.0, min(loss, 1.0)), activation
