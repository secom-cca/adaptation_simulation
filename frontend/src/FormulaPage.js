// FormulaPage.js
import React from 'react';
import { Box, Typography, Paper, Button } from '@mui/material';
import 'katex/dist/katex.min.css';
import { BlockMath, InlineMath } from 'react-katex';

function FormulaPage({ onBack }) {
  // 纯信息展示页面 - 不需要状态管理

  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h4" gutterBottom>
        シミュレーション数式とパラメータ調整
      </Typography>

      <Box sx={{ mb: 3 }}>
        <Button
          variant="contained"
          onClick={onBack}
        >
          戻る
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

        {/* 静态示例 - 移除交互元素 */}
        <Typography variant="subtitle2" sx={{ mt: 3 }}>► 年平均気温の予測（例）</Typography>
        <BlockMath math={`\\text{Temp}(t) = T_0 + \\alpha_T\\,(t - t_0)`} />
        <Typography>例：気温上昇率 α<InlineMath math="T" /> = 0.03 ℃/年</Typography>
        <Typography>計算結果（2035年）: 15.3 ℃</Typography>
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

        {/* 静态示例 - 移除交互元素 */}
        <Typography variant="subtitle2" sx={{ mt: 3 }}>► 森林による洪水軽減効果（例）</Typography>
        <BlockMath math={`\\text{FloodReduction} = \\rho_f \\cdot \\frac{A_{\\text{forest}}}{A_{\\text{total}}}`}/>
        <Typography>例：森林面積 = 3000 ha, 総面積 = 10000 ha, 軽減係数 = 0.4</Typography>
        <Typography>洪水軽減割合: 12.0 %</Typography>
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

        {/* 静态示例 - 移除交互元素 */}
        <Typography variant="subtitle2" sx={{ mt: 3 }}>► 作物収量の推定（例）</Typography>
        <BlockMath math={`Y = Y_{\\max}\\,(1-L_T)\\,\\varphi_W\\,(1-\\varphi_{\\text{paddy}})`}/>
        <Typography>例：温度被害 L<InlineMath math="T" /> = 0.2 （20%の被害）</Typography>
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

        {/* 静态示例 - 移除交互元素 */}
        <Typography variant="subtitle2" sx={{ mt: 3 }}>► 洪水被害の簡易推定（例）</Typography>
        <BlockMath math={`D = \\sum(R_i - L - P)\\,(1-\\varphi_{\\text{flood}})\\,\\rho_D`} />
        <Typography>例：堤防高さ L = 100 mm</Typography>
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
