import React, { useState } from 'react';
import LandingPage from './components/LandingPage';
import Sidebar from './components/Sidebar';
import AssetDashboard from './components/AssetDashboard';

export default function App() {
  const [currentView, setCurrentView] = useState('landing'); // 'landing' or 'dashboard'
  const [activeTab, setActiveTab] = useState('action-queue'); // 'action-queue', 'available', 'overdue-alerts', 'underutilized', 'datewise-returns'
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isReseeding, setIsReseeding] = useState(false);

  const handleEnterDashboard = () => {
    setCurrentView('dashboard');
    setActiveTab('action-queue');
  };

  const handleTabChange = (tabId) => {
    if (tabId === 'landing') {
      setCurrentView('landing');
    } else {
      setCurrentView('dashboard');
      setActiveTab(tabId);
    }
  };

  const handleReseed = async () => {
    setIsReseeding(true);
    try {
      const res = await fetch('/api/dashboard/reseed', { method: 'POST' });
      const data = await res.json();
      alert(`Success: ${data.message}`);
      window.location.reload();
    } catch (err) {
      alert(`Error reseeding database: ${err.message}`);
    } finally {
      setIsReseeding(false);
    }
  };

  if (currentView === 'landing') {
    return <LandingPage onEnterDashboard={handleEnterDashboard} />;
  }

  return (
    <div className="min-h-screen bg-cat-dark text-slate-100 flex overflow-hidden">
      {/* Side Navigation Bar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={handleTabChange}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
        onReseed={handleReseed}
        isReseeding={isReseeding}
      />

      {/* Main Content View */}
      <main className="flex-1 overflow-y-auto min-h-screen">
        <AssetDashboard
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />
      </main>
    </div>
  );
}
