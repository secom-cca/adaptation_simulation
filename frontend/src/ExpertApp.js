import React, { useMemo, useState, useEffect } from 'react';
import { Box, AppBar, Toolbar, Typography, Divider, Button, Paper, FormControl, InputLabel, Select, MenuItem, Stack, Slider, Alert, CircularProgress, Menu, Dialog, DialogTitle, DialogContent, DialogActions } from '@mui/material';
import Plot from 'react-plotly.js';
import MenuIcon from '@mui/icons-material/Menu';
import IconButton from '@mui/material/IconButton';
import axios from 'axios';


// 専門家向けのDMDUデータ分析UI
// - 3カラム構成: 左10% 入力、中央45% 散布図、右45% 時系列

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";

export default function ExpertApp() {
  const [scenario, setScenario] = useState('ALL');
  const [period, setPeriod] = useState(2050);
  
  // データベースオプション選択状態
  const [dbOptions, setDbOptions] = useState({
    planting_trees_amount_level: 0,
    dam_levee_construction_cost_level: 0,
    house_migration_amount_level: 0,
    paddy_dam_construction_cost_level: 0,
  });

  // Parameter filters for timeseries extraction (English keys from JSON)
  const [paramBounds, setParamBounds] = useState({}); // { key: {min, max} }
  const [paramFilters, setParamFilters] = useState({}); // applied values

  // 軸ラベル選択状態
  const [axisLabels, setAxisLabels] = useState({
    scatterX: 'Crop Yield',
    scatterY: 'Flood Damage',
    timeseriesMetric: 'Flood Damage'
  });

  // DMDUデータ連携状態
  const [dmduStatus, setDmduStatus] = useState('not-loaded'); // 'not-loaded', 'loading', 'loaded', 'error'
  const [dmduError, setDmduError] = useState('');
  const [meansData, setMeansData] = useState([]); // options_yearly_means.json
  const [timeseriesRaw, setTimeseriesRaw] = useState([]); // options_simulation_timeseries.json
  // AppBar menu & upload dialog
  const [menuAnchorEl, setMenuAnchorEl] = useState(null);
  const menuOpen = Boolean(menuAnchorEl);
  const [uploadOpen, setUploadOpen] = useState(false);

  const handleMenuOpen = (e) => setMenuAnchorEl(e.currentTarget);
  const handleMenuClose = () => setMenuAnchorEl(null);
  const handleOpenUpload = () => { setUploadOpen(true); handleMenuClose(); };
  const handleCloseUpload = () => setUploadOpen(false);

  const handleUploadFile = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    try {
      let loadedMeans = false;
      let loadedTs = false;
      for (const file of files) {
        const text = await file.text();
        const json = JSON.parse(text);
        if (!Array.isArray(json) || json.length === 0) continue;
        const first = json[0];
        // Detect timeseries vs means by fields
        if ((first && (first.series || first.simulation || first.params)) && !loadedTs) {
          setTimeseriesRaw(json);
          // Rebuild bounds for param sliders
          const keys = first.params ? Object.keys(first.params) : [];
          const bounds = {};
          for (const k of keys) bounds[k] = { min: Number.POSITIVE_INFINITY, max: Number.NEGATIVE_INFINITY };
          for (const rec of json) {
            const p = rec.params || {};
            for (const k of keys) {
              const v = Number(p[k]);
              if (!Number.isFinite(v)) continue;
              if (v < bounds[k].min) bounds[k].min = v;
              if (v > bounds[k].max) bounds[k].max = v;
            }
          }
          const filters = {};
          for (const k of Object.keys(bounds)) {
            const b = bounds[k];
            if (Number.isFinite(b.min) && Number.isFinite(b.max)) filters[k] = [b.min, b.max];
          }
          setParamBounds(bounds);
          setParamFilters(filters);
          loadedTs = true;
        } else if ((first && first.metrics) && !loadedMeans) {
          setMeansData(json);
          loadedMeans = true;
        }
      }
      if (loadedMeans && loadedTs) {
        setDmduStatus('loaded');
      } else {
        setDmduError('');
      }
      setUploadOpen(false);
    } catch (err) {
      console.warn('Failed to read uploaded files', err);
    } finally {
      e.target.value = '';
    }
  };

  // APIでデータをロード
  useEffect(() => {
    loadDMDUData();
  }, []);

  const loadDMDUData = async () => {
    setDmduStatus('loading');
    try {
      const response = await axios.post(`${BACKEND_URL}/load-dmdu-data`);
      setDmduStatus('loaded');
      console.log(response.data)
      // ローカルJSONの読み込み（public配下）
      try {
        const meansResp = await fetch('/options_yearly_means.json');
        const meansJson = await meansResp.json();
        setMeansData(meansJson);
      } catch (e) {
        console.warn('Failed to load options_yearly_means.json', e);
      }
      try {
        const tsResp = await fetch('/options_simulation_timeseries.json');
        const tsJson = await tsResp.json();
        setTimeseriesRaw(tsJson);
        // Build bounds and initial filters from params
        const first = tsJson.find(r => r && r.params && Object.keys(r.params).length > 0);
        const keys = first ? Object.keys(first.params) : [];
        const bounds = {};
        for (const k of keys) bounds[k] = { min: Number.POSITIVE_INFINITY, max: Number.NEGATIVE_INFINITY };
        for (const rec of tsJson) {
          const p = rec.params || {};
          for (const k of keys) {
            const v = Number(p[k]);
            if (!Number.isFinite(v)) continue;
            if (v < bounds[k].min) bounds[k].min = v;
            if (v > bounds[k].max) bounds[k].max = v;
          }
        }
        const filters = {};
        for (const k of Object.keys(bounds)) {
          const b = bounds[k];
          if (Number.isFinite(b.min) && Number.isFinite(b.max)) filters[k] = [b.min, b.max];
        }
        setParamBounds(bounds);
        setParamFilters(filters);
      } catch (e) {
        console.warn('Failed to load options_simulation_timeseries.json', e);
      }
    } catch (error) {
      setDmduStatus('error');
      setDmduError(error.response?.data?.detail || 'No Data Loaded');
    }
  };

  // （遅延なし）

  // (削除) クエリ実行機能は使用しない

  // データベースオプション変更ハンドラー
  const handleDbOptionChange = (option, value) => {
    setDbOptions(prev => ({
      ...prev,
      [option]: value
    }));
  };

  // (削除) クエリ実行機能は使用しない

  const availableMetrics = useMemo(() => [
    'Flood Damage',
    'Crop Yield',
    'Ecosystem Level',
    'Municipal Cost'
  ], []);

  // 右下パラメータ調整フィルタのUI（boundsから自動生成）
  const ParamFilters = () => {
    const keys = Object.keys(paramBounds || {}).filter(k => Number.isFinite(paramBounds[k]?.min) && Number.isFinite(paramBounds[k]?.max));
    if (!keys.length) return null;
    return (
      <Stack spacing={2} sx={{ mt: 1 }}>
        {keys.map((k) => {
          const b = paramBounds[k];
          const val = (paramFilters && paramFilters[k]) ? paramFilters[k] : [b.min, b.max];
          return (
            <Box key={k} sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="body2" sx={{ minWidth: 220 }} color="text.secondary">{k}</Typography>
              <Slider
                value={val}
                onChange={(_, newRange) => setParamFilters(prev => ({ ...prev, [k]: newRange }))}
                valueLabelDisplay="auto"
                min={b.min}
                max={b.max}
                marks={true}
                step={0.1}
                size="small"
                aria-label="small"
                sx={{
                  '& .MuiSlider-thumb': { pointerEvents: 'none' },
                  '& .MuiSlider-track': { pointerEvents: 'auto' },
                  '& .MuiSlider-rail': { pointerEvents: 'auto' }
                }}
              />
              <Typography variant="caption" sx={{ minWidth: 100 }} color="text.primary">{Number(val[0]).toFixed(2)} - {Number(val[1]).toFixed(2)}</Typography>
            </Box>
          );
        })}
      </Stack>
    );
  };

  // 散布図データ（meansから生成）
  const scatterData = useMemo(() => {
    if (!meansData?.length) return [];
    // 年・シナリオでフィルタ
    const filtered = meansData.filter(r => {
      const matchYear = (r.year ?? 0) === period;
      const matchScenario = scenario === 'ALL' ? true : (r.options?.RCP === scenario);
      return matchYear && matchScenario;
    });
    // optionsキーをシリアライズしシリーズ化（選択オプションは強調）
    const seriesMap = new Map();
    for (const rec of filtered) {
      const key = JSON.stringify(rec.options);
      const metrics = rec.metrics || {};
      const xv = metrics[axisLabels.scatterX] ?? null;
      const yv = metrics[axisLabels.scatterY] ?? null;
      if (xv == null || yv == null) continue;
      const isSelected = (
        rec.options?.planting_trees_amount_level === dbOptions.planting_trees_amount_level &&
        rec.options?.dam_levee_construction_cost_level === dbOptions.dam_levee_construction_cost_level &&
        rec.options?.house_migration_amount_level === dbOptions.house_migration_amount_level &&
        rec.options?.paddy_dam_construction_cost_level === dbOptions.paddy_dam_construction_cost_level
      );
      if (!seriesMap.has(key)) seriesMap.set(key, { x: [], y: [], customdata: [], name: key, selected: false });
      const s = seriesMap.get(key);
      s.x.push(xv);
      s.y.push(yv);
      s.customdata.push(key);
      if (isSelected) s.selected = true;
    }
    const ACCENT = '#e53935';
    const MUTED = '#b0b0b0';
    return Array.from(seriesMap.values()).map(s => ({
      ...s,
      type: 'scatter',
      mode: 'markers',
      marker: { size: s.selected ? 12 : 6, opacity: s.selected ? 1.0 : 0.35, color: s.selected ? ACCENT : MUTED },
      hovertemplate: (() => {
        const opts = JSON.parse(s.customdata[0] || '{}');
        const lines = [];
        if (opts.planting_trees_amount_level !== undefined) lines.push(`植林レベル: ${opts.planting_trees_amount_level}`);
        if (opts.dam_levee_construction_cost_level !== undefined) lines.push(`ダム・堤防レベル: ${opts.dam_levee_construction_cost_level}`);
        if (opts.house_migration_amount_level !== undefined) lines.push(`住宅移転レベル: ${opts.house_migration_amount_level}`);
        if (opts.paddy_dam_construction_cost_level !== undefined) lines.push(`田んぼダムレベル: ${opts.paddy_dam_construction_cost_level}`);
        if (opts.RCP) lines.push(`RCP: ${opts.RCP}`);
        return lines.join('<br>') + '<extra></extra>';
      })()
    }));
  }, [meansData, period, scenario, axisLabels, dbOptions.planting_trees_amount_level, dbOptions.dam_levee_construction_cost_level, dbOptions.house_migration_amount_level, dbOptions.paddy_dam_construction_cost_level]);

  // 散布図クリックでDBオプションへ反映
  const handleScatterClick = (event) => {
    const pt = event?.points?.[0];
    if (!pt || pt.customdata == null) return;
    try {
      const opts = typeof pt.customdata === 'string' ? JSON.parse(pt.customdata) : pt.customdata;
      const next = {
        planting_trees_amount_level: Number(opts?.planting_trees_amount_level),
        dam_levee_construction_cost_level: Number(opts?.dam_levee_construction_cost_level),
        house_migration_amount_level: Number(opts?.house_migration_amount_level),
        paddy_dam_construction_cost_level: Number(opts?.paddy_dam_construction_cost_level)
      };
      // いずれかが数値であれば反映
      if (Object.values(next).some(v => Number.isFinite(v))) {
        setDbOptions(prev => ({
          planting_trees_amount_level: Number.isFinite(next.planting_trees_amount_level) ? next.planting_trees_amount_level : prev.planting_trees_amount_level,
          dam_levee_construction_cost_level: Number.isFinite(next.dam_levee_construction_cost_level) ? next.dam_levee_construction_cost_level : prev.dam_levee_construction_cost_level,
          house_migration_amount_level: Number.isFinite(next.house_migration_amount_level) ? next.house_migration_amount_level : prev.house_migration_amount_level,
          paddy_dam_construction_cost_level: Number.isFinite(next.paddy_dam_construction_cost_level) ? next.paddy_dam_construction_cost_level : prev.paddy_dam_construction_cost_level
        }));
      }
    } catch (_) {
      // 解析失敗時は何もしない
    }
  };

  // パラレルカテゴリ（meansから生成・年度で平均済の値をそのまま使用）
  const parallelData = useMemo(() => {
    if (!meansData?.length) return { dimensions: [], customdata: [] };
    const fixedOutputMetrics = ['Flood Damage', 'Crop Yield', 'Ecosystem Level', 'Municipal Cost'];
    const metricDisplay = {
      'Flood Damage': 'Flood Damage',
      'Crop Yield': 'Crop Yield',
      'Ecosystem Level': 'Ecosystem Level',
      'Municipal Cost': 'Municipal Cost'
    };
    const filtered = meansData.filter(r => {
      const matchYear = (r.year ?? 0) === period;
      const matchScenario = scenario === 'ALL' ? true : (r.options?.RCP === scenario);
      return matchYear && matchScenario;
    });
    // 該当年の値のみ + 選択オプション強調
    const valuesByMetric = Object.fromEntries(fixedOutputMetrics.map(m => [m, []]));
    const highlight = [];
    const customdata = [];
    for (const rec of filtered) {
      const isSelected = (
        rec.options?.planting_trees_amount_level === dbOptions.planting_trees_amount_level &&
        rec.options?.dam_levee_construction_cost_level === dbOptions.dam_levee_construction_cost_level &&
        rec.options?.house_migration_amount_level === dbOptions.house_migration_amount_level &&
        rec.options?.paddy_dam_construction_cost_level === dbOptions.paddy_dam_construction_cost_level
      ) ? 1 : 0;
      highlight.push(isSelected);
      for (const m of fixedOutputMetrics) valuesByMetric[m].push(rec.metrics?.[m] ?? 0);
      
      // ホバー情報用のカスタムデータ
      const opts = rec.options || {};
      const lines = [];
      if (opts.planting_trees_amount_level !== undefined) lines.push(`植林レベル: ${opts.planting_trees_amount_level}`);
      if (opts.dam_levee_construction_cost_level !== undefined) lines.push(`ダム・堤防レベル: ${opts.dam_levee_construction_cost_level}`);
      if (opts.house_migration_amount_level !== undefined) lines.push(`住宅移転レベル: ${opts.house_migration_amount_level}`);
      if (opts.paddy_dam_construction_cost_level !== undefined) lines.push(`田んぼダムレベル: ${opts.paddy_dam_construction_cost_level}`);
      if (opts.RCP) lines.push(`RCP: ${opts.RCP}`);
      customdata.push(lines.join('<br>'));
    }
    return {
      dimensions: fixedOutputMetrics.map(cat => ({
        label: metricDisplay[cat] || cat,
        values: valuesByMetric[cat] || [],
        labelfont: { size: 12, color: '#424242' },
        tickfont: { size: 10, color: '#616161' }
      })),
      line: {
        color: highlight,
        colorscale: [[0, '#b0b0b0'], [1, '#e53935']],
        showscale: false,
        width: 2
      },
      customdata: customdata
    };
  }, [meansData, period, scenario, dbOptions.planting_trees_amount_level, dbOptions.dam_levee_construction_cost_level, dbOptions.house_migration_amount_level, dbOptions.paddy_dam_construction_cost_level]);

  // 時系列データ（options_simulation_timeseries.json を使用）
  const timeseriesTraces = useMemo(() => {
    if (!timeseriesRaw?.length) return [];
    // フィルタ: RCP と DBオプション完全一致
    const filtered = timeseriesRaw.filter(r => {
      const opt = r.options || {};
      const matchScenario = scenario === 'ALL' ? true : (opt.RCP === scenario);
      const matchOpts = (opt.planting_trees_amount_level === dbOptions.planting_trees_amount_level)
        && (opt.dam_levee_construction_cost_level === dbOptions.dam_levee_construction_cost_level)
        && (opt.house_migration_amount_level === dbOptions.house_migration_amount_level)
        && (opt.paddy_dam_construction_cost_level === dbOptions.paddy_dam_construction_cost_level);
      // 右下フィルタ（paramFilters）があれば適用
      const p = r.params || {};
      let matchParams = true;
      for (const [k, range] of Object.entries(paramFilters || {})) {
        const v = Number(p[k]);
        if (Number.isFinite(v)) {
          if (v < range[0] || v > range[1]) { matchParams = false; break; }
        }
      }
      return matchScenario && matchOpts && matchParams;
    });

    // 年配列が無い場合は series の長さから 2025 起点で再構築
    const metricKey = axisLabels.timeseriesMetric;
    const traces = [];
    for (const rec of filtered) {
      const series = rec.series || {};
      const y = Array.isArray(series[metricKey]) ? series[metricKey] : [];
      if (!y.length) continue;
      const years = Array.isArray(rec.years) && rec.years.length === y.length
        ? rec.years
        : Array.from({ length: y.length }, (_, i) => 2025 + i);
      traces.push({
        x: years,
        y,
        type: 'scatter',
        mode: 'lines',
        line: { width: 1, color: '#9e9e9e' },
        opacity: 0.15,
        hoverinfo: 'skip',
        showlegend: false,
        name: `sim-${rec.simulation}`
      });
    }
    return traces;
  }, [timeseriesRaw, scenario, dbOptions, axisLabels, paramFilters]);

  //







  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      <AppBar 
        position="fixed" 
        sx={{
          width: '100vw',
          height: 64,
          left: 0,
          right: 0,
          opacity: ({ scrollY }) => scrollY > 0 ? 0 : 1,
          transition: 'opacity 0.3s',
          '&:hover': {
            opacity: 1
          }
        }}
      >
        <Toolbar>
          <IconButton
            size="large"
            edge="start"
            color="inherit"
            aria-label="menu"
            sx={{ mr: 2 }}
            onClick={handleMenuOpen}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div">
            Analyze Dashboard
          </Typography>
          <Menu
            anchorEl={menuAnchorEl}
            open={menuOpen}
            onClose={handleMenuClose}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
            transformOrigin={{ vertical: 'top', horizontal: 'left' }}
          >
            <MenuItem onClick={handleOpenUpload}>Upload</MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      <Box sx={{ display: 'flex', width: '100%', pt: 8, height: '100%-64px' }}>
        <Dialog open={uploadOpen} onClose={handleCloseUpload} fullWidth maxWidth="sm">
          <DialogTitle>Upload JSON</DialogTitle>
          <DialogContent>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Select options_yearly_means.json または options_simulation_timeseries.json をアップロードしてください。
            </Typography>
            <Button variant="outlined" component="label">
              Choose Files
              <input type="file" accept="application/json" hidden multiple onChange={handleUploadFile} />
            </Button>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseUpload}>Close</Button>
          </DialogActions>
        </Dialog>
        <Box sx={{ width: '10%', minWidth: 160, borderRight: '1px solid rgba(0,0,0,0.12)', p: 2, height: 'calc(100vh - 64px)', overflow: 'auto' }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>入力</Typography>
            <Divider sx={{ mb: 2 }} />
            
            <Box sx={{ mb: 2 }}>
              {dmduStatus === 'not-loaded' && (
                <Alert severity="info">DMDUデータを読み込み中...</Alert>
              )}
              {dmduStatus === 'loading' && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CircularProgress size={20} />
                  <Typography variant="caption">データロード中...</Typography>
                </Box>
              )}
              {dmduStatus === 'loaded' && (
                <Alert severity="success">
                  Data loaded successfully
                </Alert>
              )}
              {dmduStatus === 'error' && (
                <Alert severity="error">{dmduError}</Alert>
              )}
            </Box>
          <Stack spacing={2}>
            <FormControl fullWidth>
              <InputLabel id="scenario-label">シナリオ</InputLabel>
              <Select labelId="scenario-label" value={scenario} label="シナリオ" onChange={(e) => setScenario(e.target.value)} size="small" aria-label="small">
                <MenuItem value={'ALL'}>ALL</MenuItem>
                <MenuItem value={'RCP1.9'}>RCP1.9</MenuItem>
                <MenuItem value={'RCP2.6'}>RCP2.6</MenuItem>
                <MenuItem value={'RCP4.5'}>RCP4.5</MenuItem>
                <MenuItem value={'RCP6.0'}>RCP6.0</MenuItem>
                <MenuItem value={'RCP8.5'}>RCP8.5</MenuItem>
              </Select>
            </FormControl>

            <Box sx={{ px: 2 }}>
              <Typography gutterBottom>年（Year）</Typography>
              <Slider
                value={period}
                onChange={(e, newValue) => setPeriod(newValue)}
                valueLabelDisplay="auto"
                min={2025}
                max={2100}
                step={1}
                size="small"
                aria-label="small"
                marks={[
                  { value: 2025, label: '2025' },
                  { value: 2100, label: '2100' }
                ]}
              />
            </Box>

            <Divider sx={{ mb: 2 }} />
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>データベースオプション</Typography>
            
            <Box sx={{ px: 2 }}>
              <Typography gutterBottom>植林・森林保全レベル</Typography>
              <Slider
                value={dbOptions.planting_trees_amount_level}
                onChange={(e, newValue) => handleDbOptionChange('planting_trees_amount_level', newValue)}
                valueLabelDisplay="auto"
                min={0}
                max={2}
                step={1}
                size="small"
                aria-label="small"
                marks={[
                  { value: 0, label: '0' },
                  { value: 1, label: '1' },
                  { value: 2, label: '2' }
                ]}
              />
            </Box>

            <Box sx={{ px: 2 }}>
              <Typography gutterBottom>ダム・堤防工事レベル</Typography>
              <Slider
                value={dbOptions.dam_levee_construction_cost_level}
                onChange={(e, newValue) => handleDbOptionChange('dam_levee_construction_cost_level', newValue)}
                valueLabelDisplay="auto"
                min={0}
                max={2}
                step={1}
                size="small"
                aria-label="small"
                marks={[
                  { value: 0, label: '0' },
                  { value: 1, label: '1' },
                  { value: 2, label: '2' }
                ]}
              />
            </Box>

            <Box sx={{ px: 2 }}>
              <Typography gutterBottom>住宅移転レベル</Typography>
              <Slider
                value={dbOptions.house_migration_amount_level}
                onChange={(e, newValue) => handleDbOptionChange('house_migration_amount_level', newValue)}
                valueLabelDisplay="auto"
                min={0}
                max={2}
                step={1}
                size="small"
                aria-label="small"
                marks={[
                  { value: 0, label: '0' },
                  { value: 1, label: '1' },
                  { value: 2, label: '2' }
                ]}
              />
            </Box>

            <Box sx={{ px: 2 }}>
              <Typography gutterBottom>田んぼダム工事レベル</Typography>
              <Slider
                value={dbOptions.paddy_dam_construction_cost_level}
                onChange={(e, newValue) => handleDbOptionChange('paddy_dam_construction_cost_level', newValue)}
                valueLabelDisplay="auto"
                min={0}
                max={2}
                step={1}
                size="small"
                aria-label="small"
                marks={[
                  { value: 0, label: '0' },
                  { value: 1, label: '1' },
                  { value: 2, label: '2' }
                ]}
              />
            </Box>

            {/* 軸設定は各図のPaper内に移動 */}
          </Stack>
        </Box>

        <Box sx={{ width: '45%', p: 2, borderRight: '1px solid rgba(0,0,0,0.12)', height: 'calc(100vh - 64px)', overflow: 'hidden' }}>
          <Stack spacing={1} sx={{ height: '100%' }}>
            <Typography variant="subtitle2" color="text.secondary">散布図</Typography>
            <Paper sx={{ p: 1, pt: 3, pb: 10, flex: 1, height: 'calc(50vh - 80px)', position: 'relative' }}>
                <Typography
                  variant="caption"
                  sx={{ position: 'absolute', left: 4, top: '50%', transform: 'translateY(-50%) rotate(-90deg)', transformOrigin: 'left top', pointerEvents: 'none' }}
                  color="text.secondary"
                >
                  {axisLabels.scatterY}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ position: 'absolute', left: '50%', bottom: 8, transform: 'translateX(-50%)', pointerEvents: 'none' }}
                  color="text.secondary"
                >
                  {axisLabels.scatterX}
                </Typography>
                <Plot
                  data={scatterData}
                  layout={{
                    title: { text: '', x: 0 },
                    font: { size: 10 },
                  margin: { t: 20, l: 60, r: 10, b: 64 },
                    plot_bgcolor: 'transparent',
                    paper_bgcolor: 'transparent',
                  xaxis: { 
                    showgrid: true, 
                    gridcolor: 'rgba(0,0,0,0.1)',
                    title: axisLabels.scatterX
                  },
                  yaxis: { 
                    showgrid: true, 
                    gridcolor: 'rgba(0,0,0,0.1)',
                    title: axisLabels.scatterY
                  },
                  showlegend: false,
                    autosize: true,
                    hovermode: 'closest',
                    hoverdistance: 50
                  }}
                  config={{ 
                    responsive: true, 
                    displayModeBar: false,
                    modeBarButtonsToRemove: [],
                    toImageButtonOptions: {
                      format: 'png',
                      filename: 'scatter_plot',
                      height: 500,
                      width: 700,
                      scale: 1
                    }
                  }}
                  style={{ width: '100%', height: '100%' }}
                  onClick={handleScatterClick}
                />
                <Box sx={{ position: 'absolute', left: 8, right: 8, bottom: 8, display: 'flex', gap: 1, alignItems: 'center', bgcolor: 'background.paper', px: 1, py: 0.5, borderRadius: 1, boxShadow: 1 }}>
                  <FormControl size="small" sx={{ minWidth: 140 }}>
                    <InputLabel id="scatter-x-label">X軸</InputLabel>
                    <Select labelId="scatter-x-label" value={axisLabels.scatterX} label="X軸" onChange={(e) => setAxisLabels(prev => ({ ...prev, scatterX: e.target.value }))}>
                      {availableMetrics.map((m) => (<MenuItem key={m} value={m}>{m}</MenuItem>))}
                    </Select>
                  </FormControl>
                  <FormControl size="small" sx={{ minWidth: 140 }}>
                    <InputLabel id="scatter-y-label">Y軸</InputLabel>
                    <Select labelId="scatter-y-label" value={axisLabels.scatterY} label="Y軸" onChange={(e) => setAxisLabels(prev => ({ ...prev, scatterY: e.target.value }))}>
                      {availableMetrics.map((m) => (<MenuItem key={m} value={m}>{m}</MenuItem>))}
                    </Select>
                  </FormControl>
                </Box>
              </Paper>

            <Typography variant="subtitle2" color="text.secondary">パラレルカテゴリ</Typography>
            <Paper sx={{ p: 1, pb: 6, flex: 1, height: 'calc(50vh - 80px)', position: 'relative' }}>
                <Plot
                  data={[{
                    type: 'parcoords',
                    line: {
                      colorscale: [
                        [0, 'rgb(33, 150, 243)'],
                        [1, 'rgb(63, 81, 181)']
                      ],
                      color: Array.from({ length: 30 }, () => Math.random()),
                      showscale: false,
                    },
                    ...parallelData,
                    hovertemplate: '%{customdata}<extra></extra>'
                  }]}
                  layout={{
                    title: { text: '', x: 0 },
                    font: { size: 10 },
                    margin: { t: 36, l: 40, r: 10, b: 20 },
                    plot_bgcolor: 'transparent',
                    paper_bgcolor: 'transparent',
                    autosize: true,
                    hovermode: 'closest',
                    hoverdistance: 50
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: '100%', height: '100%' }}
                />
              </Paper>
          </Stack>
        </Box>

        <Box sx={{ width: '45%', p: 2, height: 'calc(100vh - 64px)', overflow: 'hidden' }}>
          <Stack spacing={1} sx={{ height: '100%' }}>
            {/* 折れ線グラフエリア */}
            <Typography variant="subtitle2" color="text.secondary">時系列分析</Typography>
            <Paper sx={{ p: 1, pb: 10, flex: 1, height: '40vh', position: 'relative' }}>
              <Typography
                variant="caption"
                sx={{ position: 'absolute', left: 4, top: '50%', transform: 'translateY(-50%) rotate(-90deg)', transformOrigin: 'left top', pointerEvents: 'none' }}
                color="text.secondary"
              >
                {axisLabels.timeseriesMetric}
              </Typography>
              <Plot
                data={timeseriesTraces}
                layout={{
                  title: { text: '', x: 0 },
                  font: { size: 12 },
                  margin: { t: 20, l: 60, r: 10, b: 52 },
                  plot_bgcolor: 'transparent',
                  paper_bgcolor: 'transparent',
                  xaxis: { 
                    showgrid: true, 
                    gridcolor: 'rgba(0,0,0,0.1)',
                    title: ''
                  },
                  yaxis: { 
                    showgrid: true, 
                    gridcolor: 'rgba(0,0,0,0.1)',
                    title: axisLabels.timeseriesMetric
                  },
                  showlegend: false
                }}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%', height: '100%' }}
              />
              <Box sx={{ position: 'absolute', left: 8, bottom: 8, display: 'flex', gap: 1, alignItems: 'center', bgcolor: 'background.paper', px: 1, py: 0.5, borderRadius: 1, boxShadow: 1 }}>
                <FormControl size="small" sx={{ minWidth: 180 }}>
                  <InputLabel id="timeseries-label">Y軸</InputLabel>
                  <Select labelId="timeseries-label" value={axisLabels.timeseriesMetric} label="Y軸" onChange={(e) => setAxisLabels(prev => ({ ...prev, timeseriesMetric: e.target.value }))}>
                    {availableMetrics.map((m) => (<MenuItem key={m} value={m}>{m}</MenuItem>))}
                  </Select>
                </FormControl>
              </Box>
            </Paper>

            {/* Range sliderエリア */}
            <Typography variant="subtitle2" color="text.secondary">パラメータ調整</Typography>
            <Paper sx={{ p: 2, flex: 1, height: 'calc(60vh - 60px)', overflow: 'auto', mt: 2 }}>
              <Box sx={{ mb: 2 }}></Box>
              <ParamFilters />
            </Paper>
          </Stack>
        </Box>
      </Box>
    </Box>
  );
}


