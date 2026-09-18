import React, { useEffect } from 'react'
import s from './ModelDetails.module.css'

const RCP_ROWS = [
  { rcp: '現在気候', value: 0, temp: 0, frequency: 0, intensity: 0 },
  { rcp: 'RCP1.9', value: 1.9, temp: 0.020, frequency: 0.010, intensity: 0.020 },
  { rcp: 'RCP2.6', value: 2.6, temp: 0.025, frequency: 0.018, intensity: 0.025 },
  { rcp: 'RCP4.5', value: 4.5, temp: 0.035, frequency: 0.030, intensity: 0.035 },
  { rcp: 'RCP6.0', value: 6.0, temp: 0.045, frequency: 0.050, intensity: 0.045 },
  { rcp: 'RCP8.5', value: 8.5, temp: 0.060, frequency: 0.075, intensity: 0.060 },
]

const POLICY_ROWS = [
  ['植林・森林保全', '1点以上', '上限なし', '1点 = 年間約8.66千本。30年後に森林面積へ反映'],
  ['住宅移転', '1点以上', '累積20点', '1点 = 年間約20.5戸を移転。将来のインフラ維持負担が増加'],
  ['堤防・河川改修', '5点以上', '上限なし', '累積投資が閾値を超えると堤防高が20mm上昇'],
  ['田んぼダム', '1点以上', '各ターン・累積6点', '貯留効果を最大10mmまで増加。収量へ最大1%の影響'],
  ['防災訓練', '1点以上', '各ターン1点', '住民防災能力を毎年改善。ただし年5%減衰'],
  ['農業R&D', '1点以上', '各ターン2点', '累積投資により高温耐性を0.2℃ずつ、最大2.5℃まで改善'],
]

function Formula({ children }) {
  return <div className={s.formula}>{children}</div>
}

function ParameterTable({ rows }) {
  return (
    <div className={s.tableWrap}>
      <table className={s.parameterTable}>
        <thead><tr><th>パラメータ</th><th>設定値</th><th>意味</th></tr></thead>
        <tbody>{rows.map(row => <tr key={row[0]}><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td></tr>)}</tbody>
      </table>
    </div>
  )
}

export default function ModelDetails({ rcpValue, onClose }) {
  const selectedRcp = rcpValue === 'composite' ? 4.5 : Number(rcpValue)

  useEffect(() => {
    const handleKeyDown = event => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div className={s.overlay} role="dialog" aria-modal="true" aria-labelledby="model-details-title">
      <article className={s.page}>
        <header className={s.header}>
          <div>
            <span>SIMULATION MODEL</span>
            <h1 id="model-details-title">モデルの詳細</h1>
            <p>2026〜2100年の流域適応を、1年刻みで計算する簡略化モデルです。</p>
          </div>
          <button type="button" onClick={onClose}>概要へ戻る</button>
        </header>

        <div className={s.layout}>
          <aside className={s.contents}>
            <strong>このページの内容</strong>
            <a href="#model-overview">モデル構造</a>
            <a href="#model-climate">気候・極端降雨</a>
            <a href="#model-water">森林・水循環</a>
            <a href="#model-agriculture">農業生産</a>
            <a href="#model-flood">洪水被害</a>
            <a href="#model-ecosystem">生態系</a>
            <a href="#model-policy">政策と予算</a>
            <a href="#model-random">乱数と限界</a>
          </aside>

          <main className={s.body}>
            <section id="model-overview" className={s.section}>
              <div className={s.sectionKicker}>01 / STRUCTURE</div>
              <h2>モデル構造と計算順序</h2>
              <p>プレイヤーは25年ごとに政策配分を決めます。同じ配分をその期間の各年へ適用し、前年の状態を引き継いで次の順に更新します。</p>
              <ol className={s.flow}>
                <li><b>気候</b><span>気温、年降水量、極端降雨の回数と強度</span></li>
                <li><b>自然系</b><span>森林の成熟・減衰、水収支、田んぼダム</span></li>
                <li><b>農業</b><span>水不足、高温影響、農業R&D、洪水影響</span></li>
                <li><b>防災</b><span>住宅移転、堤防、防災能力、洪水被害</span></li>
                <li><b>評価</b><span>生態系、公的出費、住民負担、イベント判定</span></li>
              </ol>
              <div className={s.note}><b>時間解像度：</b>1年　<b>意思決定：</b>25年ごと・全3ターン　<b>空間：</b>流域全体を一つの集約地域として表現</div>
            </section>

            <section id="model-climate" className={s.section}>
              <div className={s.sectionKicker}>02 / CLIMATE</div>
              <h2>気候と極端降雨</h2>
              <h3>年平均気温</h3>
              <Formula>Tₜ = 15.5 + α<sub>T</sub>(t − 2026) + ε<sub>T</sub>　,　ε<sub>T</sub> ∼ N(0, 0.5²)</Formula>
              <h3>年降水量</h3>
              <Formula>Pₜ = max[0, 1700 + ε<sub>P</sub>]　,　ε<sub>P</sub> ∼ N(0, 50²) mm</Formula>
              <h3>極端降雨</h3>
              <Formula>λₜ = 0.1 × [1 + α<sub>F</sub>(t − 2026)]　／　Nₜ ∼ Poisson(λₜ)</Formula>
              <Formula>各豪雨量 R ∼ Gumbel(μ = 180, βₜ = 20 + α<sub>I</sub>(t − 2026)) mm</Formula>
              <p>RCPが高いほど、気温上昇率、極端降雨の発生率、豪雨分布の広がりが大きくなります。通常の年降水量トレンドは0で、違いは主に気温と極端降雨へ反映されます。</p>
              <div className={s.tableWrap}>
                <table className={s.rcpTable}>
                  <thead><tr><th>シナリオ</th><th>αT（℃/年）</th><th>αF（頻度/年）</th><th>αI（mm/年）</th></tr></thead>
                  <tbody>{RCP_ROWS.map(row => (
                    <tr key={row.rcp} className={row.value === selectedRcp ? s.selectedRow : ''}>
                      <td>{row.rcp}{row.value === selectedRcp && <b> 選択中</b>}</td><td>{row.temp}</td><td>{row.frequency}</td><td>{row.intensity}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </section>

            <section id="model-water" className={s.section}>
              <div className={s.sectionKicker}>03 / FOREST & WATER</div>
              <h2>森林と水循環</h2>
              <h3>森林面積</h3>
              <Formula>Fₜ = clip[Fₜ₋₁ + Plantₜ₋₃₀ − Fₜ₋₁dₜ, 0, 10,000]</Formula>
              <Formula>dₜ = 0.01 × [1 + 0.1α<sub>T</sub>(t − 2026)]</Formula>
              <p>植林は30年後に成熟して森林面積へ加わります。森林による洪水流出の補正は <code>1.6 × (Fₜ − 5,000) / 10,000</code>、浸透率は <code>3 × (Fₜ / 10,000) × 0.1</code> です。</p>
              <h3>利用可能水量</h3>
              <Formula>Wₜ = clip[Wₜ₋₁ + Pₜ − ETₜ − Mₜ − 330 − 0.6Pₜ + Infiltrationₜ + 66, 0, 3000]</Formula>
              <Formula>ETₜ = 300 × [1 + 0.05 max(Tₜ − 15.5, 0)]</Formula>
              <ParameterTable rows={[
                ['流域面積', '10,000 ha', '森林率や生態系の基準面積'],
                ['水田面積', '2,000 ha', '田んぼダム導入面積の上限'],
                ['農業水需要', '330 mm/年', '水充足率の分母'],
                ['最大利用可能水量', '3,000 mm', '水ストックの上限'],
                ['流出係数', '0.6', '年降水量のうち即時流出する割合'],
              ]} />
            </section>

            <section id="model-agriculture" className={s.section}>
              <div className={s.sectionKicker}>04 / AGRICULTURE</div>
              <h2>農業生産</h2>
              <Formula>Yₜ = max[5000(1 − L<sub>heat</sub>) × min(Wₜ/330, 1) × (1 − L<sub>paddy</sub>) − D<sub>flood</sub>×10⁻⁵, 0]</Formula>
              <p>登熟期気温は年平均気温＋6℃と仮定します。基本の至適温度は22℃、変曲点は30℃です。至適温度から変曲点までは1℃当たり4%、それ以上は1℃当たり10%の損失を加えます。農業R&Dの高温耐性値だけ、至適温度と変曲点が上方へ移動します。</p>
              <Formula>L<sub>paddy</sub> = 0.01 × min(A<sub>paddy</sub>/2000, 1)</Formula>
              <p>農業R&Dは内部累積投資が概ね25（閾値5×必要年数5、標準偏差0.5）を超えるたび、高温耐性を0.2℃改善します。上限は2.5℃です。</p>
            </section>

            <section id="model-flood" className={s.section}>
              <div className={s.sectionKicker}>05 / FLOOD</div>
              <h2>洪水被害</h2>
              <Formula>Overflow = max[R − H<sub>levee</sub> − H<sub>paddy</sub>, 0] × (1 − Reduction<sub>forest</sub>)</Formula>
              <Formula>Response = 1 / [1 + exp(−0.02(Overflow − 200))]</Formula>
              <Formula>D<sub>flood</sub> = Σ Overflow × 1,000,000 × [1 − C(1 − Response)] × [1 − Q(1 − Response)]</Formula>
              <p><code>C</code>は住民防災能力、<code>Q</code>は安全な地域へ移転済みの住宅割合です。小〜中規模の洪水では両政策が効きやすく、規模が極端に大きくなると効果が相対的に弱まります。</p>
              <ParameterTable rows={[
                ['初期堤防高', '0 mm（状態値）', 'ゲーム開始時の堤防・河川改修による追加防御水準'],
                ['堤防の増分', '20 mm', '投資閾値を超えるごとの上昇量'],
                ['田んぼダム効果', '最大10 mm', '導入面積率に比例'],
                ['洪水被害係数', '1,000,000円/mm', '越流水量から被害額への換算'],
                ['防災能力', '0〜0.99', '毎年5%減衰し、訓練で増加'],
              ]} />
            </section>

            <section id="model-ecosystem" className={s.section}>
              <div className={s.sectionKicker}>06 / ECOSYSTEM</div>
              <h2>生態系</h2>
              <Formula>Eₜ = 100/3 × [min(0.7Fₜ/10,000, 1) + min(Wₜ/800, 1) + Pressure] − 0.03H<sub>levee</sub></Formula>
              <Formula>Pressure = clip[1 − min(0.01H<sub>levee</sub> − 1, 1), 0, 1]</Formula>
              <p>森林、水環境、人為圧力を同じ重みで合成します。堤防高には追加の生態系影響を設定しているため、洪水防御とのトレードオフが生じます。</p>
            </section>

            <section id="model-policy" className={s.section}>
              <div className={s.sectionKicker}>07 / POLICY & BUDGET</div>
              <h2>政策ポイントと予算</h2>
              <p>1政策ポイントは年間2,000万円相当です。選んだポイントは25年間、毎年同じ強度で投入されます。</p>
              <div className={s.tableWrap}>
                <table className={s.policyTable}>
                  <thead><tr><th>政策</th><th>最低投入</th><th>上限</th><th>モデル内での作用</th></tr></thead>
                  <tbody>{POLICY_ROWS.map(row => <tr key={row[0]}>{row.map(cell => <td key={cell}>{cell}</td>)}</tr>)}</tbody>
                </table>
              </div>
              <Formula>利用可能予算 = max[0, 10 − 人口減少分 − 移転後維持費 − 前期平均洪水被害/2,000万円]</Formula>
              <p>人口による予算倍率は2026年1.00、2050年0.85、2075年0.68、2100年0.52を線形補間します。住宅移転が累積1点を超えると、移転先のインフラ維持費も将来予算から差し引かれます。</p>
              <Formula>政策費 = Σ政策ポイント × 2,000万円/年</Formula>
              <Formula>住民負担 = 表示用自治体コスト/総住宅数 + 洪水復旧費/総住宅数</Formula>
              <p>表示用自治体コストは、既存データとの互換性のため政策費を100で除した内部表示単位です。洪水復旧費は円ベースの被害額を住宅数で按分します。</p>
            </section>

            <section id="model-random" className={s.section}>
              <div className={s.sectionKicker}>08 / UNCERTAINTY</div>
              <h2>乱数、再現性、モデルの限界</h2>
              <ul className={s.limitList}>
                <li>本編は年ごとに固定シード（基準857＋経過年）を使うため、同じRCPと政策経路なら同じ結果になります。</li>
                <li>気温、降水量、水需要、極端降雨回数・強度、堤防・農業R&Dの閾値に確率変動があります。</li>
                <li>流域内の場所ごとの差、実際の河道形状、個別作物、人口移動、物価変動は集約・簡略化しています。</li>
                <li>表示値は政策間の因果関係とトレードオフを学ぶための仮想値で、実在自治体の予測値ではありません。</li>
                <li>イベント通知の閾値は説明用であり、モデル本体の連続的な計算とは別に判定されます。</li>
              </ul>
              <div className={s.warning}>このモデルは意思決定学習用の簡略モデルです。実際の政策立案では、地域の観測データ、洪水氾濫解析、農業・生態系調査、費用便益分析を別途組み合わせる必要があります。</div>
            </section>
          </main>
        </div>
      </article>
    </div>
  )
}
