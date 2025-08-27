# simulation_simple.py
# Purpose: 原型の参照モードを“軽量・透明”に再現するための最小実装
# 依存: numpy のみ

from typing import Dict, List
import numpy as np

# -----------------------------
# 共通の外生ドライバ（気候ストレス等）
# -----------------------------
def climate_stress(t: int, trend: float = 0.02, noise: float = 0.0, rng: np.random.Generator = None) -> float:
    """時間とともに高まる外生ストレス（気候・極端現象の代理）"""
    if rng is None:
        rng = np.random.default_rng(0)
    return max(0.0, trend * t + (rng.normal(0, noise) if noise > 0 else 0.0))

# -----------------------------
# 1) Fixes that Fail
#    短期対症療法が長期に露呈する
# -----------------------------
def step_fixes_that_fail(state: Dict[str, float], decision: Dict[str, float], params: Dict[str, float]) -> Dict[str, float]:
    """
    state: {damage, exposure}
    decision: {invest}  # 対症療法投資（例：堤防等）
    params: α短期効果, β暴露誘発, γ自然増
    """
    damage = state["damage"]
    exposure = state["exposure"]
    invest = decision.get("invest", 0.0)

    alpha = params.get("alpha_short", 0.5)   # 投資の即時被害削減係数
    beta  = params.get("beta_exposure", 0.2) # 投資が将来の暴露を増やす
    gamma = params.get("gamma_exposure", 0.01) # 都市化等の自然な暴露増

    # 短期は被害↓、ただし暴露↑ → 将来の被害↑
    new_exposure = max(0.0, exposure + beta * invest + gamma)
    new_damage   = max(0.0, damage - alpha * invest + 0.3 * new_exposure)

    return {"damage": new_damage, "exposure": new_exposure}

# -----------------------------
# 2) Shifting the Burden
#    対症療法に依存し根本原因が蓄積
# -----------------------------
def step_shifting_the_burden(state: Dict[str, float], decision: Dict[str, float], params: Dict[str, float]) -> Dict[str, float]:
    """
    state: {risk, root_cause}
    decision: {symptomatic, fundamental} # 対症療法, 根本対策（例：上流生態基盤整備）
    params: α対症効果, θ根本効果, δ根本原因の自然蓄積
    """
    risk = state["risk"]
    root = state["root_cause"]
    symptomatic = decision.get("symptomatic", 0.0)
    fundamental = decision.get("fundamental", 0.0)

    alpha = params.get("alpha_symptomatic", 0.6) # すぐ効く
    theta = params.get("theta_fundamental", 0.2) # 遅れて効く/効きは穏やか
    delta = params.get("delta_accum", 0.03)      # 根本原因の自然な積み上がり

    new_root = max(0.0, root + delta - theta * fundamental)
    # 根本原因が高いほど基礎リスク↑、対症で一時的に↓
    new_risk = max(0.0, risk - alpha * symptomatic + 0.5 * new_root)

    return {"risk": new_risk, "root_cause": new_root}

# -----------------------------
# 3) Limits to Growth
#    努力の効果がストレスで頭打ち
# -----------------------------
def step_limits_to_growth(state: Dict[str, float], decision: Dict[str, float], params: Dict[str, float], t: int) -> Dict[str, float]:
    """
    state: {benefit}
    decision: {effort}
    params: 効率α, ストレス感度β, 気候ストレストレンドtrend
    """
    benefit = state["benefit"]
    effort  = decision.get("effort", 0.0)

    alpha = params.get("alpha_eff", 1.0)
    beta  = params.get("beta_stress", 2.0)
    trend = params.get("stress_trend", 0.02)

    stress = climate_stress(t, trend=trend)
    inc = alpha * effort / (1.0 + beta * stress)  # ストレスが高いほど効果逓減
    new_benefit = max(0.0, benefit + inc - 0.01*benefit)  # 自然減少や維持コストを微小に

    return {"benefit": new_benefit}

# -----------------------------
# 4) Success to the Successful
#    強者への資源集中→格差拡大
# -----------------------------
def step_success_to_success(state: Dict[str, float], decision: Dict[str, float], params: Dict[str, float]) -> Dict[str, float]:
    """
    state: {res_A, res_B}  # 地域A/Bのレジリエンス
    decision: {resources}  # 年間総資源量
    params: 強化係数α
    """
    res_A = state["res_A"]
    res_B = state["res_B"]
    resources = max(0.0, decision.get("resources", 1.0))
    alpha = params.get("alpha_gain", 0.2)

    # 現状の強さに比例して配分（バイアス）
    share_A = res_A / (res_A + res_B + 1e-9)
    inv_A = resources * share_A
    inv_B = resources * (1.0 - share_A)

    new_A = max(0.0, res_A + alpha * inv_A - 0.01*res_A)
    new_B = max(0.0, res_B + alpha * inv_B - 0.01*res_B)

    return {"res_A": new_A, "res_B": new_B}

# -----------------------------
# 5) Escalation
#    被害→財政圧迫→投資減→被害増
# -----------------------------
def step_escalation(state: Dict[str, float], decision: Dict[str, float], params: Dict[str, float], t: int) -> Dict[str, float]:
    """
    state: {budget, protection, damage}
    decision: {base_invest}  # 余力があれば行う基礎投資
    params: 被害→予算減α, 投資→防護β, ストレス→被害γ
    """
    budget = state["budget"]
    prot   = state["protection"]
    damage = state["damage"]

    base_invest = decision.get("base_invest", 1.0)
    a = params.get("alpha_damage_to_budget", 0.5)
    b = params.get("beta_invest_to_prot", 0.3)
    g = params.get("gamma_stress_to_damage", 1.0)
    trend = params.get("stress_trend", 0.03)

    # 予算は被害で削られる
    new_budget = max(0.0, budget - a * damage + 0.1)  # 税収等の基礎収入0.1
    invest = max(0.0, min(new_budget, base_invest))   # 予算内で投資
    new_budget -= invest

    # 投資が防護水準を押し上げるが、劣化もする
    new_prot = max(0.0, prot + b * invest - 0.02 * prot)

    # ストレスが防護を上回る分だけ被害
    stress = climate_stress(t, trend=trend)
    new_damage = max(0.0, g * max(stress - 0.05*new_prot, 0.0))

    return {"budget": new_budget, "protection": new_prot, "damage": new_damage}

# -----------------------------
# シミュレータ：任意原型を走らせる
# -----------------------------
def simulate_archetype(kind: str, T: int = 75, seed: int = 0,
                       init: Dict[str, float] = None,
                       policy: Dict[str, float] = None,
                       params: Dict[str, float] = None) -> List[Dict[str, float]]:
    """
    kind: 'fixes', 'shift', 'limits', 'success', 'escalation'
    T: 期間（年）
    init: 初期状態
    policy: 年を通じて一定の意思決定強度（必要に応じて年次で変えてもよい）
    params: 原型パラメタ
    return: 年ごとの状態のリスト（可視化しやすいdict）
    """
    rng = np.random.default_rng(seed)
    if init is None:   init = {}
    if policy is None: policy = {}
    if params is None: params = {}

    traj = []
    # 初期値デフォルト
    if kind == "fixes":
        state = {"damage": init.get("damage", 10.0), "exposure": init.get("exposure", 5.0)}
    elif kind == "shift":
        state = {"risk": init.get("risk", 8.0), "root_cause": init.get("root_cause", 2.0)}
    elif kind == "limits":
        state = {"benefit": init.get("benefit", 0.0)}
    elif kind == "success":
        state = {"res_A": init.get("res_A", 5.0), "res_B": init.get("res_B", 5.0)}
    elif kind == "escalation":
        state = {"budget": init.get("budget", 2.0), "protection": init.get("protection", 5.0), "damage": init.get("damage", 0.5)}
    else:
        raise ValueError("unknown archetype kind")

    for t in range(T):
        year = t  # 相対年
        if kind == "fixes":
            state = step_fixes_that_fail(state, {"invest": policy.get("invest", 1.0)}, params)
            out = {"t": year, **state}
        elif kind == "shift":
            state = step_shifting_the_burden(state,
                                             {"symptomatic": policy.get("symptomatic", 1.0),
                                              "fundamental": policy.get("fundamental", 0.2)},
                                             params)
            out = {"t": year, **state}
        elif kind == "limits":
            state = step_limits_to_growth(state, {"effort": policy.get("effort", 1.0)}, params, t)
            out = {"t": year, **state}
        elif kind == "success":
            state = step_success_to_success(state, {"resources": policy.get("resources", 2.0)}, params)
            out = {"t": year, **state, "gap": abs(state["res_A"] - state["res_B"])}
        elif kind == "escalation":
            state = step_escalation(state, {"base_invest": policy.get("base_invest", 1.0)}, params, t)
            out = {"t": year, **state}
        traj.append(out)

    return traj

# -----------------------------
# 使い方（例）
# -----------------------------
if __name__ == "__main__":
    # 例1: Fixes that Fail
    fixes = simulate_archetype("fixes", T=60, policy={"invest": 1.0},
                               params={"alpha_short": 0.7, "beta_exposure": 0.25, "gamma_exposure": 0.01})
    # 例2: Shifting the Burden（対症1.0, 根本0.1）
    shift = simulate_archetype("shift", T=60, policy={"symptomatic": 1.0, "fundamental": 0.1})
    # 例3: Limits to Growth（ストレス強）
    limits = simulate_archetype("limits", T=60, policy={"effort": 1.0}, params={"beta_stress": 3.0, "stress_trend": 0.03})
    # 例4: Success to the Successful（資源2.0）
    success = simulate_archetype("success", T=60, policy={"resources": 2.0})
    # 例5: Escalation（基礎投資1.0）
    esc = simulate_archetype("escalation", T=60, policy={"base_invest": 1.0}, params={"stress_trend": 0.04})

    # 可視化は外部ノートブックや簡単なプロットで（本ファイルはデータ出力専用を想定）
    print(fixes[-3:]); print(shift[-3:]); print(limits[-3:]); print(success[-3:]); print(esc[-3:])
