import React, { useState } from 'react';
import {
  Activity, AlertTriangle, CheckCircle2, Cpu, Shield, Zap,
  ChevronDown, ChevronUp, Search, RefreshCw, BarChart3,
  Gauge, User, XCircle, Filter
} from 'lucide-react';

// ── Severity config ──────────────────────────────────────────────────────────
const SEVERITY = {
  CRITICAL: { color: '#A855F7', bg: 'bg-purple-500/10', border: 'border-purple-500/30', text: 'text-purple-400', label: 'CRITICAL', order: 0 },
  HIGH:     { color: '#EF4444', bg: 'bg-red-500/10',    border: 'border-red-500/30',    text: 'text-red-400',    label: 'HIGH',     order: 1 },
  MEDIUM:   { color: '#F97316', bg: 'bg-orange-500/10', border: 'border-orange-500/30', text: 'text-orange-400', label: 'MEDIUM',   order: 2 },
  LOW:      { color: '#EAB308', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400', label: 'LOW',      order: 3 },
  CLEAN:    { color: '#10B981', bg: 'bg-emerald-500/10',border: 'border-emerald-500/30',text: 'text-emerald-400',label: 'CLEAN',    order: 4 },
};

const RULE_META = {
  GHOST_IDLING: {
    icon: Activity, label: 'Ghost / Phantom Idling',
    desc: 'Engine Hours = 0 while Idle Hours > 0 — ignition active, engine NOT running',
    color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/30',
  },
  CONSTRAINT_VIOLATION_HIGH_IER: {
    icon: Gauge, label: 'Constraint Violation — High IER',
    desc: 'Idle Hours ≥ Engine Hours (IER ≥ 50%) — excessive key-on idling',
    color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30',
  },
  UNASSIGNED_USAGE: {
    icon: XCircle, label: 'Unassigned Asset Usage',
    desc: 'Active telemetry detected while Site ID = NULL — no site assignment',
    color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30',
  },
  MISSING_OPERATOR: {
    icon: User, label: 'Missing Operator',
    desc: 'Equipment operating with Operator ID = NULL — safety & compliance risk',
    color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30',
  },
  BEHAVIORAL_OUTLIER: {
    icon: Cpu, label: 'Behavioral Outlier (SVM)',
    desc: 'Operating pattern deviates from healthy baseline — unusual duty cycle or contextual under-utilization',
    color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/30',
  },
};

// ── Sub-components ───────────────────────────────────────────────────────────

function SeverityBadge({ severity }) {
  const s = SEVERITY[severity] || SEVERITY.CLEAN;
  return (
    <span className={`text-[10px] font-black px-2 py-0.5 rounded tracking-wider border ${s.bg} ${s.border} ${s.text}`}>
      {s.label}
    </span>
  );
}

function MetricCard({ label, value, sub, color = 'text-white', icon: Icon }) {
  return (
    <div className="bg-cat-card p-5 rounded-2xl border border-cat-border space-y-1">
      <div className="flex items-center gap-2 text-cat-subtext text-[11px] uppercase font-bold tracking-wider">
        {Icon && <Icon className="w-3.5 h-3.5" />}
        {label}
      </div>
      <div className={`text-3xl font-black font-mono ${color}`}>{value}</div>
      {sub && <p className="text-[11px] text-cat-subtext leading-normal">{sub}</p>}
    </div>
  );
}

function SeverityBar({ breakdown, total }) {
  const order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'CLEAN'];
  return (
    <div className="bg-cat-card p-5 rounded-2xl border border-cat-border">
      <h3 className="text-xs font-bold text-cat-subtext uppercase tracking-wider mb-3">Severity Distribution</h3>
      <div className="space-y-2.5">
        {order.map(sev => {
          const count = breakdown[sev] || 0;
          const pct = total > 0 ? ((count / total) * 100).toFixed(1) : '0';
          const s = SEVERITY[sev];
          return (
            <div key={sev} className="flex items-center gap-3">
              <span className={`text-[10px] font-black w-16 shrink-0 ${s.text}`}>{sev}</span>
              <div className="flex-1 bg-cat-steel rounded-full h-2 overflow-hidden">
                <div
                  className="h-2 rounded-full transition-all duration-700"
                  style={{ width: `${pct}%`, backgroundColor: s.color }}
                />
              </div>
              <span className="text-[11px] font-mono text-slate-300 w-16 text-right shrink-0">
                {count} ({pct}%)
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AnomalyCard({ record }) {
  const [expanded, setExpanded] = useState(false);
  const s = SEVERITY[record.severity] || SEVERITY.CLEAN;
  const isCritical = record.severity === 'CRITICAL';

  return (
    <div
      className={`bg-cat-card rounded-2xl border overflow-hidden transition-all duration-300 ${s.border}`}
      style={{ boxShadow: isCritical ? `0 0 20px ${s.color}18` : 'none' }}
    >
      {/* Left severity bar */}
      <div className="flex">
        <div className="w-1.5 shrink-0" style={{ backgroundColor: s.color }} />

        <div className="flex-1 p-4">
          {/* Header row */}
          <div className="flex flex-wrap items-center gap-2 justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={record.severity} />
              {record.has_rule_violation && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded border bg-red-500/10 border-red-500/30 text-red-400 tracking-wider flex items-center gap-1">
                  <Shield className="w-3 h-3" /> L1 RULE
                </span>
              )}
              {record.layer2_svm_outlier && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded border bg-purple-500/10 border-purple-500/30 text-purple-400 tracking-wider flex items-center gap-1">
                  <Cpu className="w-3 h-3" /> L2 SVM
                </span>
              )}
            </div>
            <button
              onClick={() => setExpanded(e => !e)}
              className="text-cat-subtext hover:text-white transition-colors p-1 rounded"
            >
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>

          {/* Equipment + site */}
          <div className="mt-2 flex flex-wrap gap-4 items-start">
            <div>
              <span className="text-cat-subtext text-[9px] uppercase font-bold block">Equipment</span>
              <span className="font-mono font-black text-cat-yellow text-sm">{record.equipment_id}</span>
              <span className="text-cat-subtext text-xs ml-1">({record.equipment_type})</span>
            </div>
            <div>
              <span className="text-cat-subtext text-[9px] uppercase font-bold block">Site</span>
              <span className="text-slate-200 text-sm font-semibold">{record.site_name}</span>
            </div>
            <div>
              <span className="text-cat-subtext text-[9px] uppercase font-bold block">Operator</span>
              <span className="text-slate-200 text-sm font-semibold">{record.operator_name}</span>
            </div>
            <div>
              <span className="text-cat-subtext text-[9px] uppercase font-bold block">Rental Period</span>
              <span className="text-slate-200 text-sm font-semibold">{record.rental_days} days</span>
            </div>
          </div>

          {/* Metrics mini-grid: key telemetry signals */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 bg-cat-dark p-3 rounded-xl border border-cat-border/50 text-[11px]">
            <div>
              <span className="text-cat-subtext text-[9px] uppercase block">Engine Hrs/Day</span>
              <span className={`font-mono font-black ${
                record.engine_hours_per_day === 0 && record.idle_hours_per_day > 0
                  ? 'text-purple-400' : 'text-white'
              }`}>
                {record.engine_hours_per_day}h
              </span>
            </div>
            <div>
              <span className="text-cat-subtext text-[9px] uppercase block">Idle Hrs/Day</span>
              <span className={`font-mono font-black ${
                record.idle_hours_per_day >= record.engine_hours_per_day && record.engine_hours_per_day > 0
                  ? 'text-red-400' : 'text-white'
              }`}>{record.idle_hours_per_day}h</span>
            </div>
            <div>
              <span className="text-cat-subtext text-[9px] uppercase block">IER %</span>
              <span className={`font-mono font-black ${
                record.ier_pct >= 50 ? 'text-red-400' : 'text-emerald-400'
              }`}>
                {record.ier_pct}%
              </span>
            </div>
            <div>
              <span className="text-cat-subtext text-[9px] uppercase block">Site / Operator</span>
              <span className={`font-mono font-black text-[10px] ${
                !record.site_id || !record.operator_id ? 'text-orange-400' : 'text-white'
              }`}>
                {record.site_id ? '✓ Site' : '✗ No Site'} / {record.operator_id ? '✓ Op' : '✗ No Op'}
              </span>
            </div>
          </div>

          {/* Expanded detail */}
          {expanded && (
            <div className="mt-4 space-y-3 border-t border-cat-border pt-4">
              {/* Layer 1 violations */}
              {record.layer1_violations.length > 0 && (
                <div>
                  <h4 className="text-[10px] font-black text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-red-400" /> Layer 1 — Rule Engine Violations
                  </h4>
                  <div className="space-y-2">
                    {record.layer1_violations.map((v, idx) => {
                      const meta = RULE_META[v.flag] || RULE_META[v.rule] || {};
                      const RuleIcon = meta.icon || AlertTriangle;
                      const metaColor = meta.color || 'text-red-400';
                      const metaBg = meta.bg || 'bg-red-500/10';
                      const metaBorder = meta.border || 'border-red-500/30';
                      return (
                        <div key={idx} className={`flex gap-3 items-start p-3 rounded-xl border ${metaBg} ${metaBorder}`}>
                          <RuleIcon className={`w-4 h-4 shrink-0 mt-0.5 ${metaColor}`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className={`text-[10px] font-black font-mono ${metaColor}`}>{v.flag}</span>
                              <SeverityBadge severity={v.severity} />
                            </div>
                            <p className="text-[11px] text-white font-semibold mt-0.5">{v.title}</p>
                            <p className="text-[11px] text-slate-300 mt-0.5">{v.description}</p>
                            <div className="flex flex-wrap gap-4 mt-1.5 text-[10px]">
                              <span className="text-cat-subtext">Detected: <span className="text-white font-mono font-bold">{v.detected_value}</span></span>
                              <span className="text-cat-subtext">Rule: <span className="text-emerald-400 font-mono font-bold">{v.boundary}</span></span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Layer 2 SVM result */}
              <div>
                <h4 className="text-[10px] font-black text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-purple-400" /> Layer 2 — One-Class SVM (RBF Kernel)
                </h4>
                <div className={`p-3.5 rounded-xl border ${record.layer2_svm_outlier ? 'bg-purple-500/10 border-purple-500/30' : 'bg-emerald-500/10 border-emerald-500/30'}`}>
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className={`text-sm font-black flex items-center gap-1.5 ${record.layer2_svm_outlier ? 'text-purple-400' : 'text-emerald-400'}`}>
                      {record.layer2_svm_outlier ? (
                        <>⚠ {record.svm_reason || 'Behavioral Outlier Detected'}</>
                      ) : (
                        '✓ Within Normal Behavioral Profile'
                      )}
                    </span>
                    <span className="text-[10px] font-mono text-cat-subtext">
                      Decision Score: <span className={`font-bold ${record.svm_decision_score < 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                        {record.svm_decision_score}
                      </span>
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 mt-1.5 leading-relaxed">
                    {record.layer2_svm_outlier
                      ? (record.svm_description || 'Operating pattern is statistically unusual compared to normal fleet behavior.')
                      : 'Operating pattern matches the synthetic healthy baseline. No behavioral anomaly detected by the SVM model.'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function AnomalyDetection() {
  const [scanData, setScanData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [layerFilter, setLayerFilter] = useState('ALL'); // ALL, LAYER1, LAYER2, BOTH
  const [search, setSearch] = useState('');

  const runScan = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/anomaly/scan');
      if (!res.ok) throw new Error(`Scan failed: ${res.status}`);
      const data = await res.json();
      setScanData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Filtered records
  const filteredRecords = (scanData?.anomalies || []).filter(r => {
    if (r.severity === 'CLEAN') return false; // Always exclude normal records from anomaly list
    if (severityFilter !== 'ALL' && r.severity !== severityFilter) return false;
    if (layerFilter === 'LAYER1' && !r.has_rule_violation) return false;
    if (layerFilter === 'LAYER2' && !r.layer2_svm_outlier) return false;
    if (layerFilter === 'BOTH' && !(r.has_rule_violation && r.layer2_svm_outlier)) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        r.equipment_id.toLowerCase().includes(q) ||
        r.site_name.toLowerCase().includes(q) ||
        r.operator_name.toLowerCase().includes(q) ||
        r.equipment_type.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const summary = scanData?.summary;
  const breakdown = scanData?.severity_breakdown || {};
  const svmConfig = scanData?.pipeline_config?.layer2_svm;
  const layer1Rules = scanData?.pipeline_config?.layer1_rules || [];
  const ierThreshold = scanData?.pipeline_config?.ier_violation_threshold_pct;

  return (
    <div className="space-y-6 text-left">
      {/* Header */}
      <div className="bg-cat-card p-6 rounded-2xl border border-cat-border/80 flex flex-col md:flex-row gap-5 justify-between items-start md:items-center">
        <div className="flex items-start gap-3">
          <div className="bg-purple-500/20 p-3 rounded-xl text-purple-400 shrink-0">
            <Activity className="w-7 h-7" />
          </div>
          <div>
            <h2 className="text-xl font-black text-white tracking-tight">FLEET ANOMALY DETECTION ENGINE</h2>
            <p className="text-xs text-cat-subtext mt-1 leading-relaxed max-w-xl">
              Two-layer hybrid detection: <span className="text-white font-semibold">Deterministic Rule Engine</span> (instant boundary enforcement) +{' '}
              <span className="text-purple-400 font-semibold">One-Class SVM</span> with RBF Kernel trained on a synthetic healthy operating baseline.
            </p>
          </div>
        </div>

        <button
          onClick={runScan}
          disabled={loading}
          className={`shrink-0 flex items-center gap-2.5 px-6 py-3 rounded-xl font-black text-sm transition-all ${
            loading
              ? 'bg-cat-steel text-cat-subtext cursor-not-allowed'
              : 'bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-500/20 hover:scale-[1.02] active:scale-[0.98]'
          }`}
        >
          {loading ? (
            <><RefreshCw className="w-4 h-4 animate-spin" /> Scanning Fleet...</>
          ) : (
            <><Activity className="w-4 h-4" /> Run Anomaly Scan</>
          )}
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 p-4 rounded-xl text-red-400 text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Pre-scan state */}
      {!scanData && !loading && !error && (
        <div className="bg-cat-card/50 border border-cat-border/60 rounded-2xl p-14 text-center space-y-4">
          <div className="w-16 h-16 mx-auto bg-purple-500/10 rounded-2xl flex items-center justify-center">
            <Activity className="w-8 h-8 text-purple-400" />
          </div>
          <h3 className="text-white font-bold text-lg">Anomaly Scanner Ready</h3>
          <p className="text-cat-subtext text-sm max-w-md mx-auto leading-relaxed">
            Click <strong className="text-white">Run Anomaly Scan</strong> to analyze all fleet rental records using the two-layer detection engine.
          </p>
          {/* Architecture explainer */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl mx-auto mt-6 text-left">
            <div className="bg-cat-card p-4 rounded-xl border border-red-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="w-4 h-4 text-red-400" />
                <span className="text-sm font-black text-red-400">Layer 1 — Rule Engine</span>
              </div>
              <ul className="text-[11px] text-cat-subtext space-y-1.5">
                <li className="text-purple-300">• <span className="font-bold">GHOST_IDLING</span> — Engine=0 &amp; Idle&gt;0 (phantom ignition)</li>
                <li className="text-red-300">• <span className="font-bold">CONSTRAINT_VIOLATION_HIGH_IER</span> — Idle ≥ Engine (IER ≥ 50%)</li>
                <li className="text-orange-300">• <span className="font-bold">UNASSIGNED_USAGE</span> — Active telemetry + Site ID=NULL</li>
                <li className="text-orange-300">• <span className="font-bold">MISSING_OPERATOR</span> — Active telemetry + Operator ID=NULL</li>
              </ul>
            </div>
            <div className="bg-cat-card p-4 rounded-xl border border-purple-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Cpu className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-black text-purple-400">Layer 2 — One-Class SVM</span>
              </div>
              <ul className="text-[11px] text-cat-subtext space-y-1.5">
                <li>• Kernel: <span className="text-white font-bold">RBF</span>, ν = 0.05</li>
                <li>• Trained on <span className="text-white font-bold">600 synthetic healthy records</span></li>
                <li>• Features: engine hrs, idle hrs, IER%</li>
                <li>• Score &lt; 0 → <span className="text-purple-300 font-bold">BEHAVIORAL_OUTLIER</span></li>
                <li>• Catches contextual under-utilization &amp; unusual duty cycles</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {scanData && (
        <>
          {/* Summary metric cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MetricCard label="Total Scanned" value={summary.total_scanned} sub="Rental log records" icon={BarChart3} />
            <MetricCard label="Anomalies Found" value={summary.anomaly_count} color="text-red-400" sub="Flagged by L1 or L2" icon={AlertTriangle} />
            <MetricCard label="Rule Violations" value={summary.rule_violation_count} color="text-orange-400" sub="Layer 1 engine flags" icon={Shield} />
            <MetricCard label="SVM Outliers" value={summary.svm_outlier_count} color="text-purple-400" sub="Layer 2 behavioral flags" icon={Cpu} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Severity breakdown bar */}
            <SeverityBar breakdown={breakdown} total={summary.total_scanned} />

            {/* Model config card */}
            <div className="bg-cat-card p-5 rounded-2xl border border-cat-border space-y-3">
              <h3 className="text-xs font-bold text-cat-subtext uppercase tracking-wider">Detection Configuration</h3>
              {svmConfig && (
                <div className="text-[11px] space-y-2">
                  <div className="flex justify-between border-b border-cat-border/40 pb-1.5">
                    <span className="text-cat-subtext">SVM Kernel</span>
                    <span className="text-purple-400 font-mono font-bold">{svmConfig.kernel.toUpperCase()}</span>
                  </div>
                  <div className="flex justify-between border-b border-cat-border/40 pb-1.5">
                    <span className="text-cat-subtext">Contamination (ν)</span>
                    <span className="text-white font-mono font-bold">{svmConfig.nu}</span>
                  </div>
                  <div className="flex justify-between border-b border-cat-border/40 pb-1.5">
                    <span className="text-cat-subtext">Training Samples</span>
                    <span className="text-white font-mono font-bold">{svmConfig.training_samples}</span>
                  </div>
                  <div className="flex justify-between border-b border-cat-border/40 pb-1.5">
                    <span className="text-cat-subtext">SVM Features</span>
                    <span className="text-white font-mono font-bold text-[10px]">{(svmConfig.features || []).join(', ')}</span>
                  </div>
                  {ierThreshold != null && (
                    <div className="flex justify-between border-b border-cat-border/40 pb-1.5">
                      <span className="text-cat-subtext">IER Violation Threshold</span>
                      <span className="text-red-400 font-mono font-bold">≥ {ierThreshold}%</span>
                    </div>
                  )}
                  {layer1Rules.map((rule, i) => (
                    <div key={i} className="text-[10px] text-cat-subtext py-0.5">
                      <span className="text-purple-300">✦</span> {rule}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Filter / Search bar */}
          <div className="bg-cat-card p-4 rounded-xl border border-cat-border flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
            <div className="flex flex-wrap items-center gap-3">
              {/* Severity filter */}
              <div className="flex items-center gap-2">
                <Filter className="w-3.5 h-3.5 text-cat-subtext" />
                <span className="text-[10px] text-cat-subtext uppercase font-bold">Severity:</span>
                <div className="flex bg-cat-steel p-0.5 rounded-lg border border-cat-border/60">
                  {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(s => (
                    <button
                      key={s}
                      onClick={() => {
                        setSeverityFilter(s);
                        if (s !== 'ALL') {
                          setShowClean(false);
                        }
                      }}
                      className={`px-2.5 py-1 text-xs font-bold rounded-md transition-all ${
                        severityFilter === s
                          ? 'bg-cat-yellow text-black font-black shadow'
                          : 'text-cat-subtext hover:text-white'
                      }`}
                    >
                      {s === 'ALL' ? 'All' : s}
                    </button>
                  ))}
                </div>
              </div>
 
              {/* Layer filter */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-cat-subtext uppercase font-bold">Layer:</span>
                <div className="flex bg-cat-steel p-0.5 rounded-lg border border-cat-border/60">
                  {[['ALL', 'All'], ['LAYER1', 'L1 Rules'], ['LAYER2', 'L2 SVM'], ['BOTH', 'Both']].map(([val, lbl]) => (
                    <button
                      key={val}
                      onClick={() => setLayerFilter(val)}
                      className={`px-2.5 py-1 text-xs font-bold rounded-md transition-all ${
                        layerFilter === val
                          ? 'bg-cat-yellow text-black font-black shadow'
                          : 'text-cat-subtext hover:text-white'
                      }`}
                    >
                      {lbl}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Search */}
            <div className="relative w-full md:w-72">
              <Search className="w-4 h-4 text-cat-subtext absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search equipment, site, operator..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="bg-cat-steel border border-cat-border text-white text-xs pl-9 pr-4 py-2.5 rounded-xl w-full focus:border-purple-400 outline-none transition-all placeholder:text-cat-subtext font-medium"
              />
              {search && (
                <button onClick={() => setSearch('')} className="absolute right-3 top-2.5 text-xs text-cat-subtext hover:text-white">
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Results count */}
          <div className="flex items-center justify-between text-xs text-cat-subtext px-1">
            <span>Showing <span className="text-white font-bold">{filteredRecords.length}</span> record{filteredRecords.length !== 1 ? 's' : ''}</span>
            <span>Scanned {summary.total_scanned} rental logs</span>
          </div>

          {/* Anomaly cards list */}
          <div className="space-y-3">
            {filteredRecords.length === 0 ? (
              <div className="bg-cat-card/50 p-12 rounded-2xl border border-cat-border text-center space-y-3">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
                <h3 className="text-white font-bold">No records match the selected filters</h3>
                <p className="text-xs text-cat-subtext">Try adjusting the severity or layer filters.</p>
              </div>
            ) : (
              filteredRecords.map(record => (
                <AnomalyCard key={record.rental_id} record={record} />
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
