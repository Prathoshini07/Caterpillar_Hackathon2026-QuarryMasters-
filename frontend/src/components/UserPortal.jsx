import React, { useState } from 'react';
import {
  X, LogIn, LogOut, CheckCircle2, AlertTriangle, Loader2,
  Truck, ClipboardList, Calendar, Hash, User, Clock, Zap,
  MapPin, Fuel, BarChart3, TrendingDown, Copy, Check, Sparkles,
  RefreshCw
} from 'lucide-react';
import { useSmolLM2 } from '../hooks/useSmolLM2';

const EQUIPMENT_TYPES = ['Excavator', 'Crane', 'Bulldozer', 'Grader'];
const today = new Date().toISOString().split('T')[0];

const inputCls =
  'w-full bg-[#1a1f2e] border border-[#2a3045] rounded-lg px-3 py-2.5 text-sm text-white ' +
  'placeholder-slate-500 focus:outline-none focus:border-yellow-400/60 focus:ring-1 ' +
  'focus:ring-yellow-400/30 transition-all';

const selectCls =
  'w-full bg-[#1a1f2e] border border-[#2a3045] rounded-lg px-3 py-2.5 text-sm text-white ' +
  'focus:outline-none focus:border-yellow-400/60 focus:ring-1 focus:ring-yellow-400/30 ' +
  'transition-all appearance-none cursor-pointer';

function FieldRow({ label, icon: Icon, children, span }) {
  return (
    <div className={span ? 'col-span-2' : ''}>
      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
        {Icon && <Icon className="w-3.5 h-3.5 text-yellow-400" />}
        {label}
      </label>
      {children}
    </div>
  );
}

function SummaryRow({ label, value, highlight, accent }) {
  const valColor = highlight
    ? 'text-yellow-400 font-bold'
    : accent === 'red'
    ? 'text-red-400 font-semibold'
    : accent === 'amber'
    ? 'text-amber-400 font-semibold'
    : accent === 'emerald'
    ? 'text-emerald-400 font-semibold'
    : 'text-slate-200';
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-[#2a3045] last:border-0">
      <span className="text-xs text-slate-500 uppercase tracking-wider font-medium">{label}</span>
      <span className={`text-sm font-mono ${valColor}`}>{value}</span>
    </div>
  );
}

// ── SmolLM2 AI Insight Card ──────────────────────────────────────────────────
function SmolLM2InsightCard({ prompt }) {
  const { generate, summary, loading, modelLoading, error } = useSmolLM2();
  const [triggered, setTriggered] = useState(false);

  const handleGenerate = () => {
    setTriggered(true);
    generate(prompt);
  };

  const statusText = modelLoading
    ? 'Downloading SmolLM2 model… (first time only)'
    : loading
    ? 'Generating AI summary…'
    : '';

  return (
    <div className="rounded-xl border border-violet-500/30 bg-violet-500/5 p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-violet-500/20 border border-violet-500/30 flex items-center justify-center">
            <Sparkles className="w-3.5 h-3.5 text-violet-400" />
          </div>
          <div>
            <p className="text-xs font-bold text-violet-300 uppercase tracking-wider">AI Insight</p>
            <p className="text-[10px] text-slate-500">Powered by SmolLM2 · runs in your browser</p>
          </div>
        </div>
        {triggered && !loading && !modelLoading && (
          <button
            onClick={handleGenerate}
            title="Regenerate"
            className="w-6 h-6 rounded-md bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400 hover:bg-violet-500/20 transition-all"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Body */}
      {!triggered ? (
        <button
          onClick={handleGenerate}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-violet-500/10 border border-violet-500/30 text-violet-300 text-xs font-semibold hover:bg-violet-500/20 transition-all"
        >
          <Sparkles className="w-3.5 h-3.5" />
          Generate AI Summary
        </button>
      ) : (loading || modelLoading) ? (
        <div className="flex items-center gap-3 py-2">
          <Loader2 className="w-4 h-4 animate-spin text-violet-400 shrink-0" />
          <p className="text-xs text-violet-300/70 italic">{statusText}</p>
        </div>
      ) : error ? (
        <div className="flex items-start gap-2 text-xs text-red-400">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : summary ? (
        <p className="text-sm text-slate-200 leading-relaxed">{summary}</p>
      ) : null}
    </div>
  );
}

// ── Copyable Rental ID badge ──────────────────────────────────────────────────
function RentalIdBadge({ rentalId }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(rentalId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="w-full flex items-center justify-between bg-yellow-400/10 border border-yellow-400/40
        rounded-xl px-4 py-3 hover:bg-yellow-400/15 transition-all group"
    >
      <div className="text-left">
        <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-0.5">Rental ID — Save this for Check-Out</p>
        <p className="text-xl font-black font-mono text-yellow-400">{rentalId}</p>
      </div>
      <div className="w-8 h-8 rounded-lg bg-yellow-400/20 flex items-center justify-center text-yellow-400 group-hover:bg-yellow-400/30 transition-all">
        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
      </div>
    </button>
  );
}

// ─── Check-In Form ─────────────────────────────────────────────────────────────
function CheckInForm() {
  const [form, setForm] = useState({
    equipment_id: '',
    equipment_type: 'Excavator',
    site_id: '',
    location: '',
    check_in_date: today,
    expected_rental_days: '',
    operator_id: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const handleChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setResult(null);
    if (!form.expected_rental_days || parseInt(form.expected_rental_days) <= 0) {
      setError('Expected rental days must be a positive number.'); return;
    }
    setLoading(true);
    try {
      const res = await fetch('/api/portal/checkin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          equipment_id: form.equipment_id.trim().toUpperCase(),
          equipment_type: form.equipment_type,
          site_id: form.site_id.trim().toUpperCase(),
          location: form.location.trim(),
          check_in_date: form.check_in_date,
          expected_rental_days: parseInt(form.expected_rental_days),
          operator_id: form.operator_id.trim().toUpperCase(),
        }),
      });
      const data = await res.json();
      if (!res.ok) setError(data.detail || 'An unexpected error occurred.');
      else setResult(data);
    } catch {
      setError('Network error: Could not reach the backend server.');
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <div className="space-y-4">
        <div className="flex flex-col items-center text-center py-4">
          <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mb-3">
            <CheckCircle2 className="w-7 h-7 text-emerald-400" />
          </div>
          <h3 className="text-base font-bold text-white">Check-In Successful!</h3>
          <p className="text-xs text-slate-400 mt-1">Equipment is now marked as RENTED.</p>
        </div>

        <RentalIdBadge rentalId={result.rental_id} />

        <div className="bg-[#1a1f2e] border border-[#2a3045] rounded-xl p-4 space-y-0">
          <SummaryRow label="Equipment" value={`${result.equipment_id} (${result.equipment_type})`} />
          <SummaryRow label="Site" value={`${result.site_id} — ${result.site_name}`} />
          <SummaryRow label="Location" value={result.location} />
          <SummaryRow label="Operator" value={`${result.operator_id} — ${result.operator_name}`} />
          <SummaryRow label="Check-In Date" value={result.check_in_date} />
          <SummaryRow label="Expected Return" value={result.expected_checkout_date} accent="amber" />
          <SummaryRow label="Rental Days" value={`${result.expected_rental_days} days`} />
        </div>

        <SmolLM2InsightCard prompt={
          `Check-In Summary:\n` +
          `Equipment: ${result.equipment_id} (${result.equipment_type})\n` +
          `Site: ${result.site_name} (${result.site_id}), Location: ${result.location}\n` +
          `Operator: ${result.operator_name} (${result.operator_id})\n` +
          `Check-In Date: ${result.check_in_date}\n` +
          `Expected Return: ${result.expected_checkout_date}\n` +
          `Expected Rental Duration: ${result.expected_rental_days} days\n` +
          `Rental ID: ${result.rental_id}`
        } />

        <button
          onClick={() => { setResult(null); setError(''); setForm({ equipment_id:'',equipment_type:'Excavator',site_id:'',location:'',check_in_date:today,expected_rental_days:'',operator_id:'' }); }}
          className="w-full bg-yellow-400 hover:bg-yellow-300 text-black font-bold py-2.5 rounded-xl text-sm transition-all"
        >
          Check-In Another Equipment
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-sm text-red-300">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-red-400" />
          <span>{error}</span>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3">
        <FieldRow label="Equipment ID" icon={Hash}>
          <input name="equipment_id" value={form.equipment_id} onChange={handleChange} required placeholder="e.g. EQX1001" className={inputCls} />
        </FieldRow>
        <FieldRow label="Equipment Type" icon={Truck}>
          <div className="relative">
            <select name="equipment_type" value={form.equipment_type} onChange={handleChange} required className={selectCls}>
              {EQUIPMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs">▾</div>
          </div>
        </FieldRow>
        <FieldRow label="Site ID" icon={ClipboardList}>
          <input name="site_id" value={form.site_id} onChange={handleChange} required placeholder="e.g. S001" className={inputCls} />
        </FieldRow>
        <FieldRow label="Operator ID" icon={User}>
          <input name="operator_id" value={form.operator_id} onChange={handleChange} required placeholder="e.g. OP001" className={inputCls} />
        </FieldRow>
        <FieldRow label="Location" icon={MapPin} span>
          <input name="location" value={form.location} onChange={handleChange} required placeholder="e.g. Quarry Zone A, Block 3" className={inputCls} />
        </FieldRow>
        <FieldRow label="Check-In Date" icon={Calendar}>
          <input type="date" name="check_in_date" value={form.check_in_date} onChange={handleChange} required className={inputCls + ' [color-scheme:dark]'} />
        </FieldRow>
        <FieldRow label="Expected Rental Days" icon={Clock}>
          <input type="number" name="expected_rental_days" value={form.expected_rental_days} onChange={handleChange} required min="1" placeholder="e.g. 30" className={inputCls} />
        </FieldRow>
      </div>
      <button type="submit" disabled={loading}
        className="w-full bg-yellow-400 hover:bg-yellow-300 disabled:opacity-60 disabled:cursor-not-allowed text-black font-bold py-3 rounded-xl flex items-center justify-center gap-2 text-sm transition-all shadow-lg shadow-yellow-400/20">
        {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Processing…</> : <><LogIn className="w-4 h-4" /> Confirm Check-In</>}
      </button>
    </form>
  );
}

// ─── Check-Out Form ─────────────────────────────────────────────────────────────
function CheckOutForm() {
  const [form, setForm] = useState({
    rental_id: '',
    checkout_date: today,
    total_engine_hours: '',
    total_idle_hours: '',
    fuel_usage_liters: '',
    operator_id: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const handleChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const eng = parseFloat(form.total_engine_hours);
  const idle = parseFloat(form.total_idle_hours);
  const idleExceedsEngine = !isNaN(eng) && !isNaN(idle) && idle > eng;
  const idleRatio = (!isNaN(eng) && !isNaN(idle) && eng > 0 && idle <= eng)
    ? ((idle / eng) * 100).toFixed(1) : null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setResult(null);
    if (isNaN(eng) || eng <= 0) { setError('Total engine hours must be a positive number.'); return; }
    if (isNaN(idle) || idle < 0) { setError('Total idle hours cannot be negative.'); return; }
    if (idleExceedsEngine) { setError('Total idle hours cannot exceed total engine hours.'); return; }
    const fuel = parseFloat(form.fuel_usage_liters);
    if (isNaN(fuel) || fuel < 0) { setError('Fuel usage must be 0 or greater.'); return; }

    setLoading(true);
    try {
      const res = await fetch('/api/portal/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rental_id: form.rental_id.trim().toUpperCase(),
          checkout_date: form.checkout_date,
          total_engine_hours: eng,
          total_idle_hours: idle,
          fuel_usage_liters: fuel,
          operator_id: form.operator_id.trim().toUpperCase(),
        }),
      });
      const data = await res.json();
      if (!res.ok) setError(data.detail || 'An unexpected error occurred.');
      else setResult(data);
    } catch {
      setError('Network error: Could not reach the backend server.');
    } finally {
      setLoading(false);
    }
  };

  const anomalyStyle = {
    HIGH_IDLE: 'text-red-400 bg-red-500/10 border-red-500/30',
    UNDERUTILIZED: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
    OPTIMAL: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  };

  if (result) {
    const flag = result.anomaly_flag || 'OPTIMAL';
    const downAccent = result.downtime_per_day_hrs > 8 ? 'red' : result.downtime_per_day_hrs > 4 ? 'amber' : 'emerald';
    const idleAccent = result.idle_ratio_pct > 75 ? 'red' : result.idle_ratio_pct > 50 ? 'amber' : 'emerald';
    return (
      <div className="space-y-4">
        <div className="flex flex-col items-center text-center py-3">
          <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mb-3">
            <CheckCircle2 className="w-7 h-7 text-emerald-400" />
          </div>
          <h3 className="text-base font-bold text-white">Check-Out Complete!</h3>
          <p className="text-xs text-slate-400 mt-1">Equipment is now marked as AVAILABLE.</p>
        </div>

        {/* Anomaly Flag */}
        <div className={`flex items-center justify-between px-4 py-2.5 rounded-xl border ${anomalyStyle[flag]}`}>
          <span className="text-xs font-semibold uppercase tracking-wider">Anomaly Status</span>
          <span className="text-sm font-bold">{flag}</span>
        </div>

        {/* Rental Identity */}
        <div className="bg-[#1a1f2e] border border-[#2a3045] rounded-xl p-4 space-y-0">
          <p className="text-[10px] text-yellow-400/70 uppercase tracking-widest font-bold mb-2">Rental Info</p>
          <SummaryRow label="Rental ID" value={result.rental_id} highlight />
          <SummaryRow label="Equipment" value={`${result.equipment_id} (${result.equipment_type})`} />
          <SummaryRow label="Site" value={`${result.site_id} — ${result.site_name}`} />
          <SummaryRow label="Location" value={result.location || 'N/A'} />
          <SummaryRow label="Operator" value={result.operator_name} />
          <SummaryRow label="Check-In" value={result.check_in_date} />
          <SummaryRow label="Check-Out" value={result.check_out_date} />
          <SummaryRow label="Total Days" value={`${result.actual_rental_days} days`} accent={result.is_overdue ? 'red' : 'emerald'} />
          {result.is_overdue && <SummaryRow label="Status" value="⚠ OVERDUE" accent="red" />}
        </div>

        {/* Usage Analytics — Totals entered + derived averages */}
        <div className="bg-[#1a1f2e] border border-[#2a3045] rounded-xl p-4 space-y-0">
          <p className="text-[10px] text-yellow-400/70 uppercase tracking-widest font-bold mb-2">Usage Analytics</p>
          <SummaryRow label="Total Engine Hours" value={`${result.total_engine_hours} hrs`} accent="emerald" />
          <SummaryRow label="Total Idle Hours" value={`${result.total_idle_hours} hrs`} accent={idleAccent} />
          <SummaryRow label="Total Active (Productive) Hours" value={`${result.total_active_hours} hrs`} highlight />
          <SummaryRow label="Total Downtime Hours" value={`${result.total_downtime_hours} hrs`} accent={downAccent} />
          <div className="pt-2 mt-1 border-t border-[#2a3045]">
            <p className="text-[9px] text-slate-500 uppercase tracking-widest mb-1.5">Derived daily averages (total ÷ {result.actual_rental_days} days)</p>
            <SummaryRow label="Avg Engine Hrs / Day" value={`${result.engine_hrs_per_day_avg} hrs`} />
            <SummaryRow label="Avg Idle Hrs / Day" value={`${result.idle_hrs_per_day_avg} hrs`} />
            <SummaryRow label="Avg Downtime / Day" value={`${result.downtime_per_day_hrs} hrs`} />
          </div>
          <SummaryRow label="Idle Ratio" value={`${result.idle_ratio_pct}%`} accent={idleAccent} />
          <SummaryRow label="Utilization" value={`${result.utilization_pct}%`} accent={result.utilization_pct < 30 ? 'red' : 'emerald'} />
          <SummaryRow label="Fuel Used" value={`${result.fuel_usage_liters} L`} />
        </div>

        {/* Financial Penalty Invoice */}
        {result.penalty_invoice && (
          <div className={`bg-[#1a1f2e] border rounded-xl p-4 space-y-0 ${
            result.penalty_invoice.penalty_applied
              ? 'border-red-500/40'
              : 'border-emerald-500/30'
          }`}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] text-red-400/80 uppercase tracking-widest font-bold">
                🔥 Excess Idling Penalty Invoice
              </p>
              {result.penalty_invoice.penalty_applied ? (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30 font-semibold">CHARGE APPLIED</span>
              ) : (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-semibold">NO CHARGE</span>
              )}
            </div>
            <SummaryRow label="Total Idle Hours Logged" value={`${result.penalty_invoice.total_idle_hours} hrs`} />
            <SummaryRow label="Permissible Idle Threshold" value={`${result.penalty_invoice.permissible_idle_total_hrs} hrs (2.5h/day)`} accent="emerald" />
            <SummaryRow
              label="Excess Idle Hours"
              value={`${result.penalty_invoice.excess_idle_hours > 0 ? '+' : ''}${result.penalty_invoice.excess_idle_hours} hrs`}
              accent={result.penalty_invoice.excess_idle_hours > 0 ? 'red' : 'emerald'}
            />
            <SummaryRow label="Wasted Fuel (3.5 L/hr)" value={`${result.penalty_invoice.wasted_fuel_liters} L`} accent={result.penalty_invoice.wasted_fuel_liters > 0 ? 'amber' : 'emerald'} />
            <SummaryRow label="Fuel Penalty ($3.25/L)" value={`$${result.penalty_invoice.fuel_penalty_usd.toFixed(2)}`} accent={result.penalty_invoice.fuel_penalty_usd > 0 ? 'red' : 'emerald'} />
            <SummaryRow label="Idling Penalty ($60/hr)" value={`$${result.penalty_invoice.idle_penalty_usd.toFixed(2)}`} accent={result.penalty_invoice.idle_penalty_usd > 0 ? 'red' : 'emerald'} />
            <div className={`flex justify-between items-center pt-2 mt-1 border-t ${
              result.penalty_invoice.penalty_applied ? 'border-red-500/30' : 'border-emerald-500/20'
            }`}>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">⚠ Total Excess Idling Penalty</span>
              <span className={`text-base font-black font-mono ${
                result.penalty_invoice.penalty_applied ? 'text-red-400' : 'text-emerald-400'
              }`}>${result.penalty_invoice.total_penalty_usd.toFixed(2)}</span>
            </div>
          </div>
        )}

        {/* Engine-Hour Maintenance Health */}
        {result.maintenance_health && (
          <div className="bg-[#1a1f2e] border border-[#2a3045] rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-[10px] text-blue-400/80 uppercase tracking-widest font-bold">🔧 Engine-Hour Maintenance Health</p>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold border"
                style={{ color: result.maintenance_health.maint_color, borderColor: result.maintenance_health.maint_color + '50', background: result.maintenance_health.maint_color + '15' }}>
                {result.maintenance_health.maint_status}
              </span>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-slate-400">Active Engine Hours toward next service</span>
                <span className="font-mono font-bold text-white">
                  {result.maintenance_health.hours_since_last_service} / {result.maintenance_health.service_interval_hrs} hrs
                </span>
              </div>
              <div className="w-full bg-[#0d1117] rounded-full h-3 overflow-hidden border border-[#2a3045]">
                <div
                  className="h-3 rounded-full transition-all duration-700"
                  style={{
                    width: `${Math.min(result.maintenance_health.service_life_pct, 100)}%`,
                    background: result.maintenance_health.maint_color,
                    boxShadow: `0 0 8px ${result.maintenance_health.maint_color}80`,
                  }}
                />
              </div>
              <div className="flex justify-between mt-1.5">
                <span className="text-[10px] text-slate-500">{result.maintenance_health.service_life_pct}% of interval elapsed</span>
                <span className="text-[10px]" style={{ color: result.maintenance_health.maint_color }}>
                  {result.maintenance_health.hours_until_service} hrs until service
                </span>
              </div>
            </div>
            <SummaryRow label="Cumulative Active Hours" value={`${result.maintenance_health.cumulative_active_hours} hrs`} />
          </div>
        )}

        <SmolLM2InsightCard prompt={
          `Check-Out Summary:\n` +
          `Equipment: ${result.equipment_id} (${result.equipment_type})\n` +
          `Site: ${result.site_name} (${result.site_id}), Location: ${result.location || 'N/A'}\n` +
          `Operator: ${result.operator_name}\n` +
          `Check-In: ${result.check_in_date} → Check-Out: ${result.check_out_date}\n` +
          `Actual Rental Days: ${result.actual_rental_days} days${result.is_overdue ? ' (OVERDUE)' : ''}\n` +
          `Engine Hrs/Day: ${result.engine_hrs_per_day} hrs, Idle Hrs/Day: ${result.idle_hrs_per_day} hrs\n` +
          `Idle Ratio: ${result.idle_ratio_pct}%, Utilization: ${result.utilization_pct}%\n` +
          `Total Engine Hours: ${result.total_engine_hours} hrs\n` +
          `Total Idle Hours: ${result.total_idle_hours} hrs\n` +
          `Total Runtime (Productive): ${result.total_runtime_hours} hrs\n` +
          `Total Downtime: ${result.total_downtime_hours} hrs\n` +
          `Fuel Used: ${result.fuel_usage_liters} L\n` +
          `Anomaly Status: ${result.anomaly_flag}\n` +
          (result.penalty_invoice?.penalty_applied
            ? `⚠ EXCESS IDLING PENALTY: $${result.penalty_invoice.total_penalty_usd.toFixed(2)} (${result.penalty_invoice.excess_idle_hours} excess idle hrs → wasted ${result.penalty_invoice.wasted_fuel_liters}L fuel)\n`
            : `✓ No idling penalty — within 2.5h/day threshold\n`) +
          `Maintenance Health: ${result.maintenance_health?.maint_status} (${result.maintenance_health?.hours_until_service} hrs until next service)`
        } />

        <button
          onClick={() => { setResult(null); setError(''); setForm({ rental_id:'',checkout_date:today,total_engine_hours:'',total_idle_hours:'',fuel_usage_liters:'',operator_id:'' }); }}
          className="w-full bg-yellow-400 hover:bg-yellow-300 text-black font-bold py-2.5 rounded-xl text-sm transition-all"
        >
          Check-Out Another Equipment
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Rental ID — prominent top field */}
      <div className="bg-yellow-400/5 border border-yellow-400/20 rounded-xl p-4">
        <label className="block text-xs font-bold text-yellow-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <Hash className="w-3.5 h-3.5" /> Rental ID <span className="text-slate-500 font-normal normal-case">(from your Check-In receipt)</span>
        </label>
        <input
          name="rental_id"
          value={form.rental_id}
          onChange={handleChange}
          required
          placeholder="e.g. RL-A1B2C3D4"
          className={inputCls + ' font-mono text-yellow-400 placeholder-yellow-400/30'}
        />
      </div>

      {error && (
        <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-sm text-red-300">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <FieldRow label="Operator ID" icon={User}>
          <input name="operator_id" value={form.operator_id} onChange={handleChange} required placeholder="e.g. OP001" className={inputCls} />
        </FieldRow>
        <FieldRow label="Check-Out Date" icon={Calendar}>
          <input type="date" name="checkout_date" value={form.checkout_date} onChange={handleChange} required className={inputCls + ' [color-scheme:dark]'} />
        </FieldRow>
        <FieldRow label="Total Engine Hours (entire rental)" icon={Zap}>
          <input type="number" step="0.1" name="total_engine_hours" value={form.total_engine_hours} onChange={handleChange} required min="0.1" placeholder="e.g. 210" className={inputCls} />
        </FieldRow>
        <FieldRow label="Total Idle Hours (entire rental)" icon={Clock}>
          <input type="number" step="0.1" name="total_idle_hours" value={form.total_idle_hours} onChange={handleChange} required min="0" placeholder="e.g. 35"
            className={inputCls + (idleExceedsEngine ? ' border-red-500/60' : '')} />
        </FieldRow>
        <FieldRow label="Fuel Usage (Liters)" icon={Fuel} span>
          <input type="number" step="0.1" name="fuel_usage_liters" value={form.fuel_usage_liters} onChange={handleChange} required min="0" placeholder="e.g. 450.5" className={inputCls} />
        </FieldRow>
      </div>

      {/* Live idle validation / preview */}
      {form.total_engine_hours && form.total_idle_hours && eng > 0 && (
        idleExceedsEngine ? (
          <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-sm text-red-300">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-red-400" />
            <span><strong>Invalid:</strong> Total Idle Hrs ({form.total_idle_hours}h) cannot exceed Total Engine Hrs ({form.total_engine_hours}h). Idle time is a subset of engine-on time.</span>
          </div>
        ) : (
          <div className="text-xs bg-[#1a1f2e] border border-[#2a3045] rounded-lg px-3 py-2 flex items-center justify-between">
            <span className="text-slate-500">Idle Ratio Preview ({form.total_idle_hours}h ÷ {form.total_engine_hours}h)</span>
            <span className={idleRatio > 75 ? 'text-red-400 font-bold' : idleRatio > 50 ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'}>
              {idleRatio}% — {idleRatio > 75 ? '⚠ HIGH_IDLE' : idleRatio > 50 ? '⚠ UNDERUTILIZED' : '✓ OPTIMAL'}
            </span>
          </div>
        )
      )}

      <button type="submit" disabled={loading || idleExceedsEngine}
        className="w-full bg-yellow-400 hover:bg-yellow-300 disabled:opacity-60 disabled:cursor-not-allowed text-black font-bold py-3 rounded-xl flex items-center justify-center gap-2 text-sm transition-all shadow-lg shadow-yellow-400/20">
        {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Processing…</> : <><LogOut className="w-4 h-4" /> Confirm Check-Out</>}
      </button>
    </form>
  );
}

// ─── Main Modal ───────────────────────────────────────────────────────────────
export default function UserPortal({ onClose }) {
  const [activeTab, setActiveTab] = useState('checkin');

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.78)', backdropFilter: 'blur(6px)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>

      <div className="relative w-full max-w-xl rounded-2xl border border-yellow-400/20 shadow-2xl overflow-hidden"
        style={{ background: 'linear-gradient(145deg,#111827 0%,#0f1420 100%)', boxShadow: '0 0 60px rgba(250,204,21,0.07),0 25px 50px rgba(0,0,0,0.6)' }}>

        {/* Top glow line */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-px rounded-full bg-gradient-to-r from-transparent via-yellow-400/60 to-transparent" />

        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-[#2a3045]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-yellow-400/10 border border-yellow-400/20 flex items-center justify-center">
              <Truck className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">User Portal</h2>
              <p className="text-xs text-slate-500">Equipment Check-In / Check-Out</p>
            </div>
          </div>
          <button onClick={onClose}
            className="w-8 h-8 rounded-lg bg-[#1a1f2e] border border-[#2a3045] flex items-center justify-center text-slate-400 hover:text-white hover:border-yellow-400/40 transition-all">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex px-6 pt-4 gap-2">
          {[['checkin', LogIn, 'Check-In'], ['checkout', LogOut, 'Check-Out']].map(([id, Icon, label]) => (
            <button key={id} onClick={() => setActiveTab(id)}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                activeTab === id
                  ? 'bg-yellow-400/10 border border-yellow-400/30 text-yellow-400'
                  : 'text-slate-500 hover:text-slate-300 border border-transparent'
              }`}>
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Form Body */}
        <div className="px-6 py-5 max-h-[72vh] overflow-y-auto">
          {activeTab === 'checkin' ? <CheckInForm /> : <CheckOutForm />}
        </div>

        <div className="px-6 pb-4 text-center">
          <p className="text-xs text-slate-600">All data is written directly to the rental_logs table.</p>
        </div>
      </div>
    </div>
  );
}
