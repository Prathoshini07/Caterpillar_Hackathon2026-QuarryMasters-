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
              CATERPILLAR RENTAL TRACKING SYSTEM
            </h1>
            <p className="text-xs text-cat-subtext">Intelligent Heavy Machinery Fleet Optimization</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">

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
              SMART ASSET RENTAL MANAGEMENT
            </div>

            <h1 className="text-4xl md:text-6xl font-black tracking-tight leading-none text-white">
              CATERPILLAR RENTAL <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cat-yellow via-amber-400 to-yellow-200">
                TRACKING SYSTEM
              </span>
            </h1>

            <p className="text-slate-300 text-lg md:text-xl font-normal leading-relaxed max-w-2xl">
              The complete solution for tracking heavy machinery rentals, monitoring asset utilization, and managing site operations efficiently.
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
                <div className="text-2xl md:text-3xl font-black text-amber-400 font-mono">&gt; 50%</div>
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


            </div>
          </div>

          {/* Machinery Image */}
          <div className="lg:col-span-5">
            <div className="rounded-2xl border border-cat-yellow/30 shadow-2xl overflow-hidden relative">
              <img src="/caterpillar_fleet.png" alt="Caterpillar Fleet" className="w-full h-auto object-cover opacity-90 hover:opacity-100 transition-opacity" />
              <div className="absolute inset-0 bg-gradient-to-t from-cat-dark/80 via-transparent to-transparent"></div>
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
