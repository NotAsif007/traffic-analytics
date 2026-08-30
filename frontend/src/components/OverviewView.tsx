import React from 'react';
import {
  Camera,
  Car,
  AlertTriangle,
  Flame,
  ArrowRight,
  ShieldCheck,
  TrendingUp,
  Radio,
  Clock,
  Layers,
  CheckCircle2
} from 'lucide-react';
import { CityOverviewResponse } from '../types/api';
import { TabType } from './Navbar';

interface OverviewViewProps {
  data: CityOverviewResponse | null;
  onNavigate: (tab: TabType) => void;
  onSearchPlate: (plate: string) => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  data,
  onNavigate,
  onSearchPlate,
}) => {
  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-[#71717a]">
        <div className="flex items-center gap-2 font-mono text-sm">
          <Radio className="w-4 h-4 animate-spin text-emerald-400" />
          <span>Synchronizing Operations Telemetry...</span>
        </div>
      </div>
    );
  }

  const getTrafficColor = (level: string) => {
    switch (level) {
      case 'low':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
      case 'moderate':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
      case 'heavy':
      case 'congested':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
      default:
        return 'text-[#a1a1aa] bg-white/[0.04] border-white/[0.08]';
    }
  };

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full max-w-[1600px] mx-auto animate-slide-up">
      {/* KPI Cards Row (Apple-grade Frosted Glass Cards) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* Card 1: Camera Network */}
        <div className="apple-card rounded-2xl p-4 flex flex-col justify-between relative group cursor-default">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium tracking-wider text-[#8e8e93] uppercase">
              CAMERA NETWORK
            </span>
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 group-hover:scale-110 transition-transform">
              <Camera className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold tracking-tight text-[#f4f4f5] font-mono">
              {data.active_cameras_count} / {data.total_cameras_count}
            </span>
            <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              {data.cameras_online_percentage}% Online
            </span>
          </div>
          <div className="mt-3 w-full bg-white/[0.06] h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-emerald-500 to-cyan-400 h-full rounded-full transition-all duration-700 shadow-[0_0_8px_rgba(16,185,129,0.5)]"
              style={{ width: `${data.cameras_online_percentage}%` }}
            />
          </div>
        </div>

        {/* Card 2: Vehicles Observed Today */}
        <div className="apple-card rounded-2xl p-4 flex flex-col justify-between relative group cursor-default">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium tracking-wider text-[#8e8e93] uppercase">
              OBSERVATIONS TODAY
            </span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 group-hover:scale-110 transition-transform">
              <Car className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold tracking-tight text-[#f4f4f5] font-mono">
              {data.vehicles_observed_today.toLocaleString()}
            </span>
            <span className="text-xs text-[#8e8e93]">sightings</span>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-xs text-[#a1a1aa]">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
            <span>ANPR Pipeline Active</span>
          </div>
        </div>

        {/* Card 3: Network Traffic Status */}
        <div className="apple-card rounded-2xl p-4 flex flex-col justify-between relative group cursor-default">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium tracking-wider text-[#8e8e93] uppercase">
              NETWORK CONGESTION
            </span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 group-hover:scale-110 transition-transform">
              <Flame className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between">
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase border ${getTrafficColor(
                data.current_traffic_level
              )}`}
            >
              {data.current_traffic_level}
            </span>
            <span className="text-xs text-[#8e8e93] font-mono">
              {data.congestion_hotspots.length} Hotspots
            </span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-[#8e8e93]">
            <span>Greenshields Model</span>
            <button
              onClick={() => onNavigate('analytics')}
              className="text-emerald-400 hover:text-emerald-300 flex items-center gap-0.5 cursor-pointer font-medium transition-colors"
            >
              Analytics <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Card 4: Active Alerts */}
        <div className="apple-card rounded-2xl p-4 flex flex-col justify-between relative group cursor-default">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium tracking-wider text-[#8e8e93] uppercase">
              SECURITY ALERTS
            </span>
            <div className="p-2 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20 group-hover:scale-110 transition-transform">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold tracking-tight text-rose-400 font-mono">
              {data.active_alerts_count}
            </span>
            {data.critical_alerts_count > 0 ? (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-300 animate-pulse">
                {data.critical_alerts_count} Critical
              </span>
            ) : (
              <span className="text-xs font-medium text-emerald-400">0 Critical</span>
            )}
          </div>
          <div className="mt-3 flex items-center justify-between text-xs">
            <span className="text-[#8e8e93]">Security Engine</span>
            <button
              onClick={() => onNavigate('alerts')}
              className="text-rose-400 hover:text-rose-300 flex items-center gap-0.5 cursor-pointer font-medium transition-colors"
            >
              Review Alerts <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Congestion Hotspots & Live Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
        {/* Left 7 Cols: Congestion Hotspots */}
        <div className="lg:col-span-7 apple-card rounded-2xl p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-amber-400" />
                <h3 className="font-semibold text-xs text-[#f4f4f5] tracking-tight">
                  Active Congestion Hotspots & Corridors
                </h3>
              </div>
              <span className="text-[10px] font-mono text-[#8e8e93]">
                Baseline vs Real-Time Delay
              </span>
            </div>

            <div className="mt-3">
              {data.congestion_hotspots.length === 0 ? (
                /* Free Flow State */
                <div className="space-y-2.5">
                  <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span className="text-xs font-semibold text-emerald-400 tracking-tight">
                        NETWORK OPTIMAL (LOS A) — 0 Bottlenecks Detected
                      </span>
                    </div>
                    <span className="text-[10px] text-[#8e8e93] font-mono">Free Flow</span>
                  </div>

                  {/* Corridor Chips */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    <div className="p-2.5 rounded-xl apple-subcard flex items-center justify-between hover:scale-[1.01]">
                      <span className="text-[#f4f4f5] truncate font-medium">MG Road Trinity Corridor</span>
                      <span className="text-emerald-400 font-bold text-xs ml-2 shrink-0 font-mono">48 km/h</span>
                    </div>
                    <div className="p-2.5 rounded-xl apple-subcard flex items-center justify-between hover:scale-[1.01]">
                      <span className="text-[#f4f4f5] truncate font-medium">Silk Board - Electronic City</span>
                      <span className="text-emerald-400 font-bold text-xs ml-2 shrink-0 font-mono">72 km/h</span>
                    </div>
                    <div className="p-2.5 rounded-xl apple-subcard flex items-center justify-between hover:scale-[1.01]">
                      <span className="text-[#f4f4f5] truncate font-medium">Outer Ring Road (AIIMS - Nehru)</span>
                      <span className="text-emerald-400 font-bold text-xs ml-2 shrink-0 font-mono">56 km/h</span>
                    </div>
                    <div className="p-2.5 rounded-xl apple-subcard flex items-center justify-between hover:scale-[1.01]">
                      <span className="text-[#f4f4f5] truncate font-medium">Western Express Hwy (Bandra)</span>
                      <span className="text-emerald-400 font-bold text-xs ml-2 shrink-0 font-mono">64 km/h</span>
                    </div>
                  </div>
                </div>
              ) : (
                /* Active Hotspots List */
                <div className="divide-y divide-white/[0.06]">
                  {data.congestion_hotspots.map((hotspot, idx) => (
                    <div key={idx} className="py-3 flex flex-col gap-2">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-[#f4f4f5]">
                            {hotspot.corridor_name}
                          </span>
                          <span
                            className={`text-[9px] uppercase px-2 py-0.5 rounded-full font-bold ${
                              hotspot.severity === 'severe'
                                ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                                : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            }`}
                          >
                            {hotspot.severity}
                          </span>
                        </div>
                        <span className="font-mono text-cyan-400 font-bold">
                          {hotspot.congestion_index.toFixed(2)}x Delay
                        </span>
                      </div>

                      {/* Progress Comparison */}
                      <div className="flex items-center gap-2.5 text-xs font-mono text-[#8e8e93]">
                        <div className="flex-1 bg-white/[0.06] h-1.5 rounded-full overflow-hidden flex">
                          <div
                            className="bg-emerald-500 h-full rounded-full"
                            style={{
                              width: `${Math.min(
                                (hotspot.baseline_travel_time_s / hotspot.current_travel_time_s) *
                                  100,
                                100
                              )}%`,
                            }}
                          />
                          <div className="bg-rose-500 h-full flex-1" />
                        </div>
                        <span className="text-[11px]">
                          <strong className="text-[#f4f4f5]">{hotspot.current_travel_time_s}s</strong> (Baseline:{' '}
                          {hotspot.baseline_travel_time_s}s)
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-white/[0.08] flex items-center justify-between text-xs text-[#8e8e93]">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Spatio-Temporal Graph Active
            </span>
            <button
              onClick={() => onNavigate('map')}
              className="text-emerald-400 hover:text-emerald-300 flex items-center gap-1 cursor-pointer font-medium transition-colors"
            >
              View on Map <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Right 5 Cols: Live Activity Feed */}
        <div className="lg:col-span-5 apple-card rounded-2xl p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                <h3 className="font-semibold text-xs text-[#f4f4f5] tracking-tight">
                  Live Activity & Security Feed
                </h3>
              </div>
              <span className="text-[9px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/30">
                LIVE STREAM
              </span>
            </div>

            <div className="space-y-2 mt-3 max-h-[210px] overflow-y-auto pr-1">
              {data.recent_activity.map((item, idx) => (
                <div
                  key={idx}
                  className="apple-subcard rounded-xl p-2.5 flex items-center gap-2.5 hover:scale-[1.01]"
                >
                  <div
                    className={`p-2 rounded-xl shrink-0 ${
                      item.severity === 'critical'
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                        : item.severity === 'high'
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                        : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {item.severity === 'critical' ? (
                      <AlertTriangle className="w-3.5 h-3.5" />
                    ) : item.activity_type === 'TRAJECTORY' ? (
                      <Layers className="w-3.5 h-3.5" />
                    ) : (
                      <Radio className="w-3.5 h-3.5" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold text-[#f4f4f5] truncate">
                        {item.title}
                      </h4>
                      <span className="text-[10px] font-mono text-[#8e8e93] shrink-0 ml-2">
                        {new Date(item.timestamp).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#a1a1aa] truncate mt-0.5">
                      {item.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-white/[0.08] flex items-center justify-between text-xs text-[#8e8e93]">
            <span>Redis Event Stream</span>
            <button
              onClick={() => onNavigate('alerts')}
              className="text-emerald-400 hover:text-emerald-300 flex items-center gap-1 cursor-pointer font-medium transition-colors"
            >
              All Alerts <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Quick Launchpad Strip */}
      <div className="apple-card rounded-2xl p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-[#8e8e93] font-semibold uppercase text-[10px] tracking-wider">
            QUICK ACCESS:
          </span>
          <button
            onClick={() => onNavigate('map')}
            className="px-3 py-1 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-[#f4f4f5] font-medium transition-all cursor-pointer text-xs active:scale-95"
          >
            🗺️ GIS Map
          </button>
          <button
            onClick={() => onSearchPlate('KA01AB1234')}
            className="px-3 py-1 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-[#f4f4f5] font-medium transition-all cursor-pointer text-xs active:scale-95"
          >
            🔍 Vehicle Dossier
          </button>
          <button
            onClick={() => onNavigate('watchlist')}
            className="px-3 py-1 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-[#f4f4f5] font-medium transition-all cursor-pointer text-xs active:scale-95"
          >
            📋 Watchlist
          </button>
          <button
            onClick={() => onNavigate('benchmark')}
            className="px-3 py-1 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-[#f4f4f5] font-medium transition-all cursor-pointer text-xs active:scale-95"
          >
            📊 Benchmarks
          </button>
        </div>

        <div className="font-mono text-[11px] text-[#71717a]">
          FastAPI • PostGIS • YOLOv8 • ByteTrack • Redis PubSub
        </div>
      </div>
    </div>
  );
};
