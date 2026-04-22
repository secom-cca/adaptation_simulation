import React, { useState } from 'react';
import { Box, Typography, Slider, Paper, Button, Grid } from '@mui/material';
// import { Link } from 'react-router-dom';
import 'katex/dist/katex.min.css';
import { BlockMath, InlineMath } from 'react-katex';

function FormulaPage() {
  const [startYear, setStartYear] = useState(2026);
  const [year, setYear] = useState(2040);
  const dt = year - startYear;

  // Temperature constants
  const [T0, setT0] = useState(15.5);
  const [aT, setAT] = useState(0.04);
  const [sigT, setSigT] = useState(0.5);

  // Precipitation constants
  const [P0, setP0] = useState(1700);
  const [aP, setAP] = useState(0);
  const [sigP0, setSigP0] = useState(5);
  const [aSigP, setASigP] = useState(0.0);

  // Extreme Precip constants
  const [lam0, setLam0] = useState(0.1);
  const [aLam, setALam] = useState(0.05);
  const [mu0, setMu0] = useState(180);
  const [aMu, setAMu] = useState(0.2);
  const [beta0, setBeta0] = useState(20);
  const [aBeta, setABeta] = useState(0.05);
  
  // Forest constants
  const [r_f0, setRf0] = useState(0.5);          // 初期森林比率
  const [alphaFlood, setAlphaFlood] = useState(0.4); // 洪水感度係数
  const [alphaWater, setAlphaWater] = useState(2.0); // 保水感度係数
  const [r_d, setRd] = useState(0.01);           // 自然損失率
  const [Yg, setYg] = useState(30);              // 成熟年数

  // Agriculture constants
  const [T_tol, setT_tol] = useState(0.0);
  const [T_thr, setT_thr] = useState(22.0);
  const [T_crit, setT_crit] = useState(30.0);

  // Infrastructure constants
  const [rhoD, setRhoD] = useState(100000);
  const [rhoY, setRhoY] = useState(0.00001);
  const [TL, setTL] = useState(20);        // Threshold levee investment (million yen)
  const [deltaL, setDeltaL] = useState(20); // Levee protection increment (mm)

  // Ecosystem constants
  const [betaT, setBetaT] = useState(0.05);
  const [betaP, setBetaP] = useState(0.03);
  const [betaL, setBetaL] = useState(0.01);

  // Water constants
  const [theta, setTheta] = useState(0.6);
  const [Wmax, setWmax] = useState(3000);
  const [gamma, setGamma] = useState(0.0);
  const [sigmaGamma, setSigmaGamma] = useState(0.01);

  // Public Awareness
  const [decayC, setDecayC] = useState(0.05);
  const [rhoC, setRhoC] = useState(0.01);
  const [maxC, setMaxC] = useState(0.99);

  // Cost Evaluation
  const [rhoRecover, setRhoRecover] = useState(0.1);

  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h4" gutterBottom>Model Equations & Tunable (TBD: currently untunable) Parameters</Typography>
      {/* <Box sx={{ mb: 3 }}>
        <Link to="/" style={{ textDecoration: 'none' }}><Button variant="contained">Back</Button></Link>
      </Box> */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(1-1) Temperature</Typography>
            <Typography variant="body2">
              This module simulates long-term changes in mean annual temperature using linear trends (αT) based on RCP scenarios and annual stochastic variability (σT). Mean Annual Temperature T₀ is initialized at 15.5°C, with annual variation modeled as:
            </Typography>
            <BlockMath math={"Temp_t = T_0 + \\alpha_T (t - t_0) + \\mathcal{N}(0, \\sigma_T)"} />
            {[['T₀', T0, setT0, 20], ['αT', aT, setAT, 0.1], ['σT', sigT, setSigT, 2]].map(([label, val, setVal, max]) => (
              <Grid item xs={12} key={label}><Typography variant="caption">{label}: {val}</Typography><Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setVal(v)} /></Grid>
            ))}
          </Paper>

          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(1-2) Precipitation</Typography>
            <Typography variant="body2">
              This module models average annual precipitation with variability increasing under higher RCP scenarios. σₚₜ increases over time as: σₚₜ = σₚ₀ + αₛₚ(t - t₀)
            </Typography>
            <BlockMath math={"Precip_t = \\max(0, P_0 + \\alpha_P (t - t_0) + \\mathcal{N}(0, \\sigma_{P,t}))"} />
            {[['P₀', P0, setP0, 3000], ['αP', aP, setAP, 20], ['σP₀', sigP0, setSigP0, 10], ['ασP', aSigP, setASigP, 5]].map(([label, val, setVal, max]) => (
              <Grid item xs={12} key={label}><Typography variant="caption">{label}: {val}</Typography><Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setVal(v)} /></Grid>
            ))}
          </Paper>

          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(1-3) Extreme Precipitation</Typography>
            <Typography variant="body2">
              This module simulates extreme rainfall with frequency (Poisson) and intensity (Gumbel distribution), both dependent on RCP scenario.
            </Typography>
            <BlockMath math={"\\lambda_t = \\max(0, \\lambda_0 + \\alpha_\\lambda (t - t_0))"} />
            <BlockMath math={"N_{extreme} \\sim \\text{Poisson}(\\lambda_t)"} />
            <BlockMath math={"\\mu_t = \\max(\\mu_0 + \\alpha_\\mu (t - t_0), 0)"} />
            <BlockMath math={"\\beta_t = \\max(\\beta_0 + \\alpha_\\mu (t - t_0), 0)"} />
            <BlockMath math={"RainEvent_i \\sim \\text{Gumbel}(\\mu_t, \\beta_t), \\quad i = 1, \\ldots, N_{extreme}"} />
            {[['λ₀', lam0, setLam0, 5], ['αλ', aLam, setALam, 0.2], ['μ₀', mu0, setMu0, 500], ['αμ', aMu, setAMu, 10], ['β₀', beta0, setBeta0, 100], ['αβ', aBeta, setABeta, 5]].map(([label, val, setVal, max]) => (
              <Grid item xs={12} key={label}><Typography variant="caption">{label}: {val}</Typography><Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setVal(v)} /></Grid>
            ))}
          </Paper>

          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(2) Water Resource</Typography>
            <Typography variant="body2">
              Water availability is dynamically updated based on precipitation, evapotranspiration, population-based demand, and forest water retention effects.
            </Typography>

            <Typography variant="subtitle2" sx={{ mt: 2 }}>Evapotranspiration</Typography>
            <BlockMath math={"ET_t = ET_0 \\cdot \\left(1 + 0.05 \\cdot (\\mathrm{Temp}_t - T_0)\\right)"} />

            <Typography variant="subtitle2" sx={{ mt: 2 }}>Population-based Water Demand</Typography>
            <BlockMath math={"\\mathrm{Demand}_t = \\mathrm{Demand}_{t-1} \\cdot \\left(1 + \\gamma + \\mathcal{N}(0, \\sigma_\\gamma)\\right)"} />

            <Typography variant="subtitle2" sx={{ mt: 2 }}>Water Storage Update</Typography>
            <BlockMath math={"W_t = \\min\\left( \\max\\left( W_{t-1} + \\mathrm{Precip}_t - ET_t - \\mathrm{Demand}_t - \\theta \\cdot \\mathrm{Precip}_t + \\mathrm{WaterRetention}_t \\cdot \\mathrm{Precip}_t, 0 \\right), W_{\\max} \\right)"} />

            {[['θ (Runoff Coef.)', theta, setTheta, 1.0, 0.01],
              ['γ (Growth Rate)', gamma, setGamma, 0.05, 0.001],
              ['σγ (Growth Variability)', sigmaGamma, setSigmaGamma, 0.05, 0.001]
            ].map(([label, val, setVal, max, step]) => (
              <Grid item xs={12} key={label}>
                <Typography variant="caption">{label}: {val.toFixed(3)}</Typography>
                <Slider size="small" value={val} min={0} max={max} step={step} onChange={(e, v) => setVal(v)} />
              </Grid>
            ))}
          </Paper>

          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(3) Forest</Typography>
            <Typography variant="body2">
              Forest area increases after afforestation activities mature ({`Y₍g₎`} = {Yg} years), while decreasing by a fixed loss ratio ({`r_d`} = {r_d}). The flood mitigation effect is modeled as the relative increase in forest area, and water retention is proportional to the forest share.
            </Typography>
            <BlockMath math={"\\mathrm{MaturedTrees}_t = \\mathrm{Planting}_{t - Y_g}"} />
            <BlockMath math={"\\mathrm{Loss} = A_{f,t-1} \\cdot r_d"} />
            <BlockMath math={"A_{f,t} = \\max(A_{f,t-1} + \\mathrm{MaturedTrees}_t - \\mathrm{Loss}, 0)"} />
            <BlockMath math={"\\text{FloodReduction}_t = \\alpha_{\\text{flood}} \\cdot \\left( \\frac{A_{f,t} - A_{\\text{total}} \\cdot r_{f,0}}{A_{\\text{total}}} \\right)"} />
            <BlockMath math={"\\text{WaterRetention}_t = \\alpha_{\\text{water}} \\cdot \\frac{A_{f,t}}{A_{\\text{total}}}"} />
            {[['r_f,0', r_f0, setRf0, 1], ['α_flood', alphaFlood, setAlphaFlood, 3], ['α_water', alphaWater, setAlphaWater, 5], ['r_d', r_d, setRd, 0.1], ['Y_g', Yg, setYg, 50]].map(([label, val, setVal, max]) => (
              <Grid item xs={12} key={label}>
                <Typography variant="caption">{label}: {val}</Typography>
                <Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setVal(v)} />
              </Grid>
            ))}
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          {/* (5) Agriculture */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(4) Agriculture</Typography>
            <Typography variant="body2">
              Agricultural yield is influenced by temperature stress during the ripening phase, availability of irrigation water, and usage of flood-mitigating paddy dams.
              Crop heat tolerance improves gradually through R&D investment. Paddy dam conversion reduces yield slightly due to management constraints.
            </Typography>

            <BlockMath math={"T_{\\text{ripening}} = Temp_t + 6"} />
            <BlockMath math={"T_{\\text{opt}} = 22 + T_{\\text{tol}}, \\quad T_{\\text{turn}} = 30 + T_{\\text{tol}}, \\quad T_{\\text{min}} = 20"} />
            <BlockMath math={"L_T = \\begin{cases}" +
              "0 & \\text{if } T_{\\text{ripening}} \\leq T_{\\text{min}} \\\\" +
              "(T_{\\text{min}} - T_{\\text{ripening}}) \\cdot 0.10 & \\text{if } T_{\\text{ripening}} < T_{\\text{opt}} \\\\" +
              "(T_{\\text{ripening}} - T_{\\text{opt}}) \\cdot 0.04 & \\text{if } T_{\\text{opt}} \\leq T_{\\text{ripening}} \\leq T_{\\text{turn}} \\\\" +
              "(T_{\\text{turn}} - T_{\\text{opt}}) \\cdot 0.04 + (T_{\\text{ripening}} - T_{\\text{turn}}) \\cdot 0.10 & \\text{otherwise}" +
              "\\end{cases}"} />

            <BlockMath math={"A_{\\text{dam}, t} = A_{\\text{dam}, t-1} + \\frac{I_t}{C_{\\text{dam}}}"} />
            <BlockMath math={"L_{\\text{dam}, t} = \\rho_{\\text{dam}} \\cdot \\min\\left(\\frac{A_{\\text{dam}, t}}{A_{\\text{paddy}}}, 1 \\right)"} />
            <BlockMath math={"W_{\\text{factor}, t} = \\min\\left( \\frac{W_t}{W_{\\text{need}}}, 1 \\right)"} />
            <BlockMath math={"Y_t = \\max \\left[ Y_{\\max} \\cdot (1 - L_T) \\cdot W_{\\text{factor}, t} \\cdot (1 - L_{\\text{dam}, t}), 0 \\right]"} />

            {[['T_tol', T_tol, setT_tol, 2], ['T_thr', T_thr, setT_thr, 30], ['T_crit', T_crit, setT_crit, 40]].map(([label, val, setVal, max]) => (
              <Grid item xs={12} key={label}>
                <Typography variant="caption">{label}: {val}</Typography>
                <Slider size="small" value={val} min={0} max={max} step={0.1} onChange={(e, v) => setVal(v)} />
              </Grid>
            ))}
          </Paper>

          {/* (6) Residential Relocation */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(5) Residential Relocation</Typography>
            <Typography variant="body2">Evaluates the effect of household relocation from flood-prone areas on reducing vulnerability.</Typography>
            <BlockMath math={"H_r = \\max(H_{r,t-1} - M_t, 0), \\quad H_s = H_{s,t-1} + M_t"} />
            <BlockMath math={"R_t = \\frac{H_s}{H_r + H_s}"} />
          </Paper>

          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(6) Public Awareness Module</Typography>
            <Typography variant="body2">
              Public preparedness degrades over time but can be restored through training investment.
            </Typography>

            <BlockMath math={"C_t = C_{t-1} \\cdot (1 - \\delta_C) + C_{\\text{train}} \\cdot \\rho_C"} />
            <BlockMath math={"C_t = \\min(C_t, C_{\\text{max}})"} />

            {[
              ["Decay Rate (δ_C)", decayC, setDecayC, 0.1],
              ["Training Efficiency (ρ_C)", rhoC, setRhoC, 0.05],
              ["Max Awareness (C_max)", maxC, setMaxC, 1.0],
            ].map(([label, val, setVal, max]) => (
              <Grid item xs={12} key={label}>
                <Typography variant="caption">{label}: {val}</Typography>
                <Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setVal(v)} />
              </Grid>
            ))}
          </Paper>


          {/* (7) Infrastructure & Flood */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(7) Infrastructure & Flood</Typography>
            <Typography variant="body2">
              Infrastructure investment increases levee protection in increments of <InlineMath math={"\\Delta L = 20"} /> mm when cumulative investment exceeds a stochastic threshold. 
              Flood damage is reduced by structural protections (levees, paddy-dams, forests) and social preparedness.
            </Typography>

            <BlockMath math={"I_{\\text{levee},t} = I_{\\text{levee},t-1} + C_{\\text{levee}}"} />
            <BlockMath math={"\\text{If } I_{\\text{levee},t} \\geq \\mathcal{N}(T_L, 0.01 \\cdot T_L): \\quad L_t += \\Delta L, \\quad I_{\\text{levee},t} -= \\mathcal{N}(\\cdot)"} />
            <BlockMath math={"\\phi_{\\text{paddy-flood}} = \\rho_{\\text{paddy-flood}} \\cdot \\frac{A_{\\text{paddy}}}{A_{\\text{paddy, total}}}"} />
            <BlockMath math={"D_{\\text{flood}} = \\sum_{i=1}^{N} \\max(R_i - L_t - \\phi_{\\text{paddy-flood}}, 0) \\cdot (1 - \\text{FloodReduction}_t) \\cdot \\rho_D"} />
            <BlockMath math={"\\text{response\\_factor}_i = \\frac{1}{1 + \\exp\\left(-\\beta (R_i - L_t - \\phi_{\\text{paddy-flood}} - \\tau)\\right)}"} />
            <BlockMath math={"D_{\\text{actual}} = D_{\\text{flood}} \\cdot (1 - R_t) \\cdot (1 - C_t)"} />
            <BlockMath math={"Y_t = Y_t - D_{\\text{actual}} \\cdot \\rho_Y"} />

            {[['T_L', TL, setTL, 100], ['ΔL', deltaL, setDeltaL, 100], ['ρD', rhoD, setRhoD, 500000], ['ρY', rhoY, setRhoY, 0.0001]].map(
              ([label, val, setVal, max]) => (
                <Grid item xs={12} key={label}>
                  <Typography variant="caption">{label}: {val}</Typography>
                  <Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setVal(v)} />
                </Grid>
              )
            )}
          </Paper>


          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(8) Ecosystem Evaluation</Typography>
            <Typography variant="body2">
              Ecosystem status is evaluated using three components—natural resource base, disturbance resistance, and human pressure—weighted and normalized based on the Kristensen framework.
            </Typography>

            {/* Ecological Base */}
            <Typography variant="subtitle2">Ecological Base</Typography>
            <BlockMath math={"\\text{EcologicalBase}_t = 0.5 \\cdot \\min\\left(\\frac{A_{f,t}}{A_{\\text{ftotal}}}, 1.0\\right) + 0.5 \\cdot \\min\\left(\\frac{W_t}{W_{\\text{threshold}}}, 1.0\\right)"} />

            {/* Resistance */}
            <Typography variant="subtitle2">Disturbance Resistance</Typography>
            <BlockMath math={"\\text{Resistance}_t = \\max\\left(0, 1.0 - \\beta_T \\cdot |T_t - T_0| - \\beta_P \\cdot N_{\\text{extreme},t}\\right)"} />

            {/* Human Pressure */}
            <Typography variant="subtitle2">Human Pressure</Typography>
            <BlockMath math={"\\text{HumanPressure}_t = 1.0 - \\min(\\beta_L \\cdot L_t, 1.0)"} />

            {/* Final Ecosystem Score */}
            <Typography variant="subtitle2">Final Ecosystem Score</Typography>
            <BlockMath math={"\\text{EcosystemLevel}_t = 100 \\cdot (w_1 \\cdot \\text{EcologicalBase} + w_2 \\cdot \\text{Resistance} + w_3 \\cdot \\text{HumanPressure})"} />
            <Typography variant="body2">
              Weights \((w_1, w_2, w_3)\) are set as 0.5, 0.25 and 0.25, respectively.
            </Typography>

            {/* Parameter sliders */}
            {[["β_T (Temp Sensitivity)", betaT, setBetaT, 0.2], ["β_P (Precip Sensitivity)", betaP, setBetaP, 0.1], ["β_L (Levee Pressure)", betaL, setBetaL, 0.05]].map(
              ([label, val, setVal, max]) => (
                <Grid item xs={12} key={label}>
                  <Typography variant="caption">{label}: {val}</Typography>
                  <Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setVal(v)} />
                </Grid>
              )
            )}
          </Paper>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(9) Cost Evaluation Module</Typography>
            <Typography variant="body2">
              Total costs include infrastructure, relocation, R&D, training, and disaster recovery.
            </Typography>

            <BlockMath math={"C_{\\text{tree}} = P_{\\text{tree}} \\cdot N_{\\text{tree}}, \\quad C_{\\text{migrate}} = P_{\\text{mig}} \\cdot N_{\\text{mig}}"} />
            <BlockMath math={"C_{\\text{total}} = C_{\\text{levee}} + C_{\\text{R\\&D}} + C_{\\text{paddy}} + C_{\\text{train}} + C_{\\text{tree}} + C_{\\text{migrate}} + C_{\\text{trans}}"} />
            <BlockMath math={"B_t = C_{\\text{total}} + D_{\\text{actual}} \\cdot \\rho_{\\text{recover}}"} />

            <Grid item xs={12}>
              <Typography variant="caption">Recovery Cost Multiplier (ρ_recover): {rhoRecover}</Typography>
              <Slider size="small" value={rhoRecover} min={0} max={1} step={0.01} onChange={(e, v) => setRhoRecover(v)} />
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default FormulaPage;