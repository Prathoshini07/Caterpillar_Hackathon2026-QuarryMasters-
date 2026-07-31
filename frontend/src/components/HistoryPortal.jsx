import React from 'react';
import {
  X, Loader2, Search, ArrowUpDown, Filter, History
} from 'lucide-react';

const EQUIPMENT_TYPES = ['Excavator', 'Crane', 'Bulldozer', 'Grader'];
const inputCls =
  'w-full bg-[#1a1f2e] border border-[#2a3045] rounded-lg px-3 py-2.5 text-sm text-white ' +
  'placeholder-slate-500 focus:outline-none focus:border-yellow-400/60 focus:ring-1 ' +
  'focus:ring-yellow-400/30 transition-all';

const selectCls =
  'w-full bg-[#1a1f2e] border border-[#2a3045] rounded-lg px-3 py-2.5 text-sm text-white ' +
  'focus:outline-none focus:border-yellow-400/60 focus:ring-1 focus:ring-yellow-400/30 ' +
  'transition-all appearance-none cursor-pointer';

export default function HistoryPortal({ onClose }) {
  const [logs, setLogs] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');
  const [searchQuery, setSearchQuery] = React.useState('');
  const [sortConfig, setSortConfig] = React.useState({ key: 'check_out_date', direction: 'desc' });
  const [filterType, setFilterType] = React.useState('ALL');

  React.useEffect(() => {
    fetch('/api/portal/history')
      .then(res => res.json())
      .then(data => { setLogs(data); setLoading(false); })
      .catch(err => { setError('Failed to load history'); setLoading(false); });
  }, []);

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const sortedLogs = React.useMemo(() => {
    let sortable = [...logs];
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      sortable = sortable.filter(log => 
        log.rental_id.toLowerCase().includes(q) ||
        log.equipment_id.toLowerCase().includes(q) ||
        log.site_name.toLowerCase().includes(q) ||
        log.operator_name.toLowerCase().includes(q)
      );
    }
    if (filterType !== 'ALL') {
      sortable = sortable.filter(log => log.equipment_type === filterType);
    }
    sortable.sort((a, b) => {
      if (a[sortConfig.key] < b[sortConfig.key]) return sortConfig.direction === 'asc' ? -1 : 1;
      if (a[sortConfig.key] > b[sortConfig.key]) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sortable;
  }, [logs, sortConfig, searchQuery, filterType]);

  const Th = ({ label, sortKey }) => (
    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-white transition-colors"
        onClick={() => handleSort(sortKey)}>
      <div className="flex items-center gap-1">
        {label}
        {sortConfig.key === sortKey && <ArrowUpDown className="w-3 h-3" />}
      </div>
    </th>
  );

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.78)', backdropFilter: 'blur(6px)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>

      <div className="relative w-full max-w-6xl rounded-2xl border border-yellow-400/20 shadow-2xl overflow-hidden"
        style={{ background: 'linear-gradient(145deg,#111827 0%,#0f1420 100%)', boxShadow: '0 0 60px rgba(250,204,21,0.07),0 25px 50px rgba(0,0,0,0.6)' }}>
        
        {/* Top glow line */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-px rounded-full bg-gradient-to-r from-transparent via-yellow-400/60 to-transparent" />

        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-[#2a3045]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-yellow-400/10 border border-yellow-400/20 flex items-center justify-center">
              <History className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Rental History</h2>
              <p className="text-xs text-slate-500">View and filter historical rental logs</p>
            </div>
          </div>
          <button onClick={onClose}
            className="w-8 h-8 rounded-lg bg-[#1a1f2e] border border-[#2a3045] flex items-center justify-center text-slate-400 hover:text-white hover:border-yellow-400/40 transition-all">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <div className="px-6 py-5 max-h-[80vh] overflow-y-auto space-y-4">
          {/* Controls */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input type="text" placeholder="Search by ID, Site, or Operator..." 
                     value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                     className={`${inputCls} pl-9`} />
            </div>
            <div className="relative w-48">
              <Filter className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <select value={filterType} onChange={(e) => setFilterType(e.target.value)} 
                      className={`${selectCls} pl-9`}>
                <option value="ALL">All Types</option>
                {EQUIPMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="bg-[#1a1f2e] border border-[#2a3045] rounded-xl overflow-x-auto">
            {loading ? (
              <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-yellow-400" /></div>
            ) : error ? (
              <div className="p-8 text-center text-red-400">{error}</div>
            ) : (
              <table className="w-full text-sm text-left whitespace-nowrap">
                <thead className="bg-[#2a3045]/50 sticky top-0 z-10 backdrop-blur-md">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">#</th>
                    <Th label="Rental ID" sortKey="rental_id" />
                    <Th label="Equipment" sortKey="equipment_id" />
                    <Th label="Site" sortKey="site_name" />
                    <Th label="Operator" sortKey="operator_name" />
                    <Th label="Check-In" sortKey="check_in_date" />
                    <Th label="Check-Out" sortKey="check_out_date" />
                    <Th label="Runtime" sortKey="total_runtime_hrs" />
                    <Th label="Idle" sortKey="total_idle_hrs" />
                    <Th label="Downtime" sortKey="total_downtime_hrs" />
                    <Th label="Fuel (L)" sortKey="fuel_usage_liters" />
                    <Th label="Status" sortKey="anomaly_flag" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#2a3045]">
                  {sortedLogs.map((log, idx) => (
                    <tr key={log.rental_id} className="hover:bg-yellow-400/5 transition-colors">
                      <td className="px-4 py-3 font-mono text-slate-400 font-bold">{idx + 1}</td>
                      <td className="px-4 py-3 font-mono text-yellow-400">{log.rental_id}</td>
                      <td className="px-4 py-3">{log.equipment_id} <span className="text-slate-500 text-xs">({log.equipment_type})</span></td>
                      <td className="px-4 py-3">{log.site_name}</td>
                      <td className="px-4 py-3">{log.operator_name}</td>
                      <td className="px-4 py-3 text-slate-400">{log.check_in_date}</td>
                      <td className="px-4 py-3 text-slate-400">{log.check_out_date}</td>
                      <td className="px-4 py-3 font-mono text-emerald-400">{log.total_runtime_hrs}h</td>
                      <td className="px-4 py-3 font-mono text-amber-400">{log.total_idle_hrs}h</td>
                      <td className="px-4 py-3 font-mono text-red-400">{log.total_downtime_hrs}h</td>
                      <td className="px-4 py-3 font-mono">{log.fuel_usage_liters}L</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-[10px] font-bold rounded-md uppercase tracking-wide
                          ${log.anomaly_flag === 'OPTIMAL' ? 'bg-emerald-500/20 text-emerald-400' : 
                            log.anomaly_flag === 'HIGH_IDLE' ? 'bg-red-500/20 text-red-400' : 
                            'bg-amber-500/20 text-amber-400'}`}>
                          {log.anomaly_flag || 'N/A'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
