import React, { useState, useEffect, useMemo } from 'react';
import { Loader2, Search, ArrowUpDown, Filter, Eye, AlertTriangle } from 'lucide-react';

export default function LiveEquipmentDetails() {
  const [equipments, setEquipments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'equipment_id', direction: 'asc' });
  const [filterStatus, setFilterStatus] = useState('ALL');

  useEffect(() => {
    fetch('/api/dashboard/equipment')
      .then(res => res.json())
      .then(data => { setEquipments(data.equipments || []); setLoading(false); })
      .catch(err => { setError('Failed to load equipment details'); setLoading(false); });
  }, []);

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const sortedData = useMemo(() => {
    let sortable = [...equipments];
    
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      sortable = sortable.filter(eq => 
        eq.equipment_id.toLowerCase().includes(q) ||
        eq.type.toLowerCase().includes(q) ||
        eq.site_name.toLowerCase().includes(q) ||
        eq.operator_name.toLowerCase().includes(q)
      );
    }
    
    if (filterStatus !== 'ALL') {
      sortable = sortable.filter(eq => eq.live_status === filterStatus);
    }
    
    sortable.sort((a, b) => {
      if (a[sortConfig.key] < b[sortConfig.key]) return sortConfig.direction === 'asc' ? -1 : 1;
      if (a[sortConfig.key] > b[sortConfig.key]) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sortable;
  }, [equipments, sortConfig, searchQuery, filterStatus]);

  const Th = ({ label, sortKey }) => (
    <th className="px-4 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-white transition-colors"
        onClick={() => handleSort(sortKey)}>
      <div className="flex items-center gap-1.5">
        {label}
        {sortConfig.key === sortKey && <ArrowUpDown className="w-3.5 h-3.5" />}
      </div>
    </th>
  );

  const getStatusStyle = (status) => {
    switch (status) {
      case 'Available': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'In Use': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'Idle': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'Returning Today': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      case 'Overdue': return 'bg-red-500/10 text-red-400 border-red-500/20';
      default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  if (loading) return <div className="flex justify-center p-12"><Loader2 className="w-8 h-8 animate-spin text-cat-yellow" /></div>;
  if (error) return <div className="p-8 text-center text-red-400"><AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-80" />{error}</div>;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Eye className="w-6 h-6 text-cat-yellow" />
            Live Equipment Details
          </h2>
          <p className="text-sm text-cat-subtext mt-1">Real-time status, assignments, and telematics health.</p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input 
            type="text" 
            placeholder="Search by ID, Type, Site, or Operator..." 
            value={searchQuery} 
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-cat-card border border-cat-border rounded-xl px-4 py-2.5 pl-10 text-sm text-white placeholder-slate-500 focus:border-cat-yellow focus:ring-1 focus:ring-cat-yellow transition-all"
          />
        </div>
        <div className="relative w-full sm:w-56">
          <Filter className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <select 
            value={filterStatus} 
            onChange={(e) => setFilterStatus(e.target.value)} 
            className="w-full bg-cat-card border border-cat-border rounded-xl px-4 py-2.5 pl-10 text-sm text-white focus:border-cat-yellow focus:ring-1 focus:ring-cat-yellow transition-all appearance-none cursor-pointer"
          >
            <option value="ALL">All Statuses</option>
            <option value="Available">Available</option>
            <option value="In Use">In Use</option>
            <option value="Idle">Idle</option>
            <option value="Returning Today">Returning Today</option>
            <option value="Overdue">Overdue</option>
          </select>
          <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs">▾</div>
        </div>
      </div>

      <div className="bg-cat-card border border-cat-border rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto max-h-[65vh]">
          <table className="w-full text-sm text-left whitespace-nowrap">
            <thead className="bg-cat-dark/80 border-b border-cat-border sticky top-0 z-10 backdrop-blur-md">
              <tr>
                <Th label="Equipment" sortKey="equipment_id" />
                <Th label="Status" sortKey="live_status" />
                <Th label="Assigned Site" sortKey="site_name" />
                <Th label="Location" sortKey="location" />
                <Th label="Operator" sortKey="operator_name" />
                <Th label="Return Info" sortKey="check_out_date" />
                <Th label="Idle Ratio" sortKey="idle_ratio" />
              </tr>
            </thead>
            <tbody className="divide-y divide-cat-border">
              {sortedData.map(eq => (
                <tr key={eq.equipment_id} className="hover:bg-cat-dark/40 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-mono text-cat-yellow font-bold">{eq.equipment_id}</div>
                    <div className="text-xs text-cat-subtext">{eq.type}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2.5 py-1 text-[10px] font-bold rounded-md border uppercase tracking-wider ${getStatusStyle(eq.live_status)}`}>
                      {eq.live_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-200">
                    {eq.live_status === 'Available' ? <span className="text-slate-500 italic">Central Yard</span> : eq.site_name}
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">
                    {eq.live_status === 'Available' ? 'Peoria Depot' : eq.location}
                  </td>
                  <td className="px-4 py-3 text-slate-300">
                    {eq.live_status === 'Available' ? <span className="text-slate-500 italic">Unassigned</span> : eq.operator_name}
                  </td>
                  <td className="px-4 py-3 text-slate-300">
                    {eq.live_status === 'Available' ? (
                      <span className="text-slate-500 text-xs">Ready</span>
                    ) : (
                      <div className="text-xs">
                        {eq.check_out_date}
                        {eq.days_overdue > 0 && <span className="ml-1 text-red-400 font-bold">({eq.days_overdue}d late)</span>}
                        {eq.days_remaining > 0 && <span className="ml-1 text-emerald-400">({eq.days_remaining}d left)</span>}
                        {eq.days_remaining === 0 && eq.days_overdue === 0 && <span className="ml-1 text-yellow-400 font-bold">(Today)</span>}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {eq.live_status === 'Available' ? (
                      <span className="text-slate-500 text-xs">-</span>
                    ) : (
                      <span className={`font-mono text-xs font-bold ${eq.idle_ratio > 75 ? 'text-red-400' : eq.idle_ratio > 50 ? 'text-amber-400' : 'text-emerald-400'}`}>
                        {eq.idle_ratio}%
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
