import React, { useState, useEffect } from 'react';
import {
  Activity,
  MapPin,
  Search,
  ShieldAlert,
  BarChart3,
  ListOrdered,
  Cpu,
  Radio,
  Clock,
  Terminal
} from 'lucide-react';

export type TabType = 'overview' | 'map' | 'investigate' | 'alerts' | 'analytics' | 'watchlist' | 'benchmark';

interface NavbarProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  onSearch: (query: string) => void;
  activeAlertsCount: number;
  onOpenDiagnostics?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  onSearch,
  activeAlertsCount,
  onOpenDiagnostics,
}) => {
  const [searchInput, setSearchInput] = useState('');
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString('en-US', { hour12: false }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      onSearch(searchInput.trim());
      onTabChange('investigate');
    }
  };

  const navItems: { id: TabType; label: string; icon: React.ReactNode; badge?: number }[] = [
    { id: 'overview', label: 'Overview', icon: <Activity className="w-4 h-4" /> },
    { id: 'map', label: 'Live Map', icon: <MapPin className="w-4 h-4" /> },
    { id: 'investigate', label: 'Vehicle Dossier', icon: <Search className="w-4 h-4" /> },
    {
      id: 'alerts',
      label: 'Alert Center',
      icon: <ShieldAlert className="w-4 h-4" />,
      badge: activeAlertsCount > 0 ? activeAlertsCount : undefined,
    },
    { id: 'analytics', label: 'Analytics', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'watchlist', label: 'Watchlist', icon: <ListOrdered className="w-4 h-4" /> },
    { id: 'benchmark', label: 'Benchmarks', icon: <Cpu className="w-4 h-4" /> },
  ];

  return (
    <header className="bg-[#13131b] border-b border-[#292932] h-14 flex items-center justify-between px-4 z-50 shrink-0 select-none">
      {/* Brand & Title */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-8 h-8 rounded bg-[#8083ff]/20 border border-[#8083ff]/40 text-[#c0c1ff]">
          <Radio className="w-4 h-4 animate-pulse text-[#c0c1ff]" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold tracking-wider text-sm text-[#c0c1ff]">
              CITYTRACK AI
            </span>
            <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-[#1f1f27] border border-[#34343d] text-[#bec6e0]">
              PS 26127
            </span>
          </div>
          <p className="text-[10px] text-[#908fa0] font-mono tracking-tight">
            City-Wide Multi-Camera ANPR Intelligence
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex items-center gap-1">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-all relative cursor-pointer ${
                isActive
                  ? 'bg-[#8083ff]/20 text-[#c0c1ff] border border-[#8083ff]/50 shadow-[0_0_12px_rgba(192,193,255,0.15)]'
                  : 'text-[#908fa0] hover:text-[#e4e1ed] hover:bg-[#1f1f27] border border-transparent'
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
              {item.badge !== undefined && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-[#ffb4ab]/20 text-[#ffb4ab] border border-[#ffb4ab]/40 animate-pulse">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Right Controls: Search & Clock */}
      <div className="flex items-center gap-3">
        <form onSubmit={handleSearchSubmit} className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#908fa0]" />
          <input
            type="text"
            placeholder="Search Plate (e.g. KA01AB1234)..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-56 bg-[#0d0d15] border border-[#292932] rounded pl-8 pr-2.5 py-1 text-xs text-[#e4e1ed] placeholder-[#908fa0] focus:outline-none focus:border-[#8083ff] font-mono transition-colors"
          />
        </form>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#0d0d15] border border-[#292932] text-xs font-mono text-[#c7c4d7]">
          <Clock className="w-3.5 h-3.5 text-[#38bdf8]" />
          <span>{timeStr || '00:00:00'}</span>
          <span className="text-[10px] text-[#908fa0]">UTC</span>
        </div>

        {onOpenDiagnostics && (
          <button
            onClick={onOpenDiagnostics}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#1f1f27] hover:bg-[#292932] border border-[#34343d] text-[#c0c1ff] text-xs font-mono transition-colors cursor-pointer"
            title="Open System Diagnostics & Debug Console"
          >
            <Terminal className="w-3.5 h-3.5 text-[#8083ff]" />
            <span className="font-semibold text-[11px]">Debug</span>
          </button>
        )}

        <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span className="text-[10px] font-semibold tracking-wider">LIVE</span>
        </div>
      </div>
    </header>
  );
};
