import React, { useState, useEffect } from 'react';
import { 
  Zap, Truck, AlertTriangle, Gauge, Calendar, RefreshCw, CheckCircle2, 
  Search, Filter, ShieldAlert, AlertCircle, ArrowUpRight, Phone, MapPin, 
  Clock, Play, Pause, ChevronRight, X, Sparkles, Send, Lock, CalendarRange
} from 'lucide-react';

export default function AssetDashboard({ activeTab, setActiveTab }) {
  const [stats, setStats] = useState(null);
  const [actionQueue, setActionQueue] = useState([]);
  const [availableEquip, setAvailableEquip] = useState([]);
  const [overdueAlerts, setOverdueAlerts] = useState(null);
  const [underutilized, setUnderutilized] = useState(null);
  const [datewiseData, setDatewiseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState(null);

  // Filters & Search
  const [actionFilter, setActionFilter] = useState('ALL'); // ALL, HIGH, OVERDUE, UNDERUTILIZED
  const [equipSearch, setEquipSearch] = useState('');
  const [idleThresholdPct, setIdleThresholdPct] = useState(50.0);

  // Datepicker filters for 3 Return Schedule sections
  const [overdueFromDate, setOverdueFromDate] = useState('');
  const [overdueToDate, setOverdueToDate] = useState('');
  const [overdueSearch, setOverdueSearch] = useState('');

  const [todaySearch, setTodaySearch] = useState('');

  const [upcomingFromDate, setUpcomingFromDate] = useState('');
  const [upcomingToDate, setUpcomingToDate] = useState('');
  const [upcomingSearch, setUpcomingSearch] = useState('');

  const [datewiseSection, setDatewiseSection] = useState('overdue');

  // Modals
  const [selectedAlertItem, setSelectedAlertItem] = useState(null);
  const [actionSuccessModal, setActionSuccessModal] = useState(null);

  // Fetch API data
  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [statsRes, actionRes, availRes, alertRes, underRes, dateRes] = await Promise.all([
        fetch('/api/dashboard/stats'),
        fetch('/api/dashboard/action-queue'),
        fetch('/api/dashboard/available-equipment'),
        fetch('/api/dashboard/overdue-alerts'),
        fetch(`/api/dashboard/underutilized?threshold_pct=${idleThresholdPct}`),
        fetch('/api/dashboard/datewise-returns')
      ]);

      const statsData = await statsRes.json();
      const actionData = await actionRes.json();
      const availData = await availRes.json();
      const alertData = await alertRes.json();
      const underData = await underRes.json();
      const dateData = await dateRes.json();

      setStats(statsData);
      setActionQueue(actionData.actions || []);
      setAvailableEquip(availData.available_equipments || []);
      setOverdueAlerts(alertData.levels || {});
      setUnderutilized(underData);
      setDatewiseData(dateData);
    } catch (err) {
      console.error("Error fetching dashboard data:", err);
      showNotification("Failed to connect to backend server. Make sure FastAPI is running on port 8000.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [idleThresholdPct]);

  const showNotification = (msg, type = "success") => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const handleExecuteAction = (item, actionText) => {
    setActionSuccessModal({
      title: "Action Dispatched Successfully",
      equipment_id: item.equipment_id,
      action: actionText,
      operator: item.operator_name || "Site Supervisor",
      contact: item.operator_contact || "Active Channel",
      timestamp: new Date().toLocaleTimeString()
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-cat-dark flex items-center justify-center p-6">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 border-4 border-cat-yellow border-t-transparent rounded-full animate-spin mx-auto" />
          <h3 className="font-bold text-lg text-white">Loading Caterpillar Telematics Dashboard...</h3>
          <p className="text-xs text-cat-subtext">Fetching 100 DB records for Sites, Operators, Equipment & Rental Logs</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-8 bg-cat-dark text-slate-100 min-h-screen">
      {/* Toast Notification */}
      {notification && (
        <div className={`fixed top-5 right-5 z-50 p-4 rounded-xl shadow-2xl flex items-center gap-3 border transition-all ${
          notification.type === 'error' ? 'bg-red-950 border-red-500 text-red-200' : 'bg-emerald-950 border-emerald-500 text-emerald-200'
        }`}>
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span className="text-sm font-medium">{notification.msg}</span>
        </div>
      )}

      {/* Action Success Modal */}
      {actionSuccessModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-cat-card border border-cat-yellow/40 p-6 rounded-2xl max-w-md w-full shadow-2xl space-y-4">
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-2">
                <div className="bg-cat-yellow/20 p-2 rounded-lg text-cat-yellow">
                  <Send className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-extrabold text-lg text-white">{actionSuccessModal.title}</h3>
                  <span className="text-xs font-mono text-cat-yellow">{actionSuccessModal.equipment_id}</span>
                </div>
              </div>
              <button onClick={() => setActionSuccessModal(null)} className="text-cat-subtext hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-cat-dark p-4 rounded-xl border border-cat-border space-y-2 text-xs">
              <div>
                <span className="text-cat-subtext block">Executed Action:</span>
                <span className="font-bold text-white text-sm">{actionSuccessModal.action}</span>
              </div>
              <div className="flex justify-between border-t border-cat-border pt-2 text-slate-300">
                <span>Target Operator: {actionSuccessModal.operator}</span>
                <span className="font-mono text-cat-subtext">{actionSuccessModal.contact}</span>
              </div>
              <div className="text-[10px] text-cat-subtext">Dispatched at {actionSuccessModal.timestamp}</div>
            </div>

            <button
              onClick={() => setActionSuccessModal(null)}
              className="w-full bg-cat-yellow text-black font-bold py-2.5 rounded-xl hover:bg-cat-yellowHover transition-all"
            >
              Acknowledge & Close
            </button>
          </div>
        </div>
      )}

      {/* Top Header Metrics Bar */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 border-b border-cat-border/80 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl md:text-3xl font-black tracking-tight text-white flex items-center gap-2">
              ASSET DECISION DASHBOARD
            </h1>
            <span className="bg-cat-yellow text-black text-xs px-2.5 py-1 font-bold rounded">
              SIMULATION DATE: {stats?.simulation_date}
            </span>
          </div>
          <p className="text-cat-subtext text-xs mt-1">Real-Time Caterpillar Machinery Status, Overdue Radar & Idle Efficiency Analytics</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchDashboardData}
            className="bg-cat-steel hover:bg-cat-border text-white text-xs font-bold px-3 py-2 rounded-lg flex items-center gap-2 border border-cat-border"
          >
            <RefreshCw className="w-3.5 h-3.5 text-cat-yellow" />
            Refresh Telematics
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-cat-card p-4 rounded-xl border border-cat-border">
          <div className="text-cat-subtext text-xs uppercase font-medium">Total Fleet</div>
          <div className="text-2xl font-black text-white font-mono mt-1">{stats?.total_equipment}</div>
          <div className="text-[11px] text-cat-subtext mt-1">100 EQX Units</div>
        </div>

        <div className="bg-cat-card p-4 rounded-xl border border-cat-border">
          <div className="text-cat-subtext text-xs uppercase font-medium">Active Rented</div>
          <div className="text-2xl font-black text-amber-400 font-mono mt-1">{stats?.rented_count}</div>
          <div className="text-[11px] text-cat-subtext mt-1">On Customer Sites</div>
        </div>

        <div 
          onClick={() => setActiveTab('available')}
          className="bg-cat-card p-4 rounded-xl border border-cat-border hover:border-emerald-500/50 cursor-pointer transition-all"
        >
          <div className="text-cat-subtext text-xs uppercase font-medium">Available Fleet</div>
          <div className="text-2xl font-black text-emerald-400 font-mono mt-1">{stats?.available_count}</div>
          <div className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
            Ready to Rent <ArrowUpRight className="w-3 h-3" />
          </div>
        </div>

        <div 
          onClick={() => setActiveTab('overdue-alerts')}
          className="bg-cat-card p-4 rounded-xl border border-cat-border hover:border-red-500/50 cursor-pointer transition-all"
        >
          <div className="text-cat-subtext text-xs uppercase font-medium">Overdue Items</div>
          <div className="text-2xl font-black text-red-400 font-mono mt-1">{stats?.overdue_count}</div>
          <div className="text-[11px] text-red-400 mt-1 flex items-center gap-1">
            5 Alert Severities <ArrowUpRight className="w-3 h-3" />
          </div>
        </div>

        <div 
          onClick={() => setActiveTab('underutilized')}
          className="bg-cat-card p-4 rounded-xl border border-cat-border hover:border-amber-500/50 cursor-pointer transition-all"
        >
          <div className="text-cat-subtext text-xs uppercase font-medium">Underutilized</div>
          <div className="text-2xl font-black text-amber-500 font-mono mt-1">{stats?.underutilized_count}</div>
          <div className="text-[11px] text-amber-400 mt-1 flex items-center gap-1">
            Idle Ratio &gt; 50% <ArrowUpRight className="w-3 h-3" />
          </div>
        </div>

        <div className="bg-cat-card p-4 rounded-xl border border-cat-border">
          <div className="text-cat-subtext text-xs uppercase font-medium">Avg Idle Ratio</div>
          <div className="text-2xl font-black text-cat-yellow font-mono mt-1">{stats?.avg_idle_ratio_pct}%</div>
          <div className="text-[11px] text-cat-subtext mt-1">(Idle / (Engine + Idle)) * 100</div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-cat-border pb-3">
        <button
          onClick={() => setActiveTab('action-queue')}
          className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all ${
            activeTab === 'action-queue'
              ? 'bg-cat-yellow text-black shadow-lg shadow-cat-yellow/20'
              : 'bg-cat-card text-cat-subtext hover:text-white border border-cat-border'
          }`}
        >
          <Zap className="w-4 h-4" />
          1. Action Queue ({actionQueue.length})
        </button>

        <button
          onClick={() => setActiveTab('available')}
          className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all ${
            activeTab === 'available'
              ? 'bg-cat-yellow text-black shadow-lg shadow-cat-yellow/20'
              : 'bg-cat-card text-cat-subtext hover:text-white border border-cat-border'
          }`}
        >
          <Truck className="w-4 h-4" />
          2. Available Equipments ({availableEquip.length})
        </button>

        <button
          onClick={() => setActiveTab('overdue-alerts')}
          className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all ${
            activeTab === 'overdue-alerts'
              ? 'bg-cat-yellow text-black shadow-lg shadow-cat-yellow/20'
              : 'bg-cat-card text-cat-subtext hover:text-white border border-cat-border'
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          3. Overdue Alerts (5 Levels)
        </button>

        <button
          onClick={() => setActiveTab('underutilized')}
          className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all ${
            activeTab === 'underutilized'
              ? 'bg-cat-yellow text-black shadow-lg shadow-cat-yellow/20'
              : 'bg-cat-card text-cat-subtext hover:text-white border border-cat-border'
          }`}
        >
          <Gauge className="w-4 h-4" />
          4. Underutilized Assets ({underutilized?.underutilized_count || 0})
        </button>

        <button
          onClick={() => setActiveTab('datewise-returns')}
          className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all ${
            activeTab === 'datewise-returns'
              ? 'bg-cat-yellow text-black shadow-lg shadow-cat-yellow/20'
              : 'bg-cat-card text-cat-subtext hover:text-white border border-cat-border'
          }`}
        >
          <Calendar className="w-4 h-4" />
          5. Datewise Return Schedule (3 Sections)
        </button>
      </div>

      {/* TAB 1: ACTION QUEUE */}
      {activeTab === 'action-queue' && (
        <div className="space-y-6">
          <div className="bg-cat-card p-6 rounded-2xl border border-cat-yellow/30 space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <div>
                <h2 className="text-xl font-black text-white flex items-center gap-2">
                  <Zap className="w-5 h-5 text-cat-yellow" />
                  DAILY ACTION QUEUE (OPERATIONAL DECISIONS FOR TODAY)
                </h2>
                <p className="text-xs text-cat-subtext mt-1">
                  Lists all high-priority items requiring immediate decisions today. Priority decays dynamically from HIGH to MED based on return date and idle ratio thresholds.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-cat-subtext">Filter:</span>
                <select
                  value={actionFilter}
                  onChange={(e) => setActionFilter(e.target.value)}
                  className="bg-cat-steel border border-cat-border text-white text-xs font-bold px-3 py-2 rounded-lg"
                >
                  <option value="ALL">All Actions ({actionQueue.length})</option>
                  <option value="HIGH">High Priority Only</option>
                  <option value="OVERDUE">Overdue Items</option>
                  <option value="UNDERUTILIZED">Underutilized Items</option>
                </select>
              </div>
            </div>

            {/* Action Cards List */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              {actionQueue
                .filter(item => {
                  if (actionFilter === 'HIGH') return item.priority === 'HIGH';
                  if (actionFilter === 'OVERDUE') return item.action_type === 'OVERDUE';
                  if (actionFilter === 'UNDERUTILIZED') return item.action_type === 'UNDERUTILIZED';
                  return true;
                })
                .map((item) => (
                  <div 
                    key={item.id}
                    className={`p-5 rounded-2xl border transition-all ${
                      item.priority === 'HIGH'
                        ? 'bg-cat-card border-red-500/40 hover:border-red-500'
                        : 'bg-cat-card border-amber-500/40 hover:border-amber-500'
                    }`}
                  >
                    <div className="flex justify-between items-start gap-2 mb-3">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-black px-2.5 py-1 rounded-md uppercase tracking-wider ${
                          item.priority === 'HIGH' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        }`}>
                          {item.priority} PRIORITY
                        </span>
                        <span className="text-xs font-mono text-cat-yellow font-bold">{item.equipment_id}</span>
                      </div>

                      <span className="text-[11px] text-cat-subtext font-mono">
                        Due: {item.due_date} {item.days_overdue > 0 && `(${item.days_overdue} days late)`}
                      </span>
                    </div>

                    <h3 className="font-extrabold text-white text-base mb-1">{item.title}</h3>
                    <p className="text-xs text-slate-300 mb-3">{item.description}</p>

                    <div className="bg-cat-dark p-3 rounded-xl border border-cat-border space-y-2 mb-4 text-xs">
                      <div className="flex items-center justify-between text-cat-subtext">
                        <span className="flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5 text-cat-yellow" /> Site:</span>
                        <span className="font-bold text-white">{item.site_name}</span>
                      </div>
                      <div className="flex items-center justify-between text-cat-subtext">
                        <span className="flex items-center gap-1.5"><Phone className="w-3.5 h-3.5 text-emerald-400" /> Operator:</span>
                        <span className="font-bold text-white">{item.operator_name} ({item.operator_contact})</span>
                      </div>
                    </div>

                    <div className="bg-cat-yellow/10 border border-cat-yellow/30 p-3 rounded-xl text-xs space-y-2">
                      <div className="font-bold text-cat-yellow uppercase text-[11px] tracking-wide">
                        RECOMMENDED ACTION TODAY:
                      </div>
                      <div className="text-white font-medium">{item.recommended_action}</div>
                      
                      <button
                        onClick={() => handleExecuteAction(item, item.recommended_action)}
                        className="mt-2 w-full bg-cat-yellow hover:bg-cat-yellowHover text-black font-extrabold py-2 px-3 rounded-lg text-xs flex items-center justify-center gap-2 transition-all shadow-md"
                      >
                        <Play className="w-3.5 h-3.5" /> Execute Recommended Action Now
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: AVAILABLE EQUIPMENTS */}
      {activeTab === 'available' && (
        <div className="space-y-6">
          <div className="bg-cat-card p-6 rounded-2xl border border-cat-border space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <div>
                <h2 className="text-xl font-black text-white flex items-center gap-2">
                  <Truck className="w-5 h-5 text-emerald-400" />
                  AVAILABLE HEAVY MACHINERY ({availableEquip.length} UNITS READY FOR RENT)
                </h2>
                <p className="text-xs text-cat-subtext mt-1">Unassigned machinery inspected and ready for immediate quarry site deployment.</p>
              </div>

              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="w-4 h-4 text-cat-subtext absolute left-3 top-2.5" />
                  <input
                    type="text"
                    placeholder="Search Equipment ID..."
                    value={equipSearch}
                    onChange={(e) => setEquipSearch(e.target.value)}
                    className="bg-cat-steel border border-cat-border text-white text-xs pl-9 pr-3 py-2 rounded-lg w-48 focus:border-cat-yellow outline-none"
                  />
                </div>
              </div>
            </div>

            {/* Equipment Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
              {availableEquip
                .filter(eq => eq.equipment_id.toLowerCase().includes(equipSearch.toLowerCase()))
                .map((eq) => (
                  <div key={eq.equipment_id} className="bg-cat-dark p-5 rounded-2xl border border-cat-border hover:border-emerald-500/50 transition-all space-y-3">
                    <div className="flex justify-between items-start">
                      <span className="font-mono text-base font-extrabold text-cat-yellow">{eq.equipment_id}</span>
                      <span className="bg-emerald-500/20 text-emerald-400 text-[10px] font-bold px-2.5 py-1 rounded-full border border-emerald-500/30">
                        {eq.readiness}
                      </span>
                    </div>

                    <div>
                      <h3 className="font-bold text-white text-lg">{eq.type}</h3>
                      <p className="text-xs text-cat-subtext flex items-center gap-1 mt-0.5">
                        <MapPin className="w-3.5 h-3.5 text-cat-yellow" /> Last Depot: {eq.last_site_name} ({eq.last_location})
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs bg-cat-card p-3 rounded-xl border border-cat-border">
                      <div>
                        <span className="text-cat-subtext block text-[10px]">Fuel Level</span>
                        <span className="font-bold text-white">{eq.fuel_level}</span>
                      </div>
                      <div>
                        <span className="text-cat-subtext block text-[10px]">Telematics Health</span>
                        <span className="font-bold text-emerald-400">{eq.telematics_health}</span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleExecuteAction(eq, `Assign ${eq.equipment_id} to new site rental contract`)}
                      className="w-full bg-emerald-500 hover:bg-emerald-600 text-black font-bold py-2 rounded-xl text-xs flex items-center justify-center gap-2 transition-all"
                    >
                      Dispatch / Allocate Machinery
                    </button>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: OVERDUE ALERTS (5 LEVELS) */}
      {activeTab === 'overdue-alerts' && overdueAlerts && (
        <div className="space-y-6">
          <div className="bg-cat-card p-6 rounded-2xl border border-cat-border space-y-4">
            <div>
              <h2 className="text-xl font-black text-white flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                FIVE-LEVEL OVERDUE ALERT SYSTEM
              </h2>
              <p className="text-xs text-cat-subtext mt-1">
                Automated alert escalation engine based on delay severity. Generates specific enforcement actions per level.
              </p>
            </div>

            {/* 5 Severity Columns */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 pt-2">
              {[1, 2, 3, 4, 5].map((lvlNum) => {
                const lvlData = overdueAlerts[lvlNum];
                if (!lvlData) return null;

                return (
                  <div 
                    key={lvlNum} 
                    className="bg-cat-dark p-4 rounded-2xl border flex flex-col justify-between space-y-3"
                    style={{ borderColor: `${lvlData.color}50` }}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-black uppercase px-2.5 py-0.5 rounded text-white" style={{ backgroundColor: lvlData.color }}>
                          {lvlData.badge}
                        </span>
                        <span className="font-mono text-lg font-black text-white">{lvlData.count}</span>
                      </div>

                      <h3 className="font-bold text-sm text-white">{lvlData.name}</h3>
                      <p className="text-[11px] text-cat-subtext mt-1">
                        {lvlNum === 1 && "0-1 day overdue / Due Today"}
                        {lvlNum === 2 && "2-3 days late notice"}
                        {lvlNum === 3 && "4-6 days late + Surcharge"}
                        {lvlNum === 4 && "7-10 days late + Contract Penalty"}
                        {lvlNum === 5 && ">10 days late + Remote Engine Lock"}
                      </p>
                    </div>

                    <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                      {lvlData.items.map((item, idx) => (
                        <div 
                          key={idx} 
                          className="bg-cat-card p-3 rounded-xl border border-cat-border text-xs space-y-1.5 hover:border-cat-yellow cursor-pointer"
                          onClick={() => setSelectedAlertItem(item)}
                        >
                          <div className="flex justify-between font-mono font-bold text-cat-yellow">
                            <span>{item.equipment_id}</span>
                            <span className="text-red-400">+{item.days_overdue}d</span>
                          </div>
                          <div className="text-white font-medium">{item.type}</div>
                          <div className="text-cat-subtext text-[11px] truncate">Site: {item.site_name}</div>
                          <div className="text-[10px] text-slate-400">Operator: {item.operator_name}</div>
                          
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleExecuteAction(item, item.recommended_action);
                            }}
                            className="w-full mt-1 bg-cat-steel hover:bg-cat-yellow hover:text-black text-cat-yellow text-[10px] font-bold py-1 px-2 rounded flex items-center justify-center gap-1 transition-all"
                          >
                            Dispatch Level {lvlNum} Alert
                          </button>
                        </div>
                      ))}

                      {lvlData.items.length === 0 && (
                        <div className="text-center py-6 text-xs text-cat-subtext italic">No assets at Level {lvlNum} alert.</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: UNDERUTILIZED ASSETS */}
      {activeTab === 'underutilized' && underutilized && (
        <div className="space-y-6">
          <div className="bg-cat-card p-6 rounded-2xl border border-cat-border space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <div>
                <h2 className="text-xl font-black text-white flex items-center gap-2">
                  <Gauge className="w-5 h-5 text-amber-500" />
                  UNDERUTILIZED ASSETS ANALYZER ({underutilized.underutilized_count} FLAGGED)
                </h2>
                <p className="text-xs text-cat-subtext mt-1">
                  Formula: <span className="font-mono text-cat-yellow font-bold">Idle Efficiency Ratio = (Idle Hours / (Engine Hours + Idle Hours)) * 100%</span>. Flagged if ratio &gt; 50%. (Note: Engine Hours &ge; Idle Hours).
                </p>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs text-cat-subtext">Threshold Ratio:</span>
                <input
                  type="number"
                  step="5"
                  value={idleThresholdPct}
                  onChange={(e) => setIdleThresholdPct(parseFloat(e.target.value) || 50.0)}
                  className="bg-cat-steel border border-cat-border text-white text-xs font-mono font-bold px-3 py-1.5 rounded-lg w-20 text-center"
                />
                <span className="text-xs text-cat-subtext">% Idle Ratio</span>
              </div>
            </div>

            {/* Underutilized Table */}
            <div className="overflow-x-auto rounded-xl border border-cat-border">
              <table className="w-full text-left text-xs">
                <thead className="bg-cat-steel text-cat-subtext uppercase font-bold text-[10px] tracking-wider">
                  <tr>
                    <th className="p-3">Equipment ID</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Site Location</th>
                    <th className="p-3">Engine Runtime (Total)</th>
                    <th className="p-3">Idle Hours</th>
                    <th className="p-3">Productive Hours</th>
                    <th className="p-3">Idle Efficiency Ratio %</th>
                    <th className="p-3">Anomaly Flag</th>
                    <th className="p-3">Recommended Decision</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cat-border bg-cat-card">
                  {underutilized.equipments.map((item) => (
                    <tr 
                      key={item.rental_id}
                      className={`hover:bg-cat-cardHover transition-colors ${
                        item.is_underutilized ? 'bg-amber-500/5' : ''
                      }`}
                    >
                      <td className="p-3 font-mono font-bold text-cat-yellow">{item.equipment_id}</td>
                      <td className="p-3 font-semibold text-white">{item.type}</td>
                      <td className="p-3 text-slate-300">{item.site_name}</td>
                      <td className="p-3 font-mono text-emerald-400 font-bold">{item.engine_hours} hrs</td>
                      <td className="p-3 font-mono text-red-400 font-bold">{item.idle_hours} hrs</td>
                      <td className="p-3 font-mono text-slate-200">{item.productive_hours} hrs</td>
                      <td className="p-3 font-mono font-black">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-cat-dark h-2 rounded-full overflow-hidden">
                            <div 
                              className={`h-full ${item.idle_efficiency_ratio > 70 ? 'bg-red-500' : 'bg-amber-500'}`} 
                              style={{ width: `${Math.min(100, item.idle_efficiency_ratio)}%` }}
                            />
                          </div>
                          <span className={item.idle_efficiency_ratio > 50 ? 'text-red-400 font-bold' : 'text-emerald-400'}>
                            {item.idle_efficiency_ratio}%
                          </span>
                        </div>
                      </td>
                      <td className="p-3">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          item.is_underutilized ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-emerald-500/20 text-emerald-400'
                        }`}>
                          {item.anomaly_flag}
                        </span>
                      </td>
                      <td className="p-3 text-slate-300 font-medium">
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate max-w-xs">{item.recommendation}</span>
                          <button
                            onClick={() => handleExecuteAction(item, item.recommendation)}
                            className="bg-cat-steel hover:bg-cat-yellow hover:text-black text-cat-yellow text-[10px] font-bold px-2.5 py-1 rounded transition-all shrink-0"
                          >
                            Execute
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: DATEWISE RETURN SCHEDULE (SPLIT INTO 3 SECTIONS WITH DATEPICKERS & TABLES) */}
      {activeTab === 'datewise-returns' && datewiseData && (
        <div className="space-y-8">
          {/* Toggle buttons for Datewise Return Sections */}
          <div className="flex bg-cat-card p-1 rounded-xl border border-cat-border max-w-md mx-auto shadow-lg">
            <button
              onClick={() => setDatewiseSection('overdue')}
              className={`flex-1 py-2 text-xs font-black rounded-lg transition-all tracking-wider ${datewiseSection === 'overdue' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'text-cat-subtext hover:text-white'}`}
            >
              1. OVERDUE
            </button>
            <button
              onClick={() => setDatewiseSection('today')}
              className={`flex-1 py-2 text-xs font-black rounded-lg transition-all tracking-wider ${datewiseSection === 'today' ? 'bg-cat-yellow/20 text-cat-yellow border border-cat-yellow/30' : 'text-cat-subtext hover:text-white'}`}
            >
              2. TODAY
            </button>
            <button
              onClick={() => setDatewiseSection('upcoming')}
              className={`flex-1 py-2 text-xs font-black rounded-lg transition-all tracking-wider ${datewiseSection === 'upcoming' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'text-cat-subtext hover:text-white'}`}
            >
              3. UPCOMING
            </button>
          </div>

          {/* SECTION 1: OVERDUE RETURNS */}
          {datewiseSection === 'overdue' && (
          <div className="bg-cat-card p-6 rounded-2xl border border-red-500/40 space-y-4">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-cat-border pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="bg-red-500 text-white text-xs font-black px-2.5 py-1 rounded uppercase tracking-wider">
                    SECTION 1
                  </span>
                  <h2 className="text-xl font-black text-red-400 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5" />
                    OVERDUE RETURNS ({datewiseData.overdue_count} UNITS LATE)
                  </h2>
                </div>
                <p className="text-xs text-cat-subtext mt-1">Equipment past due check-out date needing immediate recovery or contract extension.</p>
              </div>

              {/* Datepicker Filters */}
              <div className="flex flex-wrap items-center gap-2">
                <CalendarRange className="w-4 h-4 text-cat-subtext" />
                <span className="text-xs text-cat-subtext">From:</span>
                <input
                  type="date"
                  value={overdueFromDate}
                  onChange={(e) => setOverdueFromDate(e.target.value)}
                  className="bg-cat-steel border border-cat-border text-white text-xs px-2.5 py-1.5 rounded-lg focus:border-red-500 outline-none"
                />
                <span className="text-xs text-cat-subtext">To:</span>
                <input
                  type="date"
                  value={overdueToDate}
                  onChange={(e) => setOverdueToDate(e.target.value)}
                  className="bg-cat-steel border border-cat-border text-white text-xs px-2.5 py-1.5 rounded-lg focus:border-red-500 outline-none"
                />
                <input
                  type="text"
                  placeholder="Filter Equipment/Site..."
                  value={overdueSearch}
                  onChange={(e) => setOverdueSearch(e.target.value)}
                  className="bg-cat-steel border border-cat-border text-white text-xs px-3 py-1.5 rounded-lg w-40 focus:border-red-500 outline-none"
                />
                {(overdueFromDate || overdueToDate || overdueSearch) && (
                  <button 
                    onClick={() => { setOverdueFromDate(''); setOverdueToDate(''); setOverdueSearch(''); }}
                    className="text-xs text-red-400 hover:underline"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            {/* Overdue Table */}
            <div className="overflow-x-auto rounded-xl border border-cat-border">
              <table className="w-full text-left text-xs">
                <thead className="bg-cat-steel text-cat-subtext uppercase font-bold text-[10px] tracking-wider">
                  <tr>
                    <th className="p-3">Equipment ID</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Site & Location</th>
                    <th className="p-3">Operator & Contact</th>
                    <th className="p-3">Check-In Date</th>
                    <th className="p-3">Check-Out Date</th>
                    <th className="p-3">Days Overdue</th>
                    <th className="p-3">Alert Level</th>
                    <th className="p-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cat-border bg-cat-card">
                  {datewiseData.overdue_returns
                    .filter(item => {
                      if (overdueFromDate && item.check_out_date < overdueFromDate) return false;
                      if (overdueToDate && item.check_out_date > overdueToDate) return false;
                      if (overdueSearch) {
                        const q = overdueSearch.toLowerCase();
                        return item.equipment_id.toLowerCase().includes(q) || item.site_name.toLowerCase().includes(q) || item.type.toLowerCase().includes(q);
                      }
                      return true;
                    })
                    .map((item) => (
                      <tr key={item.rental_id} className="hover:bg-cat-cardHover transition-colors bg-red-500/5">
                        <td className="p-3 font-mono font-bold text-cat-yellow">{item.equipment_id}</td>
                        <td className="p-3 font-semibold text-white">{item.type}</td>
                        <td className="p-3 text-slate-300">{item.site_name} ({item.location})</td>
                        <td className="p-3 text-slate-300">{item.operator_name} <span className="text-cat-subtext block text-[10px]">{item.operator_contact}</span></td>
                        <td className="p-3 font-mono text-cat-subtext">{item.check_in_date}</td>
                        <td className="p-3 font-mono text-red-400 font-bold">{item.check_out_date}</td>
                        <td className="p-3 font-mono font-black text-red-400">+{item.days_overdue} Days Late</td>
                        <td className="p-3">
                          <span className="bg-red-500/20 text-red-400 text-[10px] font-bold px-2 py-0.5 rounded border border-red-500/30">
                            Level {item.alert_level} Alert
                          </span>
                        </td>
                        <td className="p-3">
                          <button
                            onClick={() => handleExecuteAction(item, `Dispatch Level ${item.alert_level} Recovery Alert for ${item.equipment_id}`)}
                            className="bg-red-500 hover:bg-red-600 text-white font-bold px-3 py-1 rounded text-[10px] transition-all"
                          >
                            Dispatch Recovery
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
          )}


          {/* SECTION 2: TODAY'S RETURNS */}
          {datewiseSection === 'today' && (
          <div className="bg-cat-card p-6 rounded-2xl border border-cat-yellow/50 space-y-4">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-cat-border pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="bg-cat-yellow text-black text-xs font-black px-2.5 py-1 rounded uppercase tracking-wider">
                    SECTION 2
                  </span>
                  <h2 className="text-xl font-black text-cat-yellow flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    TODAY'S SCHEDULED RETURNS ({datewiseData.today_count} UNITS DUE TODAY)
                  </h2>
                </div>
                <p className="text-xs text-cat-subtext mt-1">Contracts expiring today (Simulation Date: {stats?.simulation_date}). Confirm check-in or extend lease.</p>
              </div>

              <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-cat-subtext" />
                <input
                  type="text"
                  placeholder="Filter Today's Equipment..."
                  value={todaySearch}
                  onChange={(e) => setTodaySearch(e.target.value)}
                  className="bg-cat-steel border border-cat-border text-white text-xs px-3 py-1.5 rounded-lg w-48 focus:border-cat-yellow outline-none"
                />
              </div>
            </div>

            {/* Today Table */}
            <div className="overflow-x-auto rounded-xl border border-cat-border">
              <table className="w-full text-left text-xs">
                <thead className="bg-cat-steel text-cat-subtext uppercase font-bold text-[10px] tracking-wider">
                  <tr>
                    <th className="p-3">Equipment ID</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Site & Location</th>
                    <th className="p-3">Operator & Contact</th>
                    <th className="p-3">Check-In Date</th>
                    <th className="p-3">Return Due Date</th>
                    <th className="p-3">Engine vs Idle Hours</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cat-border bg-cat-card">
                  {datewiseData.today_returns
                    .filter(item => !todaySearch || item.equipment_id.toLowerCase().includes(todaySearch.toLowerCase()) || item.site_name.toLowerCase().includes(todaySearch.toLowerCase()))
                    .map((item) => (
                      <tr key={item.rental_id} className="hover:bg-cat-cardHover transition-colors bg-cat-yellow/5">
                        <td className="p-3 font-mono font-bold text-cat-yellow">{item.equipment_id}</td>
                        <td className="p-3 font-semibold text-white">{item.type}</td>
                        <td className="p-3 text-slate-300">{item.site_name} ({item.location})</td>
                        <td className="p-3 text-slate-300">{item.operator_name} <span className="text-cat-subtext block text-[10px]">{item.operator_contact}</span></td>
                        <td className="p-3 font-mono text-cat-subtext">{item.check_in_date}</td>
                        <td className="p-3 font-mono text-cat-yellow font-bold">{item.check_out_date}</td>
                        <td className="p-3 font-mono text-slate-300">{item.engine_hours}h total / {item.idle_hours}h idle</td>
                        <td className="p-3">
                          <span className="bg-cat-yellow text-black text-[10px] font-black px-2 py-0.5 rounded">
                            DUE TODAY
                          </span>
                        </td>
                        <td className="p-3">
                          <button
                            onClick={() => handleExecuteAction(item, `Confirm Check-In and transport for ${item.equipment_id}`)}
                            className="bg-cat-yellow hover:bg-cat-yellowHover text-black font-bold px-3 py-1 rounded text-[10px] transition-all"
                          >
                            Confirm Check-In
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
          )}


          {/* SECTION 3: UPCOMING DUE RETURNS */}
          {datewiseSection === 'upcoming' && (
          <div className="bg-cat-card p-6 rounded-2xl border border-emerald-500/40 space-y-4">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-cat-border pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="bg-emerald-500 text-black text-xs font-black px-2.5 py-1 rounded uppercase tracking-wider">
                    SECTION 3
                  </span>
                  <h2 className="text-xl font-black text-emerald-400 flex items-center gap-2">
                    <Calendar className="w-5 h-5" />
                    UPCOMING DUE RETURNS ({datewiseData.upcoming_count} UNITS SCHEDULED)
                  </h2>
                </div>
                <p className="text-xs text-cat-subtext mt-1">Future return dates. Plan transport logistics and pre-position equipment for next rentals.</p>
              </div>

              {/* Datepicker Filters */}
              <div className="flex flex-wrap items-center gap-2">
                <CalendarRange className="w-4 h-4 text-cat-subtext" />
                <span className="text-xs text-cat-subtext">From:</span>
                <input
                  type="date"
                  value={upcomingFromDate}
                  onChange={(e) => setUpcomingFromDate(e.target.value)}
                  className="bg-cat-steel border border-cat-border text-white text-xs px-2.5 py-1.5 rounded-lg focus:border-emerald-500 outline-none"
                />
                <span className="text-xs text-cat-subtext">To:</span>
                <input
                  type="date"
                  value={upcomingToDate}
                  onChange={(e) => setUpcomingToDate(e.target.value)}
                  className="bg-cat-steel border border-cat-border text-white text-xs px-2.5 py-1.5 rounded-lg focus:border-emerald-500 outline-none"
                />
                <input
                  type="text"
                  placeholder="Filter Equipment/Site..."
                  value={upcomingSearch}
                  onChange={(e) => setUpcomingSearch(e.target.value)}
                  className="bg-cat-steel border border-cat-border text-white text-xs px-3 py-1.5 rounded-lg w-40 focus:border-emerald-500 outline-none"
                />
                {(upcomingFromDate || upcomingToDate || upcomingSearch) && (
                  <button 
                    onClick={() => { setUpcomingFromDate(''); setUpcomingToDate(''); setUpcomingSearch(''); }}
                    className="text-xs text-emerald-400 hover:underline"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            {/* Upcoming Table */}
            <div className="overflow-x-auto rounded-xl border border-cat-border">
              <table className="w-full text-left text-xs">
                <thead className="bg-cat-steel text-cat-subtext uppercase font-bold text-[10px] tracking-wider">
                  <tr>
                    <th className="p-3">Equipment ID</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Site & Location</th>
                    <th className="p-3">Operator & Contact</th>
                    <th className="p-3">Check-In Date</th>
                    <th className="p-3">Scheduled Return Date</th>
                    <th className="p-3">Days Remaining</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cat-border bg-cat-card">
                  {datewiseData.upcoming_returns
                    .filter(item => {
                      if (upcomingFromDate && item.check_out_date < upcomingFromDate) return false;
                      if (upcomingToDate && item.check_out_date > upcomingToDate) return false;
                      if (upcomingSearch) {
                        const q = upcomingSearch.toLowerCase();
                        return item.equipment_id.toLowerCase().includes(q) || item.site_name.toLowerCase().includes(q) || item.type.toLowerCase().includes(q);
                      }
                      return true;
                    })
                    .map((item) => (
                      <tr key={item.rental_id} className="hover:bg-cat-cardHover transition-colors">
                        <td className="p-3 font-mono font-bold text-cat-yellow">{item.equipment_id}</td>
                        <td className="p-3 font-semibold text-white">{item.type}</td>
                        <td className="p-3 text-slate-300">{item.site_name} ({item.location})</td>
                        <td className="p-3 text-slate-300">{item.operator_name} <span className="text-cat-subtext block text-[10px]">{item.operator_contact}</span></td>
                        <td className="p-3 font-mono text-cat-subtext">{item.check_in_date}</td>
                        <td className="p-3 font-mono text-emerald-400 font-bold">{item.check_out_date}</td>
                        <td className="p-3 font-mono text-emerald-400 font-bold">{item.days_remaining} Days Left</td>
                        <td className="p-3">
                          <span className="bg-emerald-500/20 text-emerald-400 text-[10px] font-bold px-2 py-0.5 rounded border border-emerald-500/30">
                            ON SCHEDULE
                          </span>
                        </td>
                        <td className="p-3">
                          <button
                            onClick={() => handleExecuteAction(item, `Pre-schedule transport haulage for ${item.equipment_id} on ${item.check_out_date}`)}
                            className="bg-cat-steel hover:bg-emerald-500 hover:text-black text-emerald-400 font-bold px-3 py-1 rounded text-[10px] transition-all"
                          >
                            Schedule Haulage
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
          )}

        </div>
      )}
    </div>
  );
}
