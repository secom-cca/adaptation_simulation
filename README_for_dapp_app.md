# README for `dapp_app.py`

`dapp_app.py` は、Dynamic Adaptive Policy Pathways (DAPP) を Streamlit 上で実行・可視化するためのアプリです。

この版では、DAPP を「固定された政策経路図」としてではなく、**状態空間上の適応ルール**として扱います。つまり、同じ adaptive rule を多数の Monte Carlo シナリオに適用し、その結果として実現した政策・目的レジームの経路を比較します。

## 1. このアプリで何を見るのか

このアプリの中心的な問いは次の 3 つです。

1. ある適応ルールを使うと、どのような政策経路が実現しやすいか。
2. 目的レジーム、つまり「何を成功とみなすか」は、どのタイミングで変わるか。
3. 目的レジームを固定した DAPP と、内生的に切り替える DAPP では、頑健性・費用・被害・ロックインにどのような差が出るか。

ここで重要なのは、Objective Regime は政策そのものではない、という点です。

- Policy: 実際に実行する政策手段です。
- Objective Regime: その時点で何を成功とみなすかを定義する評価状態です。

たとえば `Agriculture-oriented` は「農業維持を重視する評価状態」であり、`Safety-oriented` は「洪水安全を重視する評価状態」です。これらは政策メニューではなく、政策を評価するための成功基準です。

## 2. 実行方法

リポジトリ直下で実行します。

```bash
streamlit run dapp_app.py
```

依存関係が未導入の場合は、通常は次のどちらかで環境を準備します。

```bash
poetry install
```

または

```bash
pip install -r requirements.txt
```

アプリはデフォルトで次のモジュールを使います。

- `backend.config`: デフォルトパラメータ、RCP 気候設定
- `backend.src.simulation`: 年次シミュレーション本体
- `dapp_app.py`: Streamlit UI、Monte Carlo 実行、DAPP ロジック、可視化

## 3. 基本概念

### Objective Regime

Objective Regime は「何を成功とみなすか」を定義します。

各レジームには次の要素があります。

- thresholds: 評価指標ごとの成功条件
- weight: ObjectiveStrain 計算時の重み
- strain_threshold: Objective ATP が発火する ObjectiveStrain の閾値
- min_strain_years: 何年連続で strain が高いと切替判定するか
- next_regime_candidates: 切替候補となる次の Objective Regime

例:

```text
Agriculture-oriented
  Flood Damage <= 1,000,000
  Crop Yield >= 4,700
  Ecosystem Level >= 70
  Resident Burden <= 100,000
```

### Policy Primitive

Policy Primitive は、実際に適用される政策手段です。

例:

- `NoRegret-Lite`
- `Nature-Boost`
- `Levee-Boost`
- `AgriR&D-Boost`
- `Relocation-Boost`
- `All-Boost`

これらは Objective Regime に固定されません。同じ政策でも、評価する Objective Regime が違えば成功・失敗の意味が変わります。

### Performance ATP

Performance ATP は、現在適用中の Objective Regime の thresholds を一定年数連続で満たせなかったときに発火します。

発火すると、policy decision mode に従って次期政策 `PolicyNext` が選ばれます。

### Objective ATP

Objective ATP は、ObjectiveStrain が高い状態が一定年数続いたときに発火します。

発火すると、次期 Objective Regime `ObjectiveRegimeNext` が選ばれます。必要に応じて、そのレジームに合う suggested policy も `SuggestedPolicyAfterRegimeSwitch` として記録されます。

### Applied と Next

このアプリでは、年 t に実際に適用された状態と、年 t の評価によって翌年以降に適用される状態を分けています。

- `PolicyApplied`: 年 t に実際に使われた政策
- `ObjectiveRegimeApplied`: 年 t に実際に使われた評価レジーム
- `PolicyNext`: 年 t の判定後に、年 t+1 から使う予定の政策
- `ObjectiveRegimeNext`: 年 t の判定後に、年 t+1 から使う予定の評価レジーム

したがって、切替が判断された年の `ObjectiveRegimeApplied` は旧レジームのままです。新レジームが実際に適用されるのは次の年からです。

## 4. UI の流れ

### 1. Objective Regime Definitions

Objective Regime を定義します。

ここでは、各レジームの thresholds、strain threshold、切替候補を編集します。

見るべき点:

- 閾値が厳しすぎないか
- `next_regime_candidates` が空でないか
- 使っている metric 名が simulator の出力列と一致しているか

### 2. Objective Regime switching settings

初期 Objective Regime と、Objective Regime の切替モードを選びます。

- `Fixed`: 目的レジームを固定する
- `Endogenous`: ObjectiveStrain によって目的レジームを内生的に切り替える

`ObjectiveStrain: lock-in weight` は重要です。この値を上げると、ロックイン的な政策が続いていること自体が ObjectiveStrain に反映されやすくなります。

### 3. Policy primitives

政策プリミティブを編集します。

このアプリでは、政策は Objective Regime に属していません。全政策プリミティブはグローバルな候補として扱われます。

### 4. Policy decision mode

Performance ATP が発火したときに、次の政策をどう選ぶかを設定します。

代表的には次の 2 つです。

- Reactive: ladder に従って次の政策へ進む
- Anticipatory: lookahead window 内の将来性能を比較して政策を選ぶ

### 5. Run DAPP

`Run DAPP (Monte Carlo)` を押すと、複数シナリオに同じ adaptive rule を適用します。

重要:

`occurrence_share` は「その経路自体の確率」ではありません。  
これは、**同じ adaptive rule を Monte Carlo シナリオ群に適用したとき、その実現経路が何割出現したか**を表します。

## 5. Results の読み方

### A) Adaptive Rule Summary

今回の実行条件の要約です。

確認する項目:

- Initial Objective Regime
- Objective Regime switching mode
- Policy decision mode
- Lookahead window
- ObjectiveStrain lock-in weight
- Performance ATP k
- Number of scenarios
- Number of objective regimes
- Number of policy primitives

ここは、結果を解釈するときの前提条件です。

### B) Representative Realized Pathways

Monte Carlo で実現した代表的な経路をまとめた表です。

例:

```text
Agriculture-oriented / NoRegret-Lite
→ Agriculture-oriented / Nature-Boost
→ Safety-oriented / Relocation-Boost
```

主な列:

- `representative_scenario_id`: その経路を代表するシナリオ ID
- `median_switch_years`: その経路群で典型的に切替が起きる年
- `objective_switch_metrics`: Objective Regime 切替時に支配的だった metric
- `performance_trigger_metrics`: Performance ATP を引き起こした metric
- `mean_InitialRegimeRobustness`: 初期レジーム基準での平均頑健性
- `mean_RegimeAwareRobustness`: 各年の適用レジーム基準での平均頑健性
- `mean_ObjectiveStrain`: 平均 ObjectiveStrain
- `mean_LockIn_Years`: ロックイン政策の平均年数
- `occurrence_count`: その経路が出現したシナリオ数
- `occurrence_share`: その経路が出現したシナリオ割合

読み方:

- 上位数経路に `occurrence_share` が集中している場合、adaptive rule は比較的安定した実現パターンを持ちます。
- 経路が細かく分散している場合、気候・需要・洪水などの不確実性に対して経路が敏感です。
- `objective_switch_metrics` に同じ metric が集中する場合、その指標が目的レジーム転換の主因です。

### C) Objective Regime Composition

年ごとに、どの Objective Regime が何%のシナリオで実際に適用されていたかを示します。

この図は `ObjectiveRegimeApplied` を使います。

読み方:

- `Agriculture-oriented` が長く残るなら、初期目的を維持しやすいルールです。
- `Safety-oriented` が増えるなら、洪水安全を成功基準にするシナリオが増えていると読めます。
- `Retreat-oriented` が増えるなら、曝露削減や撤退を成功基準にする状況が増えています。

### D) Policy Composition

年ごとに、どの政策が何%のシナリオで実際に適用されていたかを示します。

この図は `PolicyApplied` を使います。

読み方:

- 初期に柔軟な政策が多いなら、早期の不可逆コミットメントを避ける設計です。
- 後半に `Levee-Boost` や `Relocation-Boost` が増えるなら、リスクが顕在化した後に強い介入へ移っています。
- Objective Regime Composition と合わせて見ると、「成功基準の変化」と「政策選択の変化」が対応しているかを確認できます。

### E) Metro Map

Objective Regime と Policy の組み合わせを、時間バケットごとの状態遷移として可視化します。

この図も `ObjectiveRegimeApplied` / `PolicyApplied` を使います。

読み方:

- 太い線は多くのシナリオが通った実現経路です。
- 分岐が多い時点は、シナリオ間で適応判断が分かれた時期です。
- 同じ Objective Regime の中で政策だけ変わるのか、Objective Regime 自体も変わるのかを区別して見ます。

### F) Scorecards

シナリオごとの評価指標と、その集計を表示します。

特に重要な指標:

- `Initial-regime Robustness`
- `Regime-aware Robustness`
- `NPV Municipal Cost`
- `NPV Flood Damage`
- `Cumulative Total Cost`
- `Mean ObjectiveStrain`
- `Max ObjectiveStrain`
- `Lock-in Years`
- `Early Irreversible Commitment Years`
- `Option-preserving Share Early`
- `#PolicySwitches`
- `#ObjectiveRegimeSwitches`
- `ObjectiveRegimeSwitchYear`

Robustness の読み分け:

- `Initial-regime Robustness`: 全期間を初期 Objective Regime の thresholds で評価します。
- `Regime-aware Robustness`: 各年を、その年の `ObjectiveRegimeApplied` の thresholds で評価します。

典型的な解釈:

```text
Initial-regime Robustness 高い + Regime-aware Robustness 高い
  → 初期目的を維持したまま適応できている。

Initial-regime Robustness 低い + Regime-aware Robustness 高い
  → 初期目的は守れないが、目的を切り替えることで新しい成功基準には適応している。

Initial-regime Robustness 低い + Regime-aware Robustness 低い
  → 政策プリミティブ、閾値、切替ルールが不十分な可能性が高い。

Initial-regime Robustness 高い + Regime-aware Robustness 低い
  → 切替後のレジームが厳しすぎる、または切替先の選択が不適切な可能性がある。
```

### Threshold Satisfaction

主表示は 2 種類です。

- Active regime threshold satisfaction over time
- Initial regime threshold satisfaction over time

Active regime threshold satisfaction は、その年に実際に適用されていた `ObjectiveRegimeApplied` の thresholds を満たしているかを示します。

Initial regime threshold satisfaction は、全期間を初期 Objective Regime の thresholds で評価したものです。

All regime thresholds は補助表示です。細かい metric ごとの成否を確認したいときに使います。

### G) Fixed vs Endogenous Comparison

固定目的レジーム DAPP と、内生的目的レジーム DAPP を、同じ scenario seeds で比較します。

見るべき指標:

- `Initial-regime Robustness`
- `Regime-aware Robustness`
- `Cumulative Total Cost`
- `NPV Flood Damage`
- `Lock-in Years`
- `Option-preserving Share Early`
- `Mean ObjectiveStrain`
- `#ObjectiveRegimeSwitches`
- `Near-term policy divergence`

読み方:

Endogenous DAPP が Fixed DAPP より次の傾向を示すなら、目的レジームを内生的に切り替える価値があると解釈できます。

- Regime-aware Robustness が高い
- NPV Flood Damage が低い
- Lock-in Years が少ない
- Option-preserving Share Early が高い
- Cumulative Total Cost が大きく悪化していない

ただし、Regime-aware Robustness が高いだけでは十分ではありません。目的レジームを切り替えることで評価基準が変わるため、費用・被害・ロックインの指標とセットで判断する必要があります。

## 6. 結果から言えること

このアプリから直接言えることは、「この adaptive rule は、どのような状況で、どのような目的レジームと政策経路を実現しやすいか」です。

より具体的には、次のような問いに答えられます。

- 初期の農業重視目標は、どのくらいのシナリオで維持できるか。
- 安全重視や撤退重視へ目的レジームが変わるのは、何年ごろか。
- 目的レジームの切替は、Flood Damage、Crop Yield、Ecosystem Level など、どの指標に駆動されているか。
- 内生的に目的を切り替えることで、洪水被害やロックインは減るか。
- その改善は、費用増加に見合うか。
- 早期に不可逆な政策へ入りすぎていないか。

## 7. 注意点

### occurrence_share は経路確率ではない

Representative Pathways の `occurrence_share` は、その経路そのものの客観確率ではありません。

これは、与えられた Monte Carlo 設定と adaptive rule のもとで、その実現経路が何割観測されたかです。

### Objective Regime は政策戦略ではない

Objective Regime は「評価状態」です。

したがって、`Safety-oriented` になったからといって、必ず `Levee-Boost` を実行するわけではありません。実行政策は Performance ATP と policy decision mode によって選ばれます。

### 切替年の読み方

切替判断が年 t に起きた場合:

- 年 t の `ObjectiveRegimeApplied` は旧レジーム
- 年 t の `ObjectiveRegimeNext` は新レジーム
- 年 t+1 の `ObjectiveRegimeApplied` が新レジーム

これは、年 t の結果は年 t に実際に適用された政策・レジームで発生したものとして解釈するためです。

### lock-in weight の意味

`ObjectiveStrain: lock-in weight` を大きくすると、ロックイン的政策が続いていることが ObjectiveStrain に強く反映されます。

値を変えたときに見るべきもの:

- Mean ObjectiveStrain
- ObjectiveRegimeSwitchYear
- #ObjectiveRegimeSwitches
- Lock-in Years
- Representative Realized Pathways

## 8. よくある確認ポイント

### Objective ATP がまったく発火しない

次を確認してください。

- `strain_threshold` が高すぎないか
- `min_strain_years` が長すぎないか
- `next_regime_candidates` が空でないか
- thresholds の metric 名が simulator 出力列と一致しているか

### 経路が細かく分散しすぎる

次の可能性があります。

- Monte Carlo 不確実性が大きい
- thresholds が境界的で、小さな変動で ATP が発火している
- policy decision mode が lookahead に敏感すぎる
- switch penalty が低すぎる

### Regime-aware Robustness だけ高い

目的レジームを切り替えたことで、評価基準が変わっている可能性があります。

この場合は必ず次も確認してください。

- Initial-regime Robustness
- NPV Flood Damage
- Cumulative Total Cost
- Lock-in Years
- ObjectiveRegimeSwitchYear

### Endogenous DAPP の費用が高い

切替や強い政策介入によってコストが増えている可能性があります。

見るべき項目:

- Cumulative Municipal Cost
- Cumulative PolicySwitch Cost
- Cumulative RegimeSwitch Cost
- NPV Flood Damage
- Cumulative Total Cost

被害削減と費用増加のバランスで判断します。

## 9. まず見るべき最小セット

結果を素早く読むなら、まず次の順に見ます。

1. Representative Realized Pathways
2. Objective Regime Composition
3. Policy Composition
4. Initial-regime Robustness と Regime-aware Robustness
5. NPV Flood Damage と Cumulative Total Cost
6. Fixed vs Endogenous Comparison

この 6 点を見れば、DAPP が「どの経路を取りやすいか」「なぜ目的が変わるか」「その適応に価値があるか」を大まかに判断できます。

