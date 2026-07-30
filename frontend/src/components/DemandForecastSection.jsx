import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  RefreshCw,
  Sparkles,
  Search,
  Filter,
  Layers,
  Building2,
  ArrowUpDown,
  Calendar,
  Zap,
  Info,
  X
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid
} from 'recharts';

import {
  getForecastStatus,
  getAllForecasts,
  getShortageForecasts,
  generateForecasts
} from '../services/forecastApi';

const EQUIPMENT_TYPES = ['Excavator', 'Bulldozer', 'Grader', 'Crane', 'Loader', 'Roller'];

export default function DemandForecastSection() {
  // State
  const [allForecasts, setAllForecasts] = useState([]);
  const [shortages, setShortages] = useState([]);
  const [statusInfo, setStatusInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // UI Filters
  const [selectedSite, setSelectedSite] = useState('ALL');
  const [selectedEquipType, setSelectedEquipType] = useState('ALL');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('risk');
  const [sortDirection, setSortDirection] = useState('desc');

  // Generate POST Action State
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateResult, setGenerateResult] = useState(null);

  // Fetch forecast data with independent endpoint handling
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    const [statusRes, dataRes, shortageRes] = await Promise.allSettled([
      getForecastStatus(),
      getAllForecasts(),
      getShortageForecasts()
    ]);

    // 1. Status processing (exact snake_case fields: model_loaded, model_version, source_latest_week, forecast_week)
    if (statusRes.status === 'fulfilled' && statusRes.value) {
      const sVal = statusRes.value.data !== undefined ? statusRes.value.data : statusRes.value;
      setStatusInfo(sVal);
    } else {
      setStatusInfo({ model_loaded: false, error: statusRes.reason?.message });
    }

    // 2. All forecasts processing
    if (dataRes.status === 'fulfilled' && dataRes.value) {
      const dVal = dataRes.value.data !== undefined ? dataRes.value.data : dataRes.value;
      setAllForecasts(Array.isArray(dVal) ? dVal : []);
    } else {
      setAllForecasts([]);
    }

    // 3. Shortages processing
    if (shortageRes.status === 'fulfilled' && shortageRes.value) {
      const shVal = shortageRes.value.data !== undefined ? shortageRes.value.data : shortageRes.value;
      setShortages(Array.isArray(shVal) ? shVal : []);
    } else {
      setShortages([]);
    }

    // Only set top-level error if both status and allForecasts failed
    if (statusRes.status === 'rejected' && dataRes.status === 'rejected') {
      setError(
        dataRes.reason?.message ||
        statusRes.reason?.message ||
        'Failed to connect to forecast API'
      );
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Explicit POST /api/forecast/generate action
  const handleGenerateForecasts = async () => {
    setIsGenerating(true);
    setGenerateResult(null);
    try {
      const res = await generateForecasts();
      const resData = res?.data !== undefined ? res.data : res;
      setGenerateResult({
        type: 'success',
        message: `Forecasts generated for ${resData.forecast_date || 'next week'}`,
        details: `Inserted: ${resData.inserted_count ?? 0} · Updated: ${resData.updated_count ?? 0}`
      });
      fetchData();
    } catch (err) {
      setGenerateResult({
        type: 'error',
        message: 'Generate & Save failed',
        details: err.message
      });
    } finally {
      setIsGenerating(false);
    }
  };

  // ── DERIVED DATA ─────────────────────────────────────────────────────────

  // Unique site list derived dynamically from forecasts
  const availableSites = useMemo(() => {
    const map = new Map();
    allForecasts.forEach(f => {
      if (!map.has(f.site_id)) map.set(f.site_id, f.site_name || f.site_id);
    });
    return Array.from(map.entries())
      .map(([id, name]) => ({ site_id: id, site_name: name }))
      .sort((a, b) => a.site_id.localeCompare(b.site_id));
  }, [allForecasts]);

  // Client-side site filtering from loaded forecasts
  const siteFilteredForecasts = useMemo(() => {
    if (selectedSite === 'ALL') return allForecasts;
    return allForecasts.filter(f => f.site_id === selectedSite);
  }, [allForecasts, selectedSite]);

  // Summary metrics using exact snake_case backend fields
  const summaryMetrics = useMemo(() => {
    const rows = siteFilteredForecasts;
    const firstRow = rows[0] || {};
    const sInfo = statusInfo || {};

    const fWeek = firstRow.forecast_week || sInfo.forecast_week || '—';
    const sWeek = firstRow.source_week || sInfo.source_latest_week || '—';

    const totalCurrent = rows.reduce((s, f) => s + (f.current_demand || 0), 0);
    const totalPredicted = rows.reduce((s, f) => s + (f.predicted_demand || 0), 0);
    const totalAdditional = rows.reduce((s, f) => s + (f.additional_units_needed || 0), 0);
    const shortageCount = rows.filter(f => f.shortage_risk === true).length;

    return {
      forecastWeek: fWeek,
      sourceWeek: sWeek,
      totalCurrent,
      totalPredicted,
      totalAdditional,
      shortageCount
    };
  }, [siteFilteredForecasts, statusInfo]);

  // Grouped Bar Chart Data
  const chartData = useMemo(() => {
    const agg = {};
    EQUIPMENT_TYPES.forEach(t => { agg[t] = { equipment_type: t, current_demand: 0, predicted_demand: 0 }; });
    siteFilteredForecasts.forEach(f => {
      const t = f.equipment_type;
      if (agg[t]) {
        agg[t].current_demand  += f.current_demand  || 0;
        agg[t].predicted_demand += f.predicted_demand || 0;
      }
    });
    return EQUIPMENT_TYPES.map(t => agg[t]);
  }, [siteFilteredForecasts]);

  // Shortage Alert Panel List (Ordered HIGH > MEDIUM, then by raw_change desc)
  const panelShortages = useMemo(() => {
    let list = selectedSite === 'ALL'
      ? [...shortages]
      : shortages.filter(s => s.site_id === selectedSite);

    const w = { HIGH: 3, MEDIUM: 2, LOW: 1 };
    list.sort((a, b) => {
      const rDiff = (w[b.shortage_risk_level] || 0) - (w[a.shortage_risk_level] || 0);
      if (rDiff !== 0) return rDiff;
      const cA = (a.raw_model_prediction || 0) - (a.current_demand || 0);
      const cB = (b.raw_model_prediction || 0) - (b.current_demand || 0);
      if (Math.abs(cB - cA) > 0.001) return cB - cA;
      return (b.additional_units_needed || 0) - (a.additional_units_needed || 0);
    });
    return list;
  }, [shortages, selectedSite]);

  // Filtered & Sorted Table Data
  const tableData = useMemo(() => {
    let list = [...siteFilteredForecasts];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(f =>
        (f.site_name || '').toLowerCase().includes(q) ||
        (f.site_id || '').toLowerCase().includes(q) ||
        (f.equipment_type || '').toLowerCase().includes(q)
      );
    }
    if (selectedEquipType !== 'ALL') {
      list = list.filter(f => f.equipment_type === selectedEquipType);
    }
    if (riskFilter === 'HIGH_MED') {
      list = list.filter(f => f.shortage_risk_level === 'HIGH' || f.shortage_risk_level === 'MEDIUM');
    } else if (riskFilter === 'SHORTAGE_ONLY') {
      list = list.filter(f => f.shortage_risk === true);
    }

    const w = { HIGH: 3, MEDIUM: 2, LOW: 1 };
    list.sort((a, b) => {
      let vA, vB;
      if (sortField === 'risk')       { vA = w[a.shortage_risk_level] || 0; vB = w[b.shortage_risk_level] || 0; }
      else if (sortField === 'additional') { vA = a.additional_units_needed || 0; vB = b.additional_units_needed || 0; }
      else if (sortField === 'predicted')  { vA = a.predicted_demand || 0;  vB = b.predicted_demand || 0; }
      else if (sortField === 'equipment')  { vA = a.equipment_type || ''; vB = b.equipment_type || ''; }
      else { vA = a.site_id || ''; vB = b.site_id || ''; }

      if (vA < vB) return sortDirection === 'asc' ? -1 : 1;
      if (vA > vB) return sortDirection === 'asc' ?  1 : -1;
      return 0;
    });
    return list;
  }, [siteFilteredForecasts, searchQuery, selectedEquipType, riskFilter, sortField, sortDirection]);

  const toggleSort = (field) => {
    if (sortField === field) setSortDirection(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDirection('desc'); }
  };

  // ── RENDER ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">

      {/* ── HEADER ── */}
      <div className="bg-cat-card p-5 rounded-2xl border border-cat-border space-y-3">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-xl font-black text-white flex items-center gap-2">
                <TrendingUp className="w-6 h-6 text-cat-yellow" />
                DEMAND FORECAST &amp; SHORTAGE RISK RADAR
              </h2>
              {statusInfo?.model_loaded ? (
                <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-xs px-2.5 py-1 font-bold rounded-full flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Model Ready
                </span>
              ) : (
                <span className="bg-red-500/20 text-red-400 border border-red-500/40 text-xs px-2.5 py-1 font-bold rounded-full flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5" /> Model Unavailable
                </span>
              )}
            </div>
            <p className="text-xs text-cat-subtext mt-1">
              CatBoost ML · FP-Growth Association &amp; Transition Probability · Calibrated Change-Gated Hybrid
            </p>
          </div>

          {/* Model metadata badges */}
          <div className="flex flex-wrap gap-2">
            <div className="bg-cat-dark border border-cat-border px-3 py-1.5 rounded-lg text-[11px] font-mono">
              <span className="text-cat-subtext">Version: </span>
              <span className="text-cat-yellow font-bold">{statusInfo?.model_version || '—'}</span>
            </div>
            <div className="bg-cat-dark border border-cat-border px-3 py-1.5 rounded-lg text-[11px] font-mono">
              <span className="text-cat-subtext">Source Week: </span>
              <span className="text-slate-300 font-bold">{summaryMetrics.sourceWeek}</span>
            </div>
            <div className="bg-cat-dark border border-cat-border px-3 py-1.5 rounded-lg text-[11px] font-mono">
              <span className="text-cat-subtext">Forecast: </span>
              <span className="text-emerald-400 font-bold">{summaryMetrics.forecastWeek}</span>
            </div>
          </div>
        </div>

        {/* Generate result toast */}
        {generateResult && (
          <div className={`p-3.5 rounded-xl border flex items-center justify-between gap-3 text-xs ${
            generateResult.type === 'error'
              ? 'bg-red-950/80 border-red-500/50 text-red-200'
              : 'bg-emerald-950/80 border-emerald-500/50 text-emerald-200'
          }`}>
            <div className="flex items-center gap-2">
              {generateResult.type === 'error'
                ? <ShieldAlert className="w-4 h-4 text-red-400 shrink-0" />
                : <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              }
              <div>
                <span className="font-bold">{generateResult.message}</span>
                <span className="text-[11px] opacity-75 ml-2">{generateResult.details}</span>
              </div>
            </div>
            <button onClick={() => setGenerateResult(null)} className="text-cat-subtext hover:text-white p-1">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* ── SUMMARY CARDS ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {[
          { label: 'Forecast Week', value: summaryMetrics.forecastWeek, color: 'text-white', sub: '7-Day Forward Horizon', icon: <Calendar className="w-4 h-4 text-cat-yellow" /> },
          { label: 'Current Demand', value: summaryMetrics.totalCurrent, color: 'text-blue-400', sub: 'Active Site Units', icon: <Layers className="w-4 h-4 text-blue-400" /> },
          { label: 'Predicted Demand', value: summaryMetrics.totalPredicted, color: 'text-cat-yellow', sub: 'ML Operational Count', icon: <TrendingUp className="w-4 h-4 text-cat-yellow" /> },
          { label: 'Add. Units Needed', value: `+${summaryMetrics.totalAdditional}`, color: 'text-amber-400', sub: 'Net Equipment Deficit', icon: <Zap className="w-4 h-4 text-amber-400" /> },
          { label: 'Shortage Risks', value: summaryMetrics.shortageCount, color: 'text-red-400', sub: 'Threshold Crossed ≥0.20', icon: <AlertTriangle className="w-4 h-4 text-red-400" /> },
        ].map(card => (
          <div key={card.label} className="bg-cat-card p-4 rounded-xl border border-cat-border">
            <div className="flex items-center justify-between text-cat-subtext text-xs uppercase font-medium">
              <span>{card.label}</span>
              {card.icon}
            </div>
            <div className={`text-xl font-black font-mono mt-2 ${card.color}`}>{card.value}</div>
            <div className="text-[11px] text-cat-subtext mt-1">{card.sub}</div>
          </div>
        ))}
      </div>

      {/* ── FILTER & ACTION BAR ── */}
      <div className="bg-cat-card p-4 rounded-xl border border-cat-border flex flex-col md:flex-row justify-between items-stretch md:items-center gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Site selector */}
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-cat-yellow shrink-0" />
            <select
              value={selectedSite}
              onChange={e => setSelectedSite(e.target.value)}
              className="bg-cat-steel border border-cat-border text-white text-xs font-bold px-3 py-2 rounded-lg hover:border-cat-yellow transition-all"
              aria-label="Filter by site"
            >
              <option value="ALL">All Sites ({availableSites.length || 10})</option>
              {availableSites.map(s => (
                <option key={s.site_id} value={s.site_id}>
                  {s.site_id} – {s.site_name}
                </option>
              ))}
            </select>
          </div>

          {/* Equipment type selector */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-cat-subtext shrink-0" />
            <select
              value={selectedEquipType}
              onChange={e => setSelectedEquipType(e.target.value)}
              className="bg-cat-steel border border-cat-border text-slate-300 text-xs font-medium px-3 py-2 rounded-lg"
              aria-label="Filter by equipment type"
            >
              <option value="ALL">All Equipment Types</option>
              {EQUIPMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="w-4 h-4 text-cat-subtext absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search site or equipment…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              aria-label="Search forecasts"
              className="w-52 bg-cat-steel border border-cat-border text-white text-xs pl-9 pr-3 py-2 rounded-lg placeholder:text-cat-subtext/60 focus:border-cat-yellow outline-none transition-all"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Refresh */}
          <button
            onClick={fetchData}
            disabled={loading}
            title="Refresh forecast data"
            className="bg-cat-steel hover:bg-cat-border text-cat-subtext hover:text-white text-xs font-bold px-3 py-2 rounded-lg flex items-center gap-2 border border-cat-border transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cat-yellow' : ''}`} />
            Refresh
          </button>

          {/* Generate & Save — only fires on click */}
          <button
            onClick={handleGenerateForecasts}
            disabled={isGenerating || loading}
            className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all shadow-lg ${
              isGenerating
                ? 'bg-cat-steel text-cat-subtext cursor-not-allowed border border-cat-border'
                : 'bg-cat-yellow hover:bg-yellow-400 text-black shadow-cat-yellow/20'
            }`}
          >
            <Sparkles className={`w-4 h-4 ${isGenerating ? 'animate-spin' : ''}`} />
            {isGenerating ? 'Generating…' : 'Generate & Save Forecasts'}
          </button>
        </div>
      </div>

      {/* ── LOADING STATE ── */}
      {loading && (
        <div className="bg-cat-card p-12 rounded-2xl border border-cat-border text-center space-y-4">
          <div className="w-10 h-10 border-4 border-cat-yellow border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-bold text-white">Computing CatBoost Demand Inference…</p>
          <p className="text-xs text-cat-subtext">Evaluating 60 site-equipment series</p>
        </div>
      )}

      {/* ── ERROR STATE ── */}
      {!loading && error && (
        <div className="bg-red-950/60 border border-red-500/50 p-6 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <ShieldAlert className="w-8 h-8 text-red-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-red-200 text-sm">Forecast API Error</h4>
              <p className="text-xs text-red-300/80 mt-0.5">{error}</p>
            </div>
          </div>
          <button
            onClick={fetchData}
            className="bg-red-900 hover:bg-red-800 text-red-100 text-xs font-bold px-4 py-2 rounded-lg border border-red-700 transition-all shrink-0"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* ── MAIN CONTENT (Chart + Shortage Panel) ── */}
      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Demand Comparison Bar Chart */}
          <div className="lg:col-span-2 bg-cat-card p-6 rounded-2xl border border-cat-border space-y-4">
            <div className="border-b border-cat-border pb-3">
              <h3 className="font-black text-white text-base flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-cat-yellow" />
                DEMAND COMPARISON BY EQUIPMENT TYPE
              </h3>
              <p className="text-xs text-cat-subtext mt-0.5">
                {selectedSite === 'ALL'
                  ? 'Aggregated across all sites — Current vs ML Predicted Demand'
                  : `Site ${selectedSite} — Current vs ML Predicted Demand`
                }
              </p>
            </div>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -18, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2e37" vertical={false} />
                  <XAxis dataKey="equipment_type" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#181b20', borderColor: '#2a2e37', borderRadius: '0.75rem', color: '#f8fafc', fontSize: '12px' }}
                    cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                    formatter={(val, name) => [val, name]}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
                  <Bar dataKey="current_demand"   name="Current Demand"   fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="predicted_demand" name="Predicted Demand" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Shortage Alert Panel */}
          <div className="bg-cat-card p-5 rounded-2xl border border-cat-border flex flex-col gap-4">
            <div className="flex justify-between items-center border-b border-cat-border pb-3">
              <h3 className="font-black text-white text-base flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-400" />
                SHORTAGE ALERTS
              </h3>
              <span className="bg-red-500/20 text-red-400 text-xs px-2 py-0.5 font-bold rounded-full border border-red-500/30">
                {panelShortages.length} Risks
              </span>
            </div>

            {/* Disclaimer */}
            <div className="bg-cat-dark p-3 rounded-xl border border-cat-border flex items-start gap-2 text-[11px] text-slate-300">
              <Info className="w-4 h-4 text-cat-yellow shrink-0 mt-0.5" />
              <p>Possible additional equipment demand detected. Risk signals, not confirmed shortages.</p>
            </div>

            {/* Alert list */}
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1 flex-1">
              {panelShortages.length === 0 ? (
                <div className="py-10 text-center text-xs text-cat-subtext">
                  No shortage risk signals for selected filter.
                </div>
              ) : panelShortages.map((item, idx) => (
                <div
                  key={`${item.site_id}-${item.equipment_type}-${idx}`}
                  className="bg-cat-dark p-3 rounded-xl border border-cat-border hover:border-red-500/40 transition-all"
                >
                  <div className="flex justify-between items-start gap-2">
                    <div className="space-y-0.5 text-xs">
                      <div className="font-bold text-white leading-tight">{item.site_name || item.site_id}</div>
                      <div className="text-cat-subtext text-[11px]">{item.equipment_type}</div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        {item.current_demand} → <span className="text-cat-yellow font-bold">{item.predicted_demand}</span>
                        {' '}
                        <span className="text-amber-400">(+{item.additional_units_needed} needed)</span>
                      </div>
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded font-extrabold shrink-0 ${
                      item.shortage_risk_level === 'HIGH'
                        ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                        : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    }`}>
                      {item.shortage_risk_level}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── FORECAST TABLE ── */}
      {!loading && (
        <div className="bg-cat-card p-6 rounded-2xl border border-cat-border space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-cat-border pb-4">
            <div>
              <h3 className="font-black text-white text-lg flex items-center gap-2">
                <Layers className="w-5 h-5 text-cat-yellow" />
                FORECAST TABLE — {tableData.length} row{tableData.length !== 1 ? 's' : ''}
              </h3>
              <p className="text-xs text-cat-subtext mt-0.5">
                Click column headers to sort. Use filters above to narrow results.
              </p>
            </div>
            <select
              value={riskFilter}
              onChange={e => setRiskFilter(e.target.value)}
              aria-label="Risk filter"
              className="bg-cat-steel border border-cat-border text-white text-xs font-bold px-3 py-1.5 rounded-lg"
            >
              <option value="ALL">All Rows ({siteFilteredForecasts.length})</option>
              <option value="HIGH_MED">High &amp; Medium Risk Only</option>
              <option value="SHORTAGE_ONLY">Shortage Alerts Only ({panelShortages.length})</option>
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-200">
              <thead className="bg-cat-steel text-cat-subtext font-bold uppercase tracking-wider text-[11px] border-b border-cat-border">
                <tr>
                  <th className="py-3 px-4">Site</th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:text-white select-none"
                    onClick={() => toggleSort('equipment')}
                  >
                    <div className="flex items-center gap-1">Equipment <ArrowUpDown className="w-3 h-3" /></div>
                  </th>
                  <th className="py-3 px-4 text-center">Current</th>
                  <th
                    className="py-3 px-4 text-center cursor-pointer hover:text-white select-none"
                    onClick={() => toggleSort('predicted')}
                  >
                    <div className="flex items-center justify-center gap-1">Predicted <ArrowUpDown className="w-3 h-3" /></div>
                  </th>
                  <th className="py-3 px-4 text-center">Change</th>
                  <th
                    className="py-3 px-4 text-center cursor-pointer hover:text-white select-none"
                    onClick={() => toggleSort('additional')}
                  >
                    <div className="flex items-center justify-center gap-1">Add. Units <ArrowUpDown className="w-3 h-3" /></div>
                  </th>
                  <th
                    className="py-3 px-4 text-center cursor-pointer hover:text-white select-none"
                    onClick={() => toggleSort('risk')}
                  >
                    <div className="flex items-center justify-center gap-1">Risk <ArrowUpDown className="w-3 h-3" /></div>
                  </th>
                  <th className="py-3 px-4 text-center">Forecast Week</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-cat-border/50">
                {tableData.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-cat-subtext">
                      No rows match the selected filters. Try adjusting the search or risk filter.
                    </td>
                  </tr>
                ) : tableData.map((row, idx) => (
                  <tr key={`${row.site_id}-${row.equipment_type}-${idx}`} className="hover:bg-cat-steel/40 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-white leading-tight">{row.site_name || row.site_id}</div>
                      <div className="text-[10px] text-cat-subtext font-mono">{row.site_id}</div>
                    </td>
                    <td className="py-3 px-4 font-medium">{row.equipment_type}</td>
                    <td className="py-3 px-4 text-center font-mono font-bold text-blue-400">{row.current_demand}</td>
                    <td className="py-3 px-4 text-center font-mono font-black text-cat-yellow text-sm">{row.predicted_demand}</td>
                    <td className="py-3 px-4 text-center font-mono font-bold">
                      {row.predicted_change > 0
                        ? <span className="text-emerald-400">+{row.predicted_change}</span>
                        : row.predicted_change < 0
                          ? <span className="text-red-400">{row.predicted_change}</span>
                          : <span className="text-cat-subtext">0</span>
                      }
                    </td>
                    <td className="py-3 px-4 text-center font-mono font-bold">
                      {row.additional_units_needed > 0
                        ? <span className="text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">+{row.additional_units_needed}</span>
                        : <span className="text-cat-subtext">—</span>
                      }
                    </td>
                    <td className="py-3 px-4 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        {row.shortage_risk && (
                          <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" aria-label="Shortage risk alert" />
                        )}
                        <span className={`text-[10px] px-2.5 py-1 rounded font-bold ${
                          row.shortage_risk_level === 'HIGH'
                            ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                            : row.shortage_risk_level === 'MEDIUM'
                              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}>
                          {row.shortage_risk_level}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-center font-mono text-cat-subtext text-[11px]">{row.forecast_week}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
