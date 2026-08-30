import React, { useState, useEffect } from 'react';
import { Navbar, TabType } from './components/Navbar';
import { OverviewView } from './components/OverviewView';
import { MapView } from './components/MapView';
import { InvestigationView } from './components/InvestigationView';
import { AlertsView } from './components/AlertsView';
import { AnalyticsView } from './components/AnalyticsView';
import { WatchlistView } from './components/WatchlistView';
import { BenchmarkView } from './components/BenchmarkView';
import { DiagnosticsModal } from './components/DiagnosticsModal';
import { CityOverviewResponse, LiveMapResponse } from './types/api';
import { api } from './services/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [searchPlate, setSearchPlate] = useState<string>('KA01AB1234');
  const [overviewData, setOverviewData] = useState<CityOverviewResponse | null>(null);
  const [mapData, setMapData] = useState<LiveMapResponse | null>(null);
  const [diagnosticsOpen, setDiagnosticsOpen] = useState<boolean>(false);

  // Poll overview and map telemetry
  const refreshData = async () => {
    try {
      const [overview, map] = await Promise.all([
        api.getCityOverview(),
        api.getLiveMap(),
      ]);
      setOverviewData(overview);
      setMapData(map);
    } catch (err) {
      console.error('Error refreshing telemetry:', err);
    }
  };

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 15000); // 15s live refresh
    return () => clearInterval(interval);
  }, []);

  const handleSearch = (plate: string) => {
    setSearchPlate(plate);
    setActiveTab('investigate');
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[#0b0f19] text-[#e4e1ed] overflow-hidden">
      {/* Top Fixed Navbar */}
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onSearch={handleSearch}
        activeAlertsCount={overviewData?.active_alerts_count || 0}
        onOpenDiagnostics={() => setDiagnosticsOpen(true)}
      />

      {/* Main Active Tab Content View */}
      <main className="flex-1 overflow-hidden relative">
        {activeTab === 'overview' && (
          <OverviewView
            data={overviewData}
            onNavigate={setActiveTab}
            onSearchPlate={handleSearch}
          />
        )}
        {activeTab === 'map' && (
          <MapView
            data={mapData}
            onSelectVehicle={handleSearch}
          />
        )}
        {activeTab === 'investigate' && (
          <InvestigationView
            initialSearchPlate={searchPlate}
          />
        )}
        {activeTab === 'alerts' && <AlertsView />}
        {activeTab === 'analytics' && <AnalyticsView />}
        {activeTab === 'watchlist' && <WatchlistView />}
        {activeTab === 'benchmark' && <BenchmarkView />}
      </main>

      {/* Developer Diagnostics & Telemetry Modal */}
      <DiagnosticsModal
        isOpen={diagnosticsOpen}
        onClose={() => setDiagnosticsOpen(false)}
      />
    </div>
  );
};

export default App;
