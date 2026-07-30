import React from 'react';
import { ShieldAlert, Cpu, Truck, Activity, ArrowRight, CheckCircle2, Clock, BarChart3, Radio, Database, UserCircle2, History } from 'lucide-react';

export default function LandingPage({ onEnterDashboard, onOpenPortal, onOpenHistory }) {
  return (
    <div className="min-h-screen bg-cat-dark text-slate-100 flex flex-col relative overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-cat-yellow/5 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-amber-600/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Top Header */}
      <header className="border-b border-cat-border/80 bg-cat-card/80 backdrop-blur-md sticky top-0 z-50 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <div className="bg-cat-yellow text-black px-3 py-1 font-black text-xl tracking-tighter rounded shadow-md">
            CAT
          </div>
          <div>
            <h1 className="font-extrabold text-lg tracking-wide text-white flex items-center gap-2">
              SMART RENTAL TRACKING
              <span className="bg-amber-500/20 text-cat-yellow text-xs px-2.5 py-0.5 rounded-full border border-cat-yellow/30 font-semibold">
                QuarryMasters '26
              </span>
            </h1>
            <p className="text-xs text-cat-subtext">Intelligent Heavy Machinery Fleet Optimization</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="hidden md:flex items-center gap-2 text-xs text-cat-subtext bg-cat-steel px-3 py-1.5 rounded-lg border border-cat-border">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            PostgreSQL DB Synced (100 Rows/Table)
          </div>
          <button
            onClick={onOpenHistory}
            className="border border-cat-yellow/40 hover:border-cat-yellow text-cat-yellow hover:bg-cat-yellow/10 font-bold px-5 py-2.5 rounded-lg flex items-center gap-2 transition-all transform hover:scale-[1.02]"
          >
            <History className="w-4 h-4" />
            Rental History
          </button>
          <button
            onClick={onOpenPortal}
            className="border border-cat-yellow/40 hover:border-cat-yellow text-cat-yellow hover:bg-cat-yellow/10 font-bold px-5 py-2.5 rounded-lg flex items-center gap-2 transition-all transform hover:scale-[1.02]"
          >
            <UserCircle2 className="w-4 h-4" />
            User Portal
          </button>
          <button
            onClick={onEnterDashboard}
            className="bg-cat-yellow hover:bg-cat-yellowHover text-black font-bold px-5 py-2.5 rounded-lg flex items-center gap-2 transition-all transform hover:scale-[1.02] shadow-lg shadow-cat-yellow/20"
          >
            Launch Control Center
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="px-6 py-16 md:py-24 max-w-7xl mx-auto flex-1 flex flex-col justify-center">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 bg-cat-yellow/10 border border-cat-yellow/30 text-cat-yellow text-xs font-bold px-4 py-1.5 rounded-full">
              <Radio className="w-4 h-4 animate-pulse text-cat-yellow" />
              DECISION-DRIVEN FLEET TELEMETRY — NOT SPREADSHEETS
            </div>

            <h1 className="text-4xl md:text-6xl font-black tracking-tight leading-none text-white">
              STOP MANAGING MACHINERY ON SPREADSHEETS. <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cat-yellow via-amber-400 to-yellow-200">
                DRIVE REAL-TIME ACTIONS.
              </span>
            </h1>

            <p className="text-slate-300 text-lg md:text-xl font-normal leading-relaxed max-w-2xl">
              Eliminate lost equipment, misallocation downtime, and unexpected rental extensions. 
              Automatically identify underutilized assets, predict regional demand, and enforce a 
              <span className="text-cat-yellow font-semibold"> 5-level overdue alert protocol</span> across 100+ active mining & construction sites.
            </p>

            {/* Live Telemetry Banner */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4">
              <div className="bg-cat-card p-4 rounded-xl border border-cat-border">
                <div className="text-cat-subtext text-xs font-medium uppercase tracking-wider mb-1">Tracked Assets</div>
                <div className="text-2xl md:text-3xl font-black text-white font-mono">100+</div>
                <div className="text-emerald-400 text-xs mt-1 flex items-center gap-1">
                  <Activity className="w-3 h-3" /> Live Telematics
                </div>
              </div>

              <div className="bg-cat-card p-4 rounded-xl border border-cat-border">
                <div className="text-cat-subtext text-xs font-medium uppercase tracking-wider mb-1">Active Sites</div>
                <div className="text-2xl md:text-3xl font-black text-cat-yellow font-mono">100</div>
                <div className="text-cat-subtext text-xs mt-1">S001 to S100</div>
              </div>

              <div className="bg-cat-card p-4 rounded-xl border border-cat-border">
                <div className="text-cat-subtext text-xs font-medium uppercase tracking-wider mb-1">Overdue Protocol</div>
                <div className="text-2xl md:text-3xl font-black text-red-400 font-mono">5 Levels</div>
                <div className="text-red-400/80 text-xs mt-1">Automated Alerts</div>
              </div>

              <div className="bg-cat-card p-4 rounded-xl border border-cat-border">
                <div className="text-cat-subtext text-xs font-medium uppercase tracking-wider mb-1">Idle Threshold</div>
                <div className="text-2xl md:text-3xl font-black text-amber-400 font-mono">&gt; 6 Hrs</div>
                <div className="text-amber-400 text-xs mt-1">Auto Flagged</div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                onClick={onEnterDashboard}
                className="bg-cat-yellow hover:bg-cat-yellowHover text-black font-extrabold text-lg px-8 py-4 rounded-xl flex items-center gap-3 transition-all transform hover:scale-105 shadow-xl shadow-cat-yellow/25"
              >
                Access Asset Dashboard
                <ArrowRight className="w-5 h-5" />
              </button>

              <div className="flex items-center gap-2 text-sm text-cat-subtext">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                SQLAlchemy + PostgreSQL / SQLite Engine Ready
              </div>
            </div>
          </div>

          {/* Graphical Machinery Teaser Card */}
          <div className="lg:col-span-5">
            <div className="bg-gradient-to-b from-cat-card to-cat-steel p-6 rounded-2xl border border-cat-yellow/30 shadow-2xl relative">
              <div className="flex items-center justify-between border-b border-cat-border pb-4 mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-red-500" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500" />
                  <div className="w-3 h-3 rounded-full bg-emerald-500" />
                </div>
                <span className="text-xs font-mono text-cat-yellow bg-cat-yellow/10 px-2 py-0.5 rounded border border-cat-yellow/20">
                  DECISION MATRIX ACTIVE
                </span>
              </div>

              {/* Sample Action Queue Card preview */}
              <div className="space-y-3">
                <div className="bg-cat-dark/90 p-4 rounded-xl border border-red-500/40">
                  <div className="flex justify-between items-start mb-2">
                    <span className="bg-red-500/20 text-red-400 text-xs font-bold px-2 py-0.5 rounded border border-red-500/30">
                      HIGH PRIORITY OVERDUE
                    </span>
                    <span className="text-xs font-mono text-cat-subtext">EQX1001</span>
                  </div>
                  <h4 className="font-bold text-white text-sm">CAT Excavator 336 — Site S003</h4>
                  <p className="text-xs text-cat-subtext mt-1">Idle Time: 10.0 Hrs/Day | Utilization: 13.0%</p>
                  <div className="mt-3 bg-red-500/10 p-2.5 rounded-lg text-xs text-red-300 flex items-center justify-between">
                    <span>Level 3 Escalated Alert Dispatched</span>
                    <span className="font-bold text-red-400">Action Needed Today</span>
                  </div>
                </div>

                <div className="bg-cat-dark/90 p-4 rounded-xl border border-amber-500/40">
                  <div className="flex justify-between items-start mb-2">
                    <span className="bg-amber-500/20 text-amber-400 text-xs font-bold px-2 py-0.5 rounded border border-amber-500/30">
                      UNDERUTILIZED ASSET
                    </span>
                    <span className="text-xs font-mono text-cat-subtext">EQX1004</span>
                  </div>
                  <h4 className="font-bold text-white text-sm">CAT Grader 140M — Site S004</h4>
                  <p className="text-xs text-cat-subtext mt-1">9.0 Idle Hrs/Day | Reallocation Recommended</p>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-cat-border flex items-center justify-between text-xs text-cat-subtext">
                <span className="flex items-center gap-1.5">
                  <Cpu className="w-4 h-4 text-cat-yellow" /> Automated Anomaly Detection
                </span>
                <span className="font-mono text-white font-bold">100 Rows Loaded</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Grid */}
      <section className="px-6 py-12 bg-cat-card/50 border-t border-cat-border">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-2xl md:text-3xl font-extrabold text-white">Five Core Decision-Driven Engines</h2>
            <p className="text-cat-subtext text-sm mt-2">Built explicitly for Caterpillar dealers, site managers, and rental operations teams.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
            <div className="bg-cat-card p-5 rounded-xl border border-cat-border hover:border-cat-yellow/50 transition-all">
              <div className="w-10 h-10 rounded-lg bg-cat-yellow/10 text-cat-yellow flex items-center justify-between p-2.5 mb-4">
                <Activity className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-white text-base mb-1">1. Action Queue</h3>
              <p className="text-xs text-cat-subtext">Daily operational decision list prioritizing overdue returns & underutilized machinery for today's action.</p>
            </div>

            <div className="bg-cat-card p-5 rounded-xl border border-cat-border hover:border-cat-yellow/50 transition-all">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-between p-2.5 mb-4">
                <Truck className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-white text-base mb-1">2. Available Fleet</h3>
              <p className="text-xs text-cat-subtext">Real-time inventory of unassigned, ready-to-deploy heavy machinery with location & readiness status.</p>
            </div>

            <div className="bg-cat-card p-5 rounded-xl border border-cat-border hover:border-cat-yellow/50 transition-all">
              <div className="w-10 h-10 rounded-lg bg-red-500/10 text-red-400 flex items-center justify-between p-2.5 mb-4">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-white text-base mb-1">3. 5-Level Overdue Alerts</h3>
              <p className="text-xs text-cat-subtext">Tiered delay severity matrix from Level 1 mild reminders up to Level 5 remote engine lockout protocols.</p>
            </div>

            <div className="bg-cat-card p-5 rounded-xl border border-cat-border hover:border-cat-yellow/50 transition-all">
              <div className="w-10 h-10 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-between p-2.5 mb-4">
                <BarChart3 className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-white text-base mb-1">4. Underutilization %</h3>
              <p className="text-xs text-cat-subtext">Productivity mathematical model sorting machines by utilization rate and flagging high idle anomalies.</p>
            </div>

            <div className="bg-cat-card p-5 rounded-xl border border-cat-border hover:border-cat-yellow/50 transition-all">
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-between p-2.5 mb-4">
                <Clock className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-white text-base mb-1">5. Return Schedule</h3>
              <p className="text-xs text-cat-subtext">Chronological datewise schedule tracking equipment return deadlines day-by-day across all active sites.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-cat-border py-6 px-6 text-center text-xs text-cat-subtext">
        <p>Caterpillar Hackathon 2026 — Quarry Masters Team | Smart Asset Rental Tracking System</p>
      </footer>
    </div>
  );
}
