import React, { useState, useEffect } from 'react';
import { 
  Coins, Fuel, AlertTriangle, ShieldAlert, CheckCircle2, 
  Search, RefreshCw, BarChart3, Calendar, Clock, DollarSign, 
  Wrench, Settings, ArrowDownToLine, ArrowRight
} from 'lucide-react';

export default function OptimizationPortal() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('penalties'); // 'penalties' or 'maintenance'
  const [searchQuery, setSearchQuery] = useState('');
  const [scheduledServices, setScheduledServices] = useState({}); // Tracking dispatched services

  const fetchOptimizationData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/optimization/data');
      if (!res.ok) throw new Error(`Failed to fetch optimization data: ${res.status}`);
      const result = await res.json();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOptimizationData();
  }, []);

  const handleDispatchService = (equipmentId) => {
    setScheduledServices(prev => ({
      ...prev,
      [equipmentId]: {
        dispatched: true,
        timestamp: new Date().toLocaleTimeString()
      }
    }));
  };

  if (loading) {
    return (
      <div className="min-h-[400px] flex items-center justify-center p-6 text-left">
        <div className="text-center space-y-4">
          <RefreshCw className="w-10 h-10 animate-spin text-cat-yellow mx-auto" />
          <p className="text-sm text-cat-subtext">Calculating cost optimization parameters & asset maintenance metrics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 p-5 rounded-2xl text-red-400 text-sm flex items-center gap-3 text-left">
        <AlertTriangle className="w-5 h-5 shrink-0" />
        <span>Error loading optimization data: {error}</span>
      </div>
    );
  }

  const { summary, rates, penalties, maintenance_schedules } = data;

  // Search logic
  const filteredPenalties = penalties.filter(p => {
    const q = searchQuery.toLowerCase();
    return p.equipment_id.toLowerCase().includes(q) || 
           p.site_name.toLowerCase().includes(q) || 
           p.operator_name.toLowerCase().includes(q);
  });

  const filteredMaintenance = maintenance_schedules.filter(m => {
    const q = searchQuery.toLowerCase();
    return m.equipment_id.toLowerCase().includes(q) || 
           m.site_name.toLowerCase().includes(q);
  });

  return (
    <div className="space-y-6 text-left">
      {/* Brand Header */}
      <div className="bg-cat-card p-6 rounded-2xl border border-cat-border/80 flex flex-col md:flex-row gap-5 justify-between items-start md:items-center">
        <div className="flex items-start gap-3">
          <div className="bg-cat-yellow/20 p-3 rounded-xl text-cat-yellow shrink-0">
            <Coins className="w-7 h-7" />
          </div>
          <div>
            <h2 className="text-xl font-black text-white tracking-tight">FINANCIAL & FLEET OPTIMIZATION</h2>
            <p className="text-xs text-cat-subtext mt-1 leading-relaxed max-w-2xl">
              Maximize profit and minimize operating overheads by imposing an <span className="text-white font-semibold">Excess Idling Cost Penalty</span> on site managers and scheduling <span className="text-white font-semibold">Preventative Servicing</span> strictly based on active work runtime (engine hours) rather than calendar days.
            </p>
          </div>
        </div>

        <button
          onClick={fetchOptimizationData}
          className="shrink-0 flex items-center gap-2 px-4 py-2.5 bg-cat-steel border border-cat-border hover:border-cat-yellow text-white text-xs font-bold rounded-xl transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Recalculate Metrics
        </button>
      </div>

      {/* Sub-Tab Selectors */}
      <div className="flex border-b border-cat-border">
        <button
          onClick={() => { setActiveSubTab('penalties'); setSearchQuery(''); }}
          className={`px-5 py-3 text-xs font-black uppercase tracking-wider border-b-2 transition-all ${
            activeSubTab === 'penalties'
              ? 'border-cat-yellow text-cat-yellow'
              : 'border-transparent text-cat-subtext hover:text-white'
          }`}
        >
          1. Fuel & Idle Cost Penalties
        </button>
        <button
          onClick={() => { setActiveSubTab('maintenance'); setSearchQuery(''); }}
          className={`px-5 py-3 text-xs font-black uppercase tracking-wider border-b-2 transition-all ${
            activeSubTab === 'maintenance'
              ? 'border-cat-yellow text-cat-yellow'
              : 'border-transparent text-cat-subtext hover:text-white'
          }`}
        >
          2. Active-Work Maintenance Scheduler
        </button>
      </div>

      {/* ── SUB-TAB 1: FUEL & IDLE COST PENALTIES ───────────────────────────── */}
      {activeSubTab === 'penalties' && (
        <div className="space-y-6">
          {/* Metrics Row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="bg-cat-card p-5 rounded-2xl border border-cat-border space-y-1">
              <span className="text-[10px] text-cat-subtext uppercase font-bold tracking-wider flex items-center gap-1.5">
                <DollarSign className="w-3.5 h-3.5 text-red-400" />
                Excess Idle Penalties Levied
              </span>
              <div className="text-3xl font-black text-red-400 font-mono mt-1">
                ${summary.total_excess_idle_penalties_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <p className="text-[11px] text-cat-subtext">
                Charged at ${rates.hourly_idle_penalty_rate}/hr exceeding standard {rates.idle_fuel_consumption_l_hr}h daily limit.
              </p>
            </div>

            <div className="bg-cat-card p-5 rounded-2xl border border-cat-border space-y-1">
              <span className="text-[10px] text-cat-subtext uppercase font-bold tracking-wider flex items-center gap-1.5">
                <Fuel className="w-3.5 h-3.5 text-orange-400" />
                Wasted Fuel Volume
              </span>
              <div className="text-3xl font-black text-white font-mono mt-1">
                {summary.total_wasted_fuel_liters.toLocaleString()} Liters
              </div>
              <p className="text-[11px] text-cat-subtext">
                Calculated at a rate of {rates.idle_fuel_consumption_l_hr} Liters/Hour of unproductive idling.
              </p>
            </div>

            <div className="bg-cat-card p-5 rounded-2xl border border-cat-border space-y-1">
              <span className="text-[10px] text-cat-subtext uppercase font-bold tracking-wider flex items-center gap-1.5">
                <Settings className="w-3.5 h-3.5 text-cat-yellow" />
                Active Penalty Rate Parameters
              </span>
              <div className="text-[11px] text-slate-300 space-y-1 mt-2.5">
                <div className="flex justify-between border-b border-cat-border/40 pb-1">
                  <span>Fuel Penalty / Liter</span>
                  <span className="text-white font-bold">${rates.fuel_cost_per_liter} / L</span>
                </div>
                <div className="flex justify-between">
                  <span>Standard Idle Threshold</span>
                  <span className="text-emerald-400 font-bold">≤ 2.5 Hrs / Day</span>
                </div>
              </div>
            </div>
          </div>

          {/* Search bar */}
          <div className="bg-cat-card p-4 rounded-xl border border-cat-border flex items-center justify-between">
            <div className="relative w-full md:w-80">
              <Search className="w-4 h-4 text-cat-subtext absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Filter by site, operator or equipment ID..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="bg-cat-steel border border-cat-border text-white text-xs pl-9 pr-4 py-2.5 rounded-xl w-full focus:border-cat-yellow outline-none transition-all font-medium placeholder:text-cat-subtext"
              />
            </div>
            <span className="text-xs text-cat-subtext">
              Showing <span className="text-white font-bold">{filteredPenalties.length}</span> invoices
            </span>
          </div>

          {/* Penalty Invoice Grid */}
          <div className="space-y-4">
            {filteredPenalties.length === 0 ? (
              <div className="bg-cat-card/50 p-12 rounded-2xl border border-cat-border text-center space-y-2">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
                <h3 className="text-white font-bold">No Excess Idling Penalties</h3>
                <p className="text-xs text-cat-subtext">All active rentals are currently running under the 2.5-hour daily idle limits.</p>
              </div>
            ) : (
              filteredPenalties.map((invoice, idx) => (
                <div 
                  key={invoice.rental_id}
                  className="bg-cat-card border border-red-500/20 hover:border-red-500/40 rounded-2xl p-5 transition-all duration-300 relative overflow-hidden"
                >
                  {/* Left severity tag */}
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500" />
                  
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    {/* Equipment and site headers */}
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] font-black px-2 py-0.5 bg-red-500/10 border border-red-500/30 text-red-400 rounded tracking-wider">
                          #{idx + 1} EXCESS IDLE PENALTY INVOICE
                        </span>
                        <span className="text-xs font-mono text-cat-subtext">
                          Rental Ref: {invoice.rental_id}
                        </span>
                      </div>
                      <h4 className="text-white font-black text-sm md:text-base">
                        {invoice.equipment_id} <span className="text-cat-subtext font-normal">({invoice.equipment_type})</span> — {invoice.site_name}
                      </h4>
                      <p className="text-xs text-slate-300">
                        Assigned Operator: <strong className="text-white">{invoice.operator_name}</strong>
                      </p>
                    </div>

                    {/* Total Penalty Levy */}
                    <div className="bg-red-500/10 border border-red-500/20 px-5 py-3 rounded-xl text-right shrink-0">
                      <span className="text-[9px] text-red-400 font-bold block uppercase tracking-wider">Total Fine Charge</span>
                      <span className="text-xl font-mono text-red-400 font-black">
                        ${invoice.total_penalty_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </div>
                  </div>

                  {/* Operational breakdown grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-cat-dark p-3.5 rounded-xl border border-cat-border/60 text-[11px] mt-4">
                    <div>
                      <span className="text-cat-subtext block uppercase tracking-wider text-[9px]">Idle Hours logged</span>
                      <span className="font-semibold text-slate-200">{invoice.idle_hours_per_day}h/day ({invoice.total_idle_hours}h total)</span>
                    </div>
                    <div>
                      <span className="text-cat-subtext block uppercase tracking-wider text-[9px]">Excess Idle Hours</span>
                      <span className="font-semibold text-red-400">+{invoice.excess_idle_hours} hrs</span>
                    </div>
                    <div>
                      <span className="text-cat-subtext block uppercase tracking-wider text-[9px]">Wasted Fuel Volume</span>
                      <span className="font-semibold text-slate-200 font-mono">{invoice.wasted_fuel_liters} Liters</span>
                    </div>
                    <div>
                      <span className="text-cat-subtext block uppercase tracking-wider text-[9px]">Wasted Fuel Cost Fine</span>
                      <span className="font-semibold text-slate-200 font-mono">${invoice.fuel_penalty_usd}</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ── SUB-TAB 2: PREVENTATIVE MAINTENANCE SCHEDULER ───────────────────── */}
      {activeSubTab === 'maintenance' && (
        <div className="space-y-6">
          {/* Metrics Row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="bg-cat-card p-5 rounded-2xl border border-cat-border space-y-1">
              <span className="text-[10px] text-cat-subtext uppercase font-bold tracking-wider flex items-center gap-1.5">
                <Wrench className="w-3.5 h-3.5 text-emerald-400" />
                Active Work Cost Optimization
              </span>
              <div className="text-3xl font-black text-emerald-400 font-mono mt-1">
                ${summary.maintenance_engine_cost_usd.toLocaleString()}
              </div>
              <p className="text-[11px] text-cat-subtext">
                Actual maintenance budget spent strictly based on Engine Hours ({rates.engine_service_interval_hrs}h active work).
              </p>
            </div>

            <div className="bg-cat-card p-5 rounded-2xl border border-cat-border space-y-1">
              <span className="text-[10px] text-cat-subtext uppercase font-bold tracking-wider flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-cat-subtext" />
                Calendar-Based Maintenance Cost
              </span>
              <div className="text-3xl font-black text-slate-400 font-mono mt-1">
                ${summary.maintenance_calendar_cost_usd.toLocaleString()}
              </div>
              <p className="text-[11px] text-cat-subtext">
                Traditional service cost scheduled strictly every {rates.calendar_service_interval_days} elapsed calendar days.
              </p>
            </div>

            <div className="bg-cat-card p-5 rounded-2xl border border-cat-border space-y-1 bg-emerald-500/5 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl" />
              <span className="text-[10px] text-emerald-400 uppercase font-black tracking-wider flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Budget Capital Saved
              </span>
              <div className="text-3xl font-black text-emerald-400 font-mono mt-1">
                +${summary.net_maintenance_savings_usd.toLocaleString()}
              </div>
              <p className="text-[11px] text-emerald-400/80">
                Wasted calendar services avoided on idling machines with low active earth-moving runtime!
              </p>
            </div>
          </div>

          {/* Search bar */}
          <div className="bg-cat-card p-4 rounded-xl border border-cat-border flex items-center justify-between">
            <div className="relative w-full md:w-80">
              <Search className="w-4 h-4 text-cat-subtext absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Filter by site or equipment ID..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="bg-cat-steel border border-cat-border text-white text-xs pl-9 pr-4 py-2.5 rounded-xl w-full focus:border-cat-yellow outline-none transition-all font-medium placeholder:text-cat-subtext"
              />
            </div>
            <span className="text-xs text-cat-subtext">
              Showing <span className="text-white font-bold">{filteredMaintenance.length}</span> fleet schedules
            </span>
          </div>

          {/* Maintenance Scheduler Grid */}
          <div className="space-y-4">
            {filteredMaintenance.map((maint, idx) => {
              const isUrgent = maint.hours_until_service <= 30;
              const isDispatched = scheduledServices[maint.equipment_id]?.dispatched;
              
              return (
                <div 
                  key={maint.equipment_id}
                  className="bg-cat-card border border-cat-border rounded-2xl p-5 hover:border-cat-yellow/30 transition-all duration-300 text-left"
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
                    {/* Header */}
                    <div className="space-y-1.5 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span 
                          className="text-[9px] font-black px-2 py-0.5 rounded tracking-wider border"
                          style={{ 
                            backgroundColor: `${maint.status_color}10`, 
                            borderColor: `${maint.status_color}30`,
                            color: maint.status_color 
                          }}
                        >
                          {maint.maint_status}
                        </span>
                        
                        <span className="text-xs text-cat-subtext font-mono">
                          Servicing Target: {rates.engine_service_interval_hrs}h active engine hours
                        </span>
                      </div>
                      
                      <h4 className="text-white font-black text-base flex items-center gap-2">
                        <span className="text-cat-yellow text-xs font-mono">#{idx + 1}</span> {maint.equipment_id} <span className="text-cat-subtext font-normal text-xs">({maint.equipment_type})</span> — {maint.site_name}
                      </h4>
                    </div>

                    {/* Action button */}
                    <div className="shrink-0 flex items-center gap-3">
                      {isDispatched ? (
                        <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Dispatched at {scheduledServices[maint.equipment_id]?.timestamp}
                        </div>
                      ) : (
                        <button
                          onClick={() => handleDispatchService(maint.equipment_id)}
                          className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all hover:scale-[1.02] active:scale-[0.98] ${
                            isUrgent
                              ? 'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-500/15'
                              : 'bg-cat-steel border border-cat-border hover:border-cat-yellow text-slate-300 hover:text-white'
                          }`}
                        >
                          Dispatch Service Technician
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Engine Hour Progress Bar */}
                  <div className="space-y-1.5 mt-4">
                    <div className="flex justify-between text-[10px] text-cat-subtext font-mono">
                      <span>Service Life Consumed ({maint.hours_since_last_service}h / {rates.engine_service_interval_hrs}h)</span>
                      <span className="text-white font-bold">{maint.life_consumed_pct}%</span>
                    </div>
                    <div className="bg-cat-dark border border-cat-border/40 h-2.5 rounded-full overflow-hidden">
                      <div 
                        className="h-full rounded-full transition-all duration-700"
                        style={{ 
                          width: `${maint.life_consumed_pct}%`,
                          backgroundColor: maint.status_color
                        }}
                      />
                    </div>
                  </div>

                  {/* Breakdown details */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-cat-dark p-3.5 rounded-xl border border-cat-border/60 text-[11px] mt-4">
                    <div>
                      <span className="text-cat-subtext block uppercase tracking-wider text-[9px]">Active Engine Work</span>
                      <span className="font-semibold text-slate-200">{maint.total_engine_hours} hours total</span>
                    </div>
                    <div>
                      <span className="text-cat-subtext block uppercase tracking-wider text-[9px]">Hours Until Service</span>
                      <span className="font-semibold text-white font-mono" style={{ color: maint.status_color }}>{maint.hours_until_service}h left</span>
                    </div>
                    <div>
                      <span className="text-cat-subtext block uppercase tracking-wider text-[9px]">Calendar Days active</span>
                      <span className="font-semibold text-slate-200">{maint.total_calendar_days} days elapsed</span>
                    </div>
                    <div>
                      <span className="text-emerald-400 block uppercase tracking-wider text-[9px] font-bold">Engine-scheduling Savings</span>
                      <span className="font-bold text-emerald-400 font-mono">${maint.potential_savings_usd} saved</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
