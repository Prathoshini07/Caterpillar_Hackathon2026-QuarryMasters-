import React, { useState } from 'react';
import LandingPage from './components/LandingPage';
import Sidebar from './components/Sidebar';
import AssetDashboard from './components/AssetDashboard';
import UserPortal from './components/UserPortal';
import HistoryPortal from './components/HistoryPortal';
import AnomalyDetection from './components/AnomalyDetection';
import OptimizationPortal from './components/OptimizationPortal';

export default function App() {
  const [currentView, setCurrentView] = useState('landing'); // 'landing' or 'dashboard'
  const [activeTab, setActiveTab] = useState('action-queue'); // all tab IDs
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isReseeding, setIsReseeding] = useState(false);
  const [showPortal, setShowPortal] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

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

  return (
    <>
      {/* User Portal Modal — available from any view */}
      {showPortal && <UserPortal onClose={() => setShowPortal(false)} />}

      {/* History Modal */}
      {showHistory && <HistoryPortal onClose={() => setShowHistory(false)} />}

      {currentView === 'landing' ? (
        <LandingPage
          onEnterDashboard={handleEnterDashboard}
          onOpenPortal={() => setShowPortal(true)}
          onOpenHistory={() => setShowHistory(true)}
        />
      ) : (
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
            {activeTab === 'anomaly-detection' ? (
              <div className="p-6">
                <AnomalyDetection />
              </div>
            ) : activeTab === 'optimization' ? (
              <div className="p-6">
                <OptimizationPortal />
              </div>
            ) : (
              <AssetDashboard
                activeTab={activeTab}
                setActiveTab={setActiveTab}
              />
            )}
          </main>
        </div>
      )}
    </>
  );
}
