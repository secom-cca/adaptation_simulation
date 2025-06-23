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
  const [sigPTrend, setSigPTrend] = useState(5);

  // Extreme Precip constants
  const [lam0, setLam0] = useState(0.1);
  const [aLam, setALam] = useState(0.05);
  const [mu0, setMu0] = useState(180);
  const [aMu, setAMu] = useState(0.2);
  const [beta0, setBeta0] = useState(20);
  const [aBeta, setABeta] = useState(0.05);

  // Forest constants
  const [r_f0, setRf0] = useState(0.5);
  const [alphaFlood, setAlphaFlood] = useState(0.4);
  const [alphaWater, setAlphaWater] = useState(2.0);

  // Agriculture constants
  const [T_tol, setT_tol] = useState(0.0);
  const [T_thr, setT_thr] = useState(22.0);
  const [T_crit, setT_crit] = useState(30.0);

  // Infrastructure constants
  const [rhoD, setRhoD] = useState(100000);
  const [rhoY, setRhoY] = useState(0.00001);

  // Ecosystem constants
  const [betaT, setBetaT] = useState(0.05);
  const [betaP, setBetaP] = useState(0.03);
  const [betaL, setBetaL] = useState(0.01);

  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h4" gutterBottom>Model Equations & Tunable Parameters</Typography>
      {/* <Box sx={{ mb: 3 }}>
        <Link to="/" style={{ textDecoration: 'none' }}><Button variant="contained">Back</Button></Link>
      </Box> */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          {/* (1) Temperature */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(1) Temperature</Typography>
            <Typography variant="body2">This module simulates long-term changes in mean annual temperature using linear trends (αT) based on RCP scenarios and annual stochastic variability (σT).</Typography>
            <BlockMath math={"Temp_t = T_0 + \\alpha_T (t - t_0) + \\mathcal{N}(0, \\sigma_T)"} />
            {[['T₀', T0, setT0, 20], ['αT', aT, setAT, 0.1], ['σT', sigT, setSigT, 2]].map(([label, val, setVal, max]) => (
              <Grid item xs={12} key={label}><Typography variant="caption">{label}: {val}</Typography><Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setVal(v)} /></Grid>
            ))}
          </Paper>

          {/* (2) Precipitation */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(2) Precipitation</Typography>
            <Typography variant="body2">This module models average annual precipitation with an optional trend and increasing variability under climate change.</Typography>
            <BlockMath math={"Precip_t = \\max(0, P_0 + \\alpha_P (t - t_0) + \\mathcal{N}(0, \\sigma_{P,t}))"} />
            {[['P₀', P0, setP0, 3000], ['αP', aP, setAP, 20], ['σP,t', sigPTrend, setSigPTrend, 10]].map(([label, val, setVal, max]) => (
              <Grid item xs={12} key={label}><Typography variant="caption">{label}: {val}</Typography><Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setVal(v)} /></Grid>
            ))}
          </Paper>

          {/* (3) Extreme Precipitation */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(3) Extreme Precipitation</Typography>
            <Typography variant="body2">This module simulates the frequency and intensity of extreme rainfall events using Poisson and Gumbel distributions with climate-dependent parameters.</Typography>
            <BlockMath math={"\\lambda_t = \\max(0, \\lambda_0 + \\alpha_\\lambda (t - t_0))"} />
            <BlockMath math={"RainEvent_i \\sim \\text{Gumbel}(\\mu_t, \\beta_t)"} />
            {[['λ₀', lam0, setLam0, 5], ['αλ', aLam, setALam, 0.2], ['μ₀', mu0, setMu0, 500], ['αμ', aMu, setAMu, 10], ['β₀', beta0, setBeta0, 100], ['αβ', aBeta, setABeta, 2]].map(([label, val, setVal, max]) => (
              <Grid item xs={12} key={label}><Typography variant="caption">{label}: {val}</Typography><Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setVal(v)} /></Grid>
            ))}
          </Paper>

          {/* (4) Forest */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(4) Forest</Typography>
            <Typography variant="body2">This module quantifies the effects of forest coverage on flood mitigation and water retention, including natural growth and loss dynamics.</Typography>
            <BlockMath math={"FloodReduction_t = \\alpha_{\\text{flood}} \\cdot (A_{f,t} - A_{\\text{total}} \\cdot r_{f,0}) / A_{\\text{total}}"} />
            <BlockMath math={"WaterRetention_t = \\alpha_{\\text{water}} \\cdot A_{f,t} / A_{\\text{total}}"} />
            {[['r_f,0', r_f0, setRf0, 1], ['α_flood', alphaFlood, setAlphaFlood, 3], ['α_water', alphaWater, setAlphaWater, 5]].map(([label, val, setVal, max]) => (
              <Grid item xs={12} key={label}><Typography variant="caption">{label}: {val}</Typography><Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setVal(v)} /></Grid>
            ))}
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          {/* (5) Agriculture */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(5) Agriculture</Typography>
            <Typography variant="body2">Simulates yield loss in rice due to elevated nighttime temperatures during the ripening phase, with R&D-based improvements in tolerance.</Typography>
            <BlockMath math={"T_{\\text{ripening}} = Temp_t + 6"} />
            {[['T_tol', T_tol, setT_tol, 2], ['T_thr', T_thr, setT_thr, 30], ['T_crit', T_crit, setT_crit, 40]].map(([label, val, setVal, max]) => (
              <Grid item xs={12} key={label}>
                <Typography variant="caption">{label}: {val}</Typography>
                <Slider size="small" value={val} min={0} max={max} step={0.1} onChange={(e, v) => setVal(v)} />
              </Grid>
            ))}
          </Paper>

          {/* (6) Residential Relocation */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(6) Residential Relocation</Typography>
            <Typography variant="body2">Evaluates the effect of household relocation from flood-prone areas on reducing vulnerability.</Typography>
            <BlockMath math={"H_r = \\max(H_{r,t-1} - M_t, 0), \\quad H_s = H_{s,t-1} + M_t"} />
            <BlockMath math={"R_t = \\frac{H_s}{H_r + H_s}"} />
          </Paper>

          {/* (7) Infrastructure */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6">(7) Infrastructure & Flood</Typography>
            <Typography variant="body2">Captures structural protection dynamics and stochastic threshold mechanisms for levee development, as well as flood damage estimation.</Typography>
            <BlockMath math={"D_{\\text{flood}} = \\sum \\max(R_i - L_t - \\phi_{\\text{paddy-flood}}, 0) \\cdot (1 - \\text{FloodReduction}_t) \\cdot \\rho_D"} />
            <BlockMath math={"D_{\\text{actual}} = D_{\\text{flood}} \\cdot (1 - R_t) \\cdot (1 - C_t)"} />
            {[['ρD', rhoD, setRhoD, 500000], ['ρY', rhoY, setRhoY, 0.0001]].map(([label, val, setVal, max]) => (
              <Grid item xs={12} key={label}>
                <Typography variant="caption">{label}: {val}</Typography>
                <Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setVal(v)} />
              </Grid>
            ))}
          </Paper>

          {/* (8) Ecosystem Evaluation */}
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6">(8) Ecosystem Evaluation</Typography>
            <Typography variant="body2">Assesses ecosystem status based on forest and water availability (base), climate stressors (resistance), and human pressure from infrastructure.</Typography>
            <BlockMath math={"E_t = 100(w_1 E_{\\text{base}} + w_2 E_{\\text{res}} + w_3 E_{\\text{human}})"} />
            {[['βT', betaT, setBetaT, 0.1], ['βP', betaP, setBetaP, 0.1], ['βL', betaL, setBetaL, 0.05]].map(([lbl, val, setf, max]) => (
              <Grid item xs={12} key={lbl}>
                <Typography variant="caption">{lbl}: {val}</Typography>
                <Slider size="small" value={val} min={0} max={max} step={max / 100} onChange={(e, v) => setf(v)} />
              </Grid>
            ))}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default FormulaPage;