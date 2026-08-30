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
  Terminal,
  Globe2
} from 'lucide-react';

export type TabType = 'overview' | 'map' | 'investigate' | 'alerts' | 'analytics' | 'watchlist' | 'benchmark';

export const CITIES_LIST = [
  { id: 'All', label: '🇮🇳 Pan-India', fullName: 'National Multi-City Network' },
  { id: 'Bengaluru', label: '🏙️ Bengaluru (KA)', fullName: 'Bengaluru Smart Traffic' },
  { id: 'Delhi NCR', label: '🏛️ Delhi NCR (DL)', fullName: 'Delhi NCR Expressway Network' },
  { id: 'Mumbai', label: '🌊 Mumbai (MH)', fullName: 'Mumbai Coastal & Freeway' },
  { id: 'Hyderabad', label: '💎 Hyderabad (TS)', fullName: 'Hyderabad IT & ORR Corridor' },
  { id: 'Chennai', label: '🏖️ Chennai (TN)', fullName: 'Chennai Arterial & OMR' },
  { id: 'Kolkata', label: '🌉 Kolkata (WB)', fullName: 'Kolkata Bypass & Heritage' },
];

interface NavbarProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  onSearch: (query: string) => void;
  activeAlertsCount: number;
  onOpenDiagnostics?: () => void;
  selectedCity?: string;
  onCityChange?: (city: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  onSearch,
  activeAlertsCount,
  onOpenDiagnostics,
  selectedCity = 'All',
  onCityChange,
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
    { id: 'overview', label: 'Overview', icon: <Activity className="w-3.5 h-3.5" /> },
    { id: 'map', label: 'Live Map', icon: <MapPin className="w-3.5 h-3.5" /> },
    { id: 'investigate', label: 'Investigation', icon: <Search className="w-3.5 h-3.5" /> },
    {
      id: 'alerts',
      label: 'Alerts',
      icon: <ShieldAlert className="w-3.5 h-3.5" />,
      badge: activeAlertsCount > 0 ? activeAlertsCount : undefined,
    },
    { id: 'analytics', label: 'Analytics', icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: 'watchlist', label: 'Watchlist', icon: <ListOrdered className="w-3.5 h-3.5" /> },
    { id: 'benchmark', label: 'Benchmarks', icon: <Cpu className="w-3.5 h-3.5" /> },
  ];

  return (
    <header className="bg-[#0e0e12]/80 backdrop-blur-2xl border-b border-white/[0.08] h-14 flex items-center justify-between px-4 z-50 shrink-0 select-none shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
      {/* Brand & Title with Apple Glass badge */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)] transition-transform hover:scale-105">
          <Radio className="w-4 h-4 text-emerald-400" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-semibold tracking-tight text-sm text-[#f4f4f5]">
              CityTrack <span className="text-emerald-400 font-bold">AI</span>
            </span>
            <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-white/[0.06] border border-white/[0.1] text-[#a1a1aa] tracking-wide">
              PS 26127
            </span>
          </div>
          <p className="text-[10px] text-[#71717a] font-normal tracking-tight">
            Pan-India Multi-Camera Intelligence
          </p>
        </div>
      </div>

      {/* Apple-Style Segmented Tab Bar */}
      <nav className="flex items-center bg-[#15151a]/80 p-1 rounded-xl border border-white/[0.06] backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-300 relative cursor-pointer ${
                isActive
                  ? 'bg-white/[0.12] text-white shadow-[0_2px_10px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.18)] border border-white/[0.12]'
                  : 'text-[#8e8e93] hover:text-[#f4f4f5] hover:bg-white/[0.04] border border-transparent'
              }`}
            >
              <span className={isActive ? 'text-emerald-400' : 'text-[#8e8e93]'}>
                {item.icon}
              </span>
              <span>{item.label}</span>
              {item.badge !== undefined && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[9px] font-bold bg-rose-500/25 text-rose-300 border border-rose-500/40 animate-pulse">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Right Controls: City Selector, Search, Diagnostics, Clock */}
      <div className="flex items-center gap-2">
        {/* City Selector Glass Pill */}
        {onCityChange && (
          <div className="flex items-center gap-1.5 bg-[#18181f]/80 px-2.5 py-1.5 rounded-xl border border-white/[0.08] text-xs backdrop-blur-md shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] transition-all hover:border-white/[0.15]">
            <Globe2 className="w-3.5 h-3.5 text-emerald-400" />
            <select
              value={selectedCity}
              onChange={(e) => onCityChange(e.target.value)}
              className="bg-transparent text-[#f4f4f5] font-medium text-xs focus:outline-none cursor-pointer pr-1"
            >
              {CITIES_LIST.map((c) => (
                <option key={c.id} value={c.id} className="bg-[#121215] text-[#f4f4f5]">
                  {c.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Search Bar */}
        <form onSubmit={handleSearchSubmit} className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#71717a]" />
          <input
            type="text"
            placeholder="Search plate (⌘K)..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-44 bg-[#18181f]/80 border border-white/[0.08] rounded-xl pl-8 pr-2.5 py-1.5 text-xs text-[#f4f4f5] placeholder-[#71717a] focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 transition-all font-mono shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
          />
        </form>

        {/* IST Clock Pill */}
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-[#18181f]/80 border border-white/[0.08] text-xs font-mono text-[#a1a1aa] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
          <Clock className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[#f4f4f5] font-medium">{timeStr || '00:00:00'}</span>
        </div>

        {/* Debug Console Button */}
        {onOpenDiagnostics && (
          <button
            onClick={onOpenDiagnostics}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#18181f]/80 hover:bg-[#22222b] border border-white/[0.08] hover:border-emerald-500/40 text-[#a1a1aa] hover:text-emerald-400 text-xs font-medium transition-all duration-200 cursor-pointer shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] active:scale-95"
            title="Open System Diagnostics & Debug Console"
          >
            <Terminal className="w-3.5 h-3.5 text-emerald-400" />
            <span>Debug</span>
          </button>
        )}

        {/* Live Status Pill */}
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium shadow-[0_0_12px_rgba(16,185,129,0.15)]">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
          <span className="text-[10px] font-bold tracking-wider">LIVE</span>
        </div>
      </div>
    </header>
  );
};
