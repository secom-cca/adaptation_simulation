import React from 'react';
import { Box, Typography, Paper, Button } from '@mui/material';
import { MathJaxContext, MathJax } from 'better-react-mathjax';

const ModelExplanationPage = ({ onBack }) => {
  // MathJax配置
  const mathJaxConfig = {
    loader: { load: ['[tex]/html'] },
    tex: {
      packages: { '[+]': ['html'] },
      inlineMath: [['$', '$'], ['\\(', '\\)']],
      displayMath: [['$$', '$$'], ['\\[', '\\]']],
      processEscapes: true,
      processEnvironments: true
    },
    options: {
      ignoreHtmlClass: 'tex2jax_ignore',
      processHtmlClass: 'tex2jax_process'
    }
  };

  return (
    <MathJaxContext config={mathJaxConfig}>
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
          <Typography sx={{ mb: 2 }}>
            本研究では、社会-環境システムの動態を年次タイムステップで再現・評価する
            <strong>動的シミュレーションモデル</strong>を構築した。気象変動・住民行動・公共投資
            など複数領域の相互作用を考慮し、気候変動適応策の効果を定量評価する。
          </Typography>
          <Typography>
            各年において社会環境・自然環境の状態を更新し、政策介入（意思決定変数）
            への応答をシミュレートする。閉じた世界を想定し、例えば品種改良の
            他地域への波及効果は考慮していない。
          </Typography>
        </Paper>

        {/* ---------- (1) 気候パラメータ設定 ---------- */}
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6">(1) 気候パラメータ設定</Typography>

          <Typography variant="subtitle1" sx={{ mt: 2 }}>年平均気温</Typography>
          <MathJax>
            {"$$\\mathrm{Temp}_t = T_0 + \\alpha_T(t - t_0) + \\mathcal{N}(0,\\sigma_T)$$"}
          </MathJax>

          <Typography variant="subtitle1" sx={{ mt: 2 }}>年平均降水量</Typography>
          <MathJax>
            {"$$\\mathrm{Precip}_t = \\max(0, P_0 + \\alpha_P(t - t_0) + \\mathcal{N}(0,\\sigma_{P,t}))$$"}
          </MathJax>

          <Typography variant="subtitle1" sx={{ mt: 2 }}>極端降水イベント</Typography>
          <MathJax>
            {"$$\\lambda_t = \\max(0, \\lambda_0 + \\alpha_\\lambda(t - t_0))$$"}
          </MathJax>
          <MathJax>
            {"$$N_{\\text{extreme}} \\sim \\text{Poisson}(\\lambda_t)$$"}
          </MathJax>
          <MathJax>
            {"$$\\text{RainEvent}_i \\sim \\text{Gumbel}(\\mu_t, \\beta_t), \\quad i=1,\\ldots,N_{\\text{extreme}}$$"}
          </MathJax>

          <Typography variant="subtitle2" sx={{ mt: 3 }}>► 年平均気温の予測（例）</Typography>
          <MathJax>
            {"$$\\text{Temp}(t) = T_0 + \\alpha_T(t - t_0)$$"}
          </MathJax>
          <Typography>例：気温上昇率 <MathJax inline>{"$\\alpha_T$"}</MathJax> = 0.03 ℃/年</Typography>
          <Typography>計算結果（2035年）: 15.3 ℃</Typography>
        </Paper>

        {/* ---------- (2) 社会環境シナリオ ---------- */}
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6">(2) 社会環境シナリオ</Typography>
          <MathJax>
            {"$$\\mathrm{Demand}_t = \\mathrm{Demand}_{t-1}(1 + \\gamma + \\mathcal{N}(0,\\sigma_\\gamma))$$"}
          </MathJax>
          <Typography sx={{ mt: 2 }}>
            年次成長率 <MathJax inline>{"$\\gamma$"}</MathJax> は一定、年々変動 <MathJax inline>{"$\\sigma_\\gamma$"}</MathJax> は 1 % と仮定。
          </Typography>
        </Paper>

        {/* ---------- (3) 森林・生態系モジュール ---------- */}
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6">(3) 森林・生態系モジュール</Typography>
          <MathJax>
            {"$$\\mathrm{MaturedTrees}_t = \\mathrm{Planting}_{t-Y_g}$$"}
          </MathJax>
          <MathJax>
            {"$$A_{f,t} = \\max(A_{f,t-1} + \\mathrm{MaturedTrees}_t - A_{f,t-1} \\cdot r_d, 0)$$"}
          </MathJax>

          <MathJax>
            {"$$\\varphi_{\\text{flood}} = \\rho_f \\frac{A_{f,t}}{A_{\\text{total}}}$$"}
          </MathJax>
          <MathJax>
            {"$$\\varphi_{\\text{retention}} = \\rho_w \\frac{A_{f,t}}{A_{\\text{total}}}$$"}
          </MathJax>
          <MathJax>
            {"$$\\varphi_{\\text{ecosystem}} = \\min(\\rho_e \\cdot A_{f,t}, 5.0)$$"}
          </MathJax>

          <Typography variant="subtitle2" sx={{ mt: 3 }}>► 森林による洪水軽減効果（例）</Typography>
          <MathJax>
            {"$$\\text{FloodReduction} = \\rho_f \\cdot \\frac{A_{\\text{forest}}}{A_{\\text{total}}}$$"}
          </MathJax>
          <Typography>例：森林面積 = 3000 ha, 総面積 = 10000 ha, 軽減係数 = 0.4</Typography>
          <Typography>洪水軽減割合: 12.0 %</Typography>
        </Paper>

        {/* ---------- (4) 水資源モジュール ---------- */}
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6">(4) 水資源モジュール</Typography>
          <MathJax>
            {"$$ET_t = ET_0(1 + 0.05(\\mathrm{Temp}_t - T_0))$$"}
          </MathJax>
          <MathJax>
            {"$$W_t = \\min(\\max(W_{t-1} + \\mathrm{Precip}_t - ET_t - D_t - \\theta \\cdot \\mathrm{Precip}_t + \\varphi_{\\text{retention}} \\cdot \\mathrm{Precip}_t, 0), W_{\\max})$$"}
          </MathJax>
        </Paper>

        {/* ---------- (5) 農業モジュール ---------- */}
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6">(5) 農業モジュール</Typography>
          <MathJax>
            {"$$L_T = \\min\\left(\\frac{\\max(0, T_{\\text{ripening}} - (T_{\\text{thresh}} + T_{\\text{tol}}))}{T_{\\text{crit}} - T_{\\text{thresh}}}, 1\\right)$$"}
          </MathJax>
          <MathJax>
            {"$$Y_{t} = Y_{\\max} \\cdot (1 - L_T) \\cdot \\varphi_W \\cdot (1 - \\varphi_{\\text{paddy}})$$"}
          </MathJax>

          <Typography variant="subtitle2" sx={{ mt: 3 }}>► 作物収量の推定（例）</Typography>
          <MathJax>
            {"$$Y = Y_{\\max} \\cdot (1-L_T) \\cdot \\varphi_W \\cdot (1-\\varphi_{\\text{paddy}})$$"}
          </MathJax>
          <Typography>例：温度被害 <MathJax inline>{"$L_T$"}</MathJax> = 0.2 （20%の被害）</Typography>
        </Paper>

        {/* ---------- (6) 居住モジュール ---------- */}
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6">(6) 居住モジュール</Typography>
          <MathJax>
            {"$$R_t = \\frac{H_s}{H_r + H_s}$$"}
          </MathJax>
        </Paper>

        {/* ---------- (7) インフラモジュール ---------- */}
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6">(7) インフラモジュール</Typography>
          <MathJax>
            {"$$I_{\\text{levee},t} = I_{\\text{levee},t-1} + C_{\\text{levee}}$$"}
          </MathJax>
          <MathJax>
            {"$$D_{\\text{flood}} = \\sum_i \\max(R_i - L_t - \\varphi_{\\text{paddy-flood}}, 0) \\cdot (1-\\varphi_{\\text{flood}}) \\cdot \\rho_D$$"}
          </MathJax>

          <Typography variant="subtitle2" sx={{ mt: 3 }}>► 洪水被害の簡易推定（例）</Typography>
          <MathJax>
            {"$$D = \\sum(R_i - L - P) \\cdot (1-\\varphi_{\\text{flood}}) \\cdot \\rho_D$$"}
          </MathJax>
          <Typography>例：堤防高さ L = 100 mm</Typography>
        </Paper>

        {/* ---------- (8) 都市の居住可能性 ---------- */}
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6">(8) 都市の居住可能性</Typography>
          <MathJax>
            {"$$U_t = (1-R_t) \\cdot T_t - D_{\\text{actual}} \\cdot \\rho_U$$"}
          </MathJax>
        </Paper>

        {/* ---------- (9) 住民意識 & 費用評価 ---------- */}
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6">(9) 住民意識 &amp; 費用評価</Typography>
          <MathJax>
            {"$$C_t = C_{t-1} \\cdot (1-\\delta_C) + C_{\\text{train}} \\cdot \\rho_C$$"}
          </MathJax>
          <MathJax>
            {"$$C_{\\text{total}} = C_{\\text{levee}} \\times 10^6 + C_{\\text{R\\&D}} \\times 10^6 + \\dots$$"}
          </MathJax>
          <MathJax>
            {"$$B_t = C_{\\text{total}} + D_{\\text{actual}} \\cdot \\rho_{\\text{recover}}$$"}
          </MathJax>
        </Paper>
      </Box>
    </MathJaxContext>
  );
};

export default ModelExplanationPage;