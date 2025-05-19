import React, { useState } from 'react';
import { Box, Typography, Slider, Paper } from '@mui/material';
import 'katex/dist/katex.min.css';
import { BlockMath } from 'react-katex';
import { Link } from 'react-router-dom';
import { Button } from '@mui/material';

function FormulaPage() {
  const [tempTrend, setTempTrend] = useState(0.03); // 気温上昇率
  const [hotDaysCoeff, setHotDaysCoeff] = useState(2.0); // 高温日数変化係数
  const [temp, setTemp] = useState(17.0); // 現在の気温
  const [baseTemp, setBaseTemp] = useState(15.0); // 基準気温

  const [extremeFreqTrend, setExtremeFreqTrend] = useState(0.05); // λの傾き
  const [startYear, setStartYear] = useState(2025);
  const [year, setYear] = useState(2035);

  const [forestArea, setForestArea] = useState(3000); // ha
  const [totalArea, setTotalArea] = useState(10000);
  const [floodReductionCoef, setFloodReductionCoef] = useState(0.4); // 洪水緩和係数

  const deltaYear = year - startYear;
  const expectedTemp = baseTemp + tempTrend * deltaYear;
  const expectedHotDays = (temp - baseTemp) * hotDaysCoeff;

  const floodReductionRate = (forestArea / totalArea) * floodReductionCoef;

// 災害被害
  const [leveeLevel, setLeveeLevel] = useState(100);
  const [paddyDam, setPaddyDam] = useState(10);
  const [damageCoef, setDamageCoef] = useState(100000);
  const [tempImpact, setTempImpact] = useState(0.2);
  const [waterAvail, setWaterAvail] = useState(0.8);
  const [paddyImpact, setPaddyImpact] = useState(0.1);
  const [leveeCost, setLeveeCost] = useState(3);
  const [migrationCost, setMigrationCost] = useState(2);
  const [rndCost, setRndCost] = useState(4);

  
  return (
    <Box sx={{ padding: 4 }}>
      <Typography variant="h4" gutterBottom>シミュレーション数式とパラメータ調整</Typography>

      <Box sx={{ marginBottom: 3 }}>
        <Link to="/" style={{ textDecoration: 'none' }}>
          <Button variant="contained" color="primary">戻る</Button>
        </Link>
      </Box>

      {/* 気温予測 */}
      <Paper sx={{ padding: 3, marginBottom: 4 }}>
        <Typography variant="h6">年平均気温の予測</Typography>
        <BlockMath math={`\\text{Temp}(t) = T_0 + \\alpha_T (t - t_0)`} />
        <Typography>気温上昇率（α<sub>T</sub>）: {tempTrend}</Typography>
        <Slider value={tempTrend} onChange={(e, val) => setTempTrend(val)} step={0.005} min={0.01} max={0.1} marks valueLabelDisplay="auto" />
        <Typography>計算結果（{year}年）: {expectedTemp.toFixed(2)} ℃</Typography>
      </Paper>

      {/* 高温日数の推定 */}
      <Paper sx={{ padding: 3, marginBottom: 4 }}>
        <Typography variant="h6">高温日数（Hot Days）の推定</Typography>
        <BlockMath math={`\\text{HotDays} = H_0 + \\beta_T (T - T_0)`} />
        <Typography>現在の気温 T: {temp} ℃</Typography>
        <Slider value={temp} onChange={(e, val) => setTemp(val)} step={0.5} min={10} max={40} marks valueLabelDisplay="auto" />
        <Typography>高温日数変化係数（β<sub>T</sub>）: {hotDaysCoeff}</Typography>
        <Slider value={hotDaysCoeff} onChange={(e, val) => setHotDaysCoeff(val)} step={0.1} min={0} max={5} marks valueLabelDisplay="auto" />
        <Typography>推定高温日数増加: {expectedHotDays.toFixed(2)} 日</Typography>
      </Paper>

      {/* 極端降水の頻度 */}
      <Paper sx={{ padding: 3, marginBottom: 4 }}>
        <Typography variant="h6">極端降水頻度の予測</Typography>
        <BlockMath math={`\\lambda(t) = \\lambda_0 + \\beta (t - t_0)`} />
        <Typography>年あたり増加率（β）: {extremeFreqTrend}</Typography>
        <Slider value={extremeFreqTrend} onChange={(e, val) => setExtremeFreqTrend(val)} step={0.01} min={0} max={0.2} marks valueLabelDisplay="auto" />
      </Paper>

      {/* 森林による洪水軽減効果 */}
      <Paper sx={{ padding: 3, marginBottom: 4 }}>
        <Typography variant="h6">森林による洪水軽減効果</Typography>
        <BlockMath math={`\\text{FloodReduction} = \\rho_f \\cdot \\frac{A_{\\text{forest}}}{A_{\\text{total}}}`} />
        <Typography>森林面積（ha）: {forestArea}</Typography>
        <Slider value={forestArea} onChange={(e, val) => setForestArea(val)} step={100} min={0} max={10000} marks valueLabelDisplay="auto" />
        <Typography>洪水軽減係数（ρ<sub>f</sub>）: {floodReductionCoef}</Typography>
        <Slider value={floodReductionCoef} onChange={(e, val) => setFloodReductionCoef(val)} step={0.05} min={0} max={1} marks valueLabelDisplay="auto" />
        <Typography>洪水軽減割合: {(floodReductionRate * 100).toFixed(1)}%</Typography>
      </Paper>


      {/* 災害被害の推定*/}
        <Paper sx={{ padding: 3, marginBottom: 4 }}>
        <Typography variant="h6">洪水被害の推定</Typography>
        <BlockMath math={`D = \\sum (R_i - L - P) \\cdot (1 - \\phi_{\\text{flood}}) \\cdot \\rho_D`} />
        <Typography>堤防の高さ L: {leveeLevel} mm</Typography>
        <Slider value={leveeLevel} onChange={(e, val) => setLeveeLevel(val)} step={10} min={0} max={300} marks valueLabelDisplay="auto" />
        <Typography>田んぼダムの軽減量 P: {paddyDam} mm</Typography>
        <Slider value={paddyDam} onChange={(e, val) => setPaddyDam(val)} step={1} min={0} max={50} marks valueLabelDisplay="auto" />
        <Typography>被害係数（ρ<sub>D</sub>）: {damageCoef.toLocaleString()}</Typography>
        <Slider value={damageCoef} onChange={(e, val) => setDamageCoef(val)} step={10000} min={10000} max={200000} marks valueLabelDisplay="auto" />
        </Paper>

      {/* 作物収量の推定*/}
        <Paper sx={{ padding: 3, marginBottom: 4 }}>
        <Typography variant="h6">作物収量の推定</Typography>
        <BlockMath math={`Y = Y_{\\max} \\cdot (1 - L_T) \\cdot \\phi_W \\cdot (1 - \\phi_{\\text{paddy}})`} />
        <Typography>温度被害 L<sub>T</sub>: {tempImpact}</Typography>
        <Slider value={tempImpact} onChange={(e, val) => setTempImpact(val)} step={0.01} min={0} max={1} marks valueLabelDisplay="auto" />
        <Typography>水の利用可能率 φ<sub>W</sub>: {waterAvail}</Typography>
        <Slider value={waterAvail} onChange={(e, val) => setWaterAvail(val)} step={0.01} min={0} max={1} marks valueLabelDisplay="auto" />
        <Typography>田んぼダムによる減少 φ<sub>paddy</sub>: {paddyImpact}</Typography>
        <Slider value={paddyImpact} onChange={(e, val) => setPaddyImpact(val)} step={0.01} min={0} max={1} marks valueLabelDisplay="auto" />
        </Paper>


    </Box>
  );
}

export default FormulaPage;
