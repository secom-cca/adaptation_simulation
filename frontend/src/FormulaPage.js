// FormulaPage.js
import React, { useState } from 'react';
import { Box, Typography, Slider, Paper, Button } from '@mui/material';
import { Link } from 'react-router-dom';
import 'katex/dist/katex.min.css';
import { BlockMath, InlineMath } from 'react-katex';

function FormulaPage() {
  /* ====== 既存のステート（気候関連パラメータ etc.） ====== */
  const [tempTrend, setTempTrend]           = useState(0.03);
  const [hotDaysCoeff, setHotDaysCoeff]     = useState(2.0);
  const [temp, setTemp]                     = useState(17.0);
  const [baseTemp, setBaseTemp]             = useState(15.0);

  const [extremeFreqTrend, setExtremeFreqTrend] = useState(0.05);
  const [startYear, setStartYear]           = useState(2025);
  const [year, setYear]                     = useState(2035);

  const [forestArea, setForestArea]         = useState(3000);
  const [totalArea, setTotalArea]           = useState(10000);
  const [floodReductionCoef, setFloodReductionCoef] = useState(0.4);

  const [leveeLevel, setLeveeLevel]         = useState(100);
  const [paddyDam, setPaddyDam]             = useState(10);
  const [damageCoef, setDamageCoef]         = useState(100000);
  const [tempImpact, setTempImpact]         = useState(0.2);
  const [waterAvail, setWaterAvail]         = useState(0.8);
  const [paddyImpact, setPaddyImpact]       = useState(0.1);

  /* ====== 派生計算 ====== */
  const deltaYear         = year - startYear;
  const expectedTemp      = baseTemp + tempTrend * deltaYear;
  const expectedHotDays   = (temp - baseTemp) * hotDaysCoeff;
  const floodReductionRate = (forestArea / totalArea) * floodReductionCoef;

  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h4" gutterBottom>
        シミュレーション数式とパラメータ調整
      </Typography>

      <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
        <Link to="/" style={{ textDecoration: 'none' }}>
          <Button variant="contained">戻る</Button>
        </Link>
        <Button
          variant="outlined"
          color="warning"
          onClick={() => {
            // 清除模拟状态但保留用户设置
            const keysToKeep = ['userName', 'selectedMode', 'chartPredictMode', 'language', 'decisionVar', 'currentValues'];
            const preservedData = {};
            keysToKeep.forEach(key => {
              const value = localStorage.getItem(key);
              if (value) preservedData[key] = value;
            });

            // 清除所有localStorage
            localStorage.clear();

            // 恢复保留的数据
            Object.entries(preservedData).forEach(([key, value]) => {
              localStorage.setItem(key, value);
            });

            // 清除模拟状态
            localStorage.removeItem('simulationState');

            alert('模拟进度已重置，但用户设置已保留。返回主页面后将从头开始。');
          }}
        >
          重置模拟进度
        </Button>
      </Box>

      {/* ---------- 概要 ---------- */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>概要</Typography>
        <Typography paragraph>
          本研究では、社会-環境システムの動態を年次タイムステップで再現・評価する
          <b>動的シミュレーションモデル</b>を構築した。気象変動・住民行動・公共投資
          など複数領域の相互作用を考慮し、気候変動適応策の効果を定量評価する。
        </Typography>
        <Typography paragraph>
          各年において社会環境・自然環境の状態を更新し、政策介入（意思決定変数）
          への応答をシミュレートする。閉じた世界を想定し、例えば品種改良の
          他地域への波及効果は考慮していない。
        </Typography>
      </Paper>

      {/* ---------- (1) 気候パラメータ設定 ---------- */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6">(1) 気候パラメータ設定</Typography>

        <Typography variant="subtitle1" sx={{ mt: 1 }}>年平均気温</Typography>
        <BlockMath math={`\\mathrm{Temp}_t = T_0 + \\alpha_T\\,(t - t_0) + \\mathcal{N}(0,\\sigma_T)`} />

        <Typography variant="subtitle1" sx={{ mt: 2 }}>年平均降水量</Typography>
        <BlockMath math={`\\mathrm{Precip}_t = \\max\\bigl(0, P_0 + \\alpha_P\\,(t - t_0) + \\mathcal{N}(0,\\sigma_{P,t})\\bigr)`} />

        <Typography variant="subtitle1" sx={{ mt: 2 }}>極端降水イベント</Typography>
        <BlockMath math={`\\lambda_t = \\max\\bigl(0, \\lambda_0 + \\alpha_\\lambda\\,(t - t_0)\\bigr),\\quad N_{\\text{extreme}} \\sim \\text{Poisson}(\\lambda_t)`} />
        <BlockMath math={`\\text{RainEvent}_i \\sim \\text{Gumbel}(\\mu_t,\\,\\beta_t),\\quad i=1,\\ldots,N_{\\text{extreme}}`} />

        {/* 既存のインタラクティブ気温・降水パネルを再利用 */}
        {/* ----- 気温予測 ----- */}
        <Typography variant="subtitle2" sx={{ mt: 3 }}>► 年平均気温の予測</Typography>
        <BlockMath math={`\\text{Temp}(t) = T_0 + \\alpha_T\\,(t - t_0)`} />
        <Typography>気温上昇率 (α<InlineMath math="T" />): {tempTrend}</Typography>
        <Slider value={tempTrend} step={0.005} min={0.01} max={0.1}
                onChange={(e,val)=>setTempTrend(val)} valueLabelDisplay="auto"/>
        <Typography>計算結果（{year}年）: {expectedTemp.toFixed(2)} ℃</Typography>
      </Paper>

      {/* ---------- (2) 社会環境シナリオ ---------- */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6">(2) 社会環境シナリオ</Typography>
        <BlockMath math={`\\mathrm{Demand}_t = \\mathrm{Demand}_{t-1}\\,\\bigl(1 + \\gamma + \\mathcal{N}(0,\\sigma_\\gamma)\\bigr)`} />
        <Typography paragraph>
          年次成長率 γ は一定、年々変動 σ<InlineMath math="γ" /> は 1 % と仮定。
        </Typography>
      </Paper>

      {/* ---------- (3) 森林・生態系モジュール ---------- */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6">(3) 森林・生態系モジュール</Typography>
        <BlockMath math={`\\mathrm{MaturedTrees}_t = \\mathrm{Planting}_{t-Y_g}`} />
        <BlockMath math={`A_{f,t} = \\max\\bigl(A_{f,t-1} + \\mathrm{MaturedTrees}_t - A_{f,t-1}\\,r_d,\\,0\\bigr)`} />

        <BlockMath math={`\\varphi_{\\text{flood}} = \\rho_f \\frac{A_{f,t}}{A_{\\text{total}}}`} />
        <BlockMath math={`\\varphi_{\\text{retention}} = \\rho_w \\frac{A_{f,t}}{A_{\\text{total}}}`} />
        <BlockMath math={`\\varphi_{\\text{ecosystem}} = \\min\\bigl(\\rho_e\\,A_{f,t},\\,5.0\\bigr)`} />

        {/* インタラクティブ洪水緩和率 (既存) */}
        <Typography variant="subtitle2" sx={{ mt: 3 }}>► 森林による洪水軽減効果（簡易）</Typography>
        <BlockMath math={`\\text{FloodReduction} = \\rho_f \\cdot \\frac{A_{\\text{forest}}}{A_{\\text{total}}}`}/>
        <Typography>森林面積 (ha): {forestArea}</Typography>
        <Slider value={forestArea} step={100} min={0} max={10000}
                onChange={(e,val)=>setForestArea(val)} valueLabelDisplay="auto"/>
        <Typography>洪水軽減割合: {(floodReductionRate*100).toFixed(1)} %</Typography>
      </Paper>

      {/* ---------- (4) 水資源モジュール ---------- */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6">(4) 水資源モジュール</Typography>
        <BlockMath math={`ET_t = ET_0\\Bigl(1 + 0.05\\,(\\mathrm{Temp}_t - T_0)\\Bigr)`} />
        <BlockMath math={`W_t = \\min\\!\\Bigl(\\max\\bigl(W_{t-1} + \\mathrm{Precip}_t - ET_t - D_t - \\theta\\,\\mathrm{Precip}_t + \\varphi_{\\text{retention}}\,\\mathrm{Precip}_t,\\,0\\bigr),\\,W_{\\max}\\Bigr)`} />
      </Paper>

      {/* ---------- (5) 農業モジュール ---------- */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6">(5) 農業モジュール</Typography>
        <BlockMath math={`L_T = \\min\\!\\Bigl(\\tfrac{\\max(0,\\,T_{\\text{ripening}} - (T_{\\text{thresh}} + T_{\\text{tol}}))}{T_{\\text{crit}} - T_{\\text{thresh}}},\\,1\\Bigr)`} />
        <BlockMath math={`Y_{t} = Y_{\\max}\\,(1 - L_T)\\,\\varphi_W\\,(1 - \\varphi_{\\text{paddy}})`} />

        {/* インタラクティブ収量パネル (既存) */}
        <Typography variant="subtitle2" sx={{ mt: 3 }}>► 作物収量の推定</Typography>
        <BlockMath math={`Y = Y_{\\max}\\,(1-L_T)\\,\\varphi_W\\,(1-\\varphi_{\\text{paddy}})`}/>
        <Typography>温度被害 L<InlineMath math="T" />: {tempImpact}</Typography>
        <Slider value={tempImpact} step={0.01} min={0} max={1}
                onChange={(e,val)=>setTempImpact(val)} valueLabelDisplay="auto"/>
      </Paper>

      {/* ---------- (6) 居住モジュール ---------- */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6">(6) 居住モジュール</Typography>
        <BlockMath math={`R_t = \\frac{H_s}{H_r + H_s}`} />
      </Paper>

      {/* ---------- (7) インフラモジュール ---------- */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6">(7) インフラモジュール</Typography>
        <BlockMath math={`I_{\\text{levee},t} = I_{\\text{levee},t-1} + C_{\\text{levee}}`} />
        <BlockMath math={`D_{\\text{flood}} = \\sum_i \\max(R_i - L_t - \\varphi_{\\text{paddy-flood}}, 0)\\,(1-\\varphi_{\\text{flood}})\\,\\rho_D`} />

        {/* インタラクティブ被害パネル (既存) */}
        <Typography variant="subtitle2" sx={{ mt: 3 }}>► 洪水被害の簡易推定</Typography>
        <BlockMath math={`D = \\sum(R_i - L - P)\\,(1-\\varphi_{\\text{flood}})\\,\\rho_D`} />
        <Typography>堤防高さ L (mm): {leveeLevel}</Typography>
        <Slider value={leveeLevel} step={10} min={0} max={300}
                onChange={(e,val)=>setLeveeLevel(val)} valueLabelDisplay="auto"/>
      </Paper>

      {/* ---------- (8) 都市の居住可能性 ---------- */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6">(8) 都市の居住可能性</Typography>
        <BlockMath math={`U_t = (1-R_t)\\,T_t - D_{\\text{actual}}\\,\\rho_U`} />
      </Paper>

      {/* ---------- (9) 住民意識 & 費用評価 ---------- */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6">(9) 住民意識 &amp; 費用評価</Typography>
        <BlockMath math={`C_t = C_{t-1}\\,(1-\\delta_C) + C_{\\text{train}}\\,\\rho_C`} />
        <BlockMath math={`C_{\\text{total}} = C_{\\text{levee}}10^6 + C_{\\text{R\\&D}}10^6 + \\dots`} />
        <BlockMath math={`B_t = C_{\\text{total}} + D_{\\text{actual}}\\,\\rho_{\\text{recover}}`} />
      </Paper>
    </Box>
  );
}

export default FormulaPage;
