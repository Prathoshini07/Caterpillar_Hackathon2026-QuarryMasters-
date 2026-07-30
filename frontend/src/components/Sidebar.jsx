import React from 'react';
import { Home, Zap, Truck, AlertTriangle, Gauge, Calendar, Database, RefreshCw, ChevronLeft, ChevronRight, Layers, Bell, Activity, Coins, TrendingUp } from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, collapsed, setCollapsed, onReseed, isReseeding }) {
  const navItems = [
    { id: 'landing', label: 'Landing Page', icon: Home },
    { id: 'action-queue', label: '1. Action Queue', icon: Zap, highlight: true },
    { id: 'available', label: '2. Available Fleet', icon: Truck },
    { id: 'overdue-alerts', label: '3. Overdue 5-Level Alerts', icon: AlertTriangle, badge: '5 Severities' },
    { id: 'notifications-alerts', label: '3.5. Notifications & Alerts', icon: Bell, badge: 'Today' },
    { id: 'underutilized', label: '4. Underutilized Assets', icon: Gauge },
    { id: 'datewise-returns', label: '5. Datewise Returns', icon: Calendar },
    { id: 'demand-forecast', label: '7. Demand Forecast', icon: TrendingUp, badge: 'AI ML' },
    { id: 'equipment-details', label: '6. Live Details', icon: Layers },
    { id: 'anomaly-detection', label: '7. Anomaly Detection', icon: Activity, badge: 'AI+Rules' },
    { id: 'optimization', label: '8. Financial & Fleet Optimization', icon: Coins, badge: 'Cost' },
  ];

  return (
    <aside className={`bg-cat-card border-r border-cat-border flex flex-col justify-between transition-all duration-300 z-40 ${collapsed ? 'w-20' : 'w-64'}`}>
      <div>
        {/* Sidebar Brand Header */}
        <div className="p-4 border-b border-cat-border flex items-center justify-between">
          {!collapsed ? (
            <div className="flex items-center gap-2.5">
              <div className="bg-cat-yellow text-black font-black px-2.5 py-1 text-sm rounded">CAT</div>
              <div>
                <span className="font-extrabold text-sm text-white tracking-wider block">SMART RENTAL</span>
                <span className="text-[10px] text-cat-yellow font-mono">Quarry Masters '26</span>
              </div>
            </div>
          ) : (
            <div className="mx-auto bg-cat-yellow text-black font-black px-2 py-1 text-xs rounded">CAT</div>
          )}

          <button
            onClick={() => setCollapsed(!collapsed)}
            className="text-cat-subtext hover:text-white p-1 rounded-lg hover:bg-cat-steel transition-colors"
            title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
          </button>
        </div>

        {/* Navigation Section */}
        <div className="p-3 space-y-1.5">
          <div className={`px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-cat-subtext ${collapsed ? 'text-center' : ''}`}>
            {!collapsed ? 'Control Modules' : '---'}
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl font-medium text-sm transition-all text-left relative ${
                  isActive
                    ? 'bg-cat-yellow text-black font-bold shadow-lg shadow-cat-yellow/20'
                    : 'text-slate-300 hover:bg-cat-steel hover:text-white'
                }`}
                title={collapsed ? item.label : undefined}
              >
                <Icon className={`w-5 h-5 shrink-0 ${isActive ? 'text-black' : 'text-cat-subtext'}`} />
                
                {!collapsed && (
                  <div className="flex-1 flex items-center justify-between overflow-hidden">
                    <span className="truncate">{item.label}</span>
                    {item.badge && (
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                        isActive ? 'bg-black/20 text-black' : 'bg-red-500/20 text-red-400 border border-red-500/30'
                      }`}>
                        {item.badge}
                      </span>
                    )}
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Database Seeding & System Status Footer */}
      <div className="p-3 border-t border-cat-border space-y-2">
        {!collapsed && (
          <div className="bg-cat-dark/80 p-3 rounded-xl border border-cat-border/60 text-xs space-y-1">
            <div className="flex items-center justify-between text-cat-subtext">
              <span>Database Engine</span>
              <span className="text-emerald-400 font-mono font-bold">100 Rows/Table</span>
            </div>
            <div className="text-[11px] text-slate-400">PostgreSQL / SQLite Storage</div>
          </div>
        )}

        <button
          onClick={onReseed}
          disabled={isReseeding}
          className={`w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-xs font-bold border transition-all ${
            isReseeding
              ? 'bg-cat-steel text-cat-subtext border-cat-border cursor-not-allowed'
              : 'bg-cat-steel hover:bg-cat-border text-cat-yellow border-cat-yellow/30 hover:border-cat-yellow'
          }`}
          title="Reset and re-generate 100 rows per table"
        >
          <RefreshCw className={`w-4 h-4 ${isReseeding ? 'animate-spin text-cat-yellow' : ''}`} />
          {!collapsed && (isReseeding ? 'Reseeding 100 Rows...' : 'Reseed 100 Rows/Table')}
        </button>
      </div>
    </aside>
  );
}
