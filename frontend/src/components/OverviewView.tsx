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
  Layers
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
      <div className="flex items-center justify-center h-full text-[#908fa0]">
        <div className="flex items-center gap-2 font-mono text-sm">
          <Radio className="w-4 h-4 animate-spin text-[#c0c1ff]" />
          <span>Synchronizing Operations Telemetry...</span>
        </div>
      </div>
    );
  }

  const getTrafficColor = (level: string) => {
    switch (level) {
      case 'low':
        return 'text-emerald-400 bg-emerald-950/30 border-emerald-500/30';
      case 'moderate':
        return 'text-amber-400 bg-amber-950/30 border-amber-500/30';
      case 'heavy':
      case 'congested':
        return 'text-rose-400 bg-rose-950/30 border-rose-500/30';
      default:
        return 'text-[#c7c4d7] bg-[#1b1b23] border-[#292932]';
    }
  };

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full max-w-[1600px] mx-auto">
      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Card 1: Active Cameras */}
        <div className="bg-[#13131b] border border-[#292932] rounded p-3.5 flex flex-col justify-between relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono tracking-wider font-semibold text-[#908fa0] uppercase">
              CAMERA NETWORK
            </span>
            <div className="p-1.5 rounded bg-[#8083ff]/10 text-[#c0c1ff]">
              <Camera className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-[#e4e1ed]">
              {data.active_cameras_count} / {data.total_cameras_count}
            </span>
            <span className="text-xs font-mono text-emerald-400 font-medium">
              {data.cameras_online_percentage}% Online
            </span>
          </div>
          <div className="mt-2 w-full bg-[#1b1b23] h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-[#38bdf8] h-full rounded-full transition-all"
              style={{ width: `${data.cameras_online_percentage}%` }}
            />
          </div>
        </div>

        {/* Card 2: Vehicles Observed Today */}
        <div className="bg-[#13131b] border border-[#292932] rounded p-3.5 flex flex-col justify-between relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono tracking-wider font-semibold text-[#908fa0] uppercase">
              OBSERVATIONS TODAY
            </span>
            <div className="p-1.5 rounded bg-emerald-500/10 text-emerald-400">
              <Car className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-[#e4e1ed]">
              {data.vehicles_observed_today.toLocaleString()}
            </span>
            <span className="text-xs font-mono text-[#908fa0]">sightings</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5 text-[11px] text-[#c7c4d7]">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
            <span>High-Throughput ANPR Stream Active</span>
          </div>
        </div>

        {/* Card 3: Network Traffic Status */}
        <div className="bg-[#13131b] border border-[#292932] rounded p-3.5 flex flex-col justify-between relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono tracking-wider font-semibold text-[#908fa0] uppercase">
              NETWORK CONGESTION
            </span>
            <div className="p-1.5 rounded bg-amber-500/10 text-amber-400">
              <Flame className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span
              className={`px-2 py-0.5 rounded text-xs font-mono font-bold uppercase border ${getTrafficColor(
                data.current_traffic_level
              )}`}
            >
              {data.current_traffic_level}
            </span>
            <span className="text-xs text-[#908fa0] font-mono">
              {data.congestion_hotspots.length} Hotspots
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px] text-[#908fa0]">
            <span>Greenshields Flow Model</span>
            <button
              onClick={() => onNavigate('analytics')}
              className="text-[#c0c1ff] hover:underline flex items-center gap-0.5 cursor-pointer"
            >
              Analytics <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Card 4: Active Alerts */}
        <div className="bg-[#13131b] border border-[#292932] rounded p-3.5 flex flex-col justify-between relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono tracking-wider font-semibold text-[#908fa0] uppercase">
              ACTIVE ALERTS
            </span>
            <div className="p-1.5 rounded bg-rose-500/10 text-rose-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-rose-400">
              {data.active_alerts_count}
            </span>
            {data.critical_alerts_count > 0 && (
              <span className="text-xs font-mono text-rose-400 font-bold px-1.5 py-0.5 rounded bg-rose-950/50 border border-rose-500/40 animate-pulse">
                {data.critical_alerts_count} Critical
              </span>
            )}
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px]">
            <span className="text-[#908fa0]">Zero Unacknowledged</span>
            <button
              onClick={() => onNavigate('alerts')}
              className="text-rose-400 hover:underline flex items-center gap-0.5 cursor-pointer font-medium"
            >
              Review Alerts <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Congestion Hotspots & Live Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Left 7 Cols: Congestion Hotspots */}
        <div className="lg:col-span-7 bg-[#13131b] border border-[#292932] rounded p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-[#292932]">
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-amber-400" />
                <h3 className="font-semibold text-sm text-[#e4e1ed]">
                  Active Congestion Hotspots & Corridors
                </h3>
              </div>
              <span className="text-xs font-mono text-[#908fa0]">
                Baseline vs Real-Time Travel Delay
              </span>
            </div>

            <div className="divide-y divide-[#1f1f27] mt-2">
              {data.congestion_hotspots.length === 0 ? (
                <div className="py-8 text-center text-[#908fa0] text-xs font-mono">
                  No abnormal corridor congestion detected. All roads operating in Free Flow.
                </div>
              ) : (
                data.congestion_hotspots.map((hotspot, idx) => (
                  <div key={idx} className="py-3 flex flex-col gap-2">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-[#e4e1ed]">
                          {hotspot.corridor_name}
                        </span>
                        <span
                          className={`text-[10px] font-mono uppercase px-1.5 py-0.2 rounded font-bold ${
                            hotspot.severity === 'severe'
                              ? 'bg-rose-950/40 text-rose-400 border border-rose-500/30'
                              : 'bg-amber-950/40 text-amber-400 border border-amber-500/30'
                          }`}
                        >
                          {hotspot.severity}
                        </span>
                      </div>
                      <span className="font-mono text-[#c0c1ff] font-bold">
                        {hotspot.congestion_index.toFixed(2)}x Normal Delay
                      </span>
                    </div>

                    {/* Progress Comparison */}
                    <div className="flex items-center gap-3 text-[11px] font-mono text-[#908fa0]">
                      <div className="flex-1 bg-[#1b1b23] h-2 rounded-full overflow-hidden flex">
                        <div
                          className="bg-emerald-500 h-full"
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
                      <span>
                        Current: <strong className="text-[#e4e1ed]">{hotspot.current_travel_time_s}s</strong> (Baseline:{' '}
                        {hotspot.baseline_travel_time_s}s)
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[#292932] flex items-center justify-between text-xs text-[#908fa0]">
            <span className="flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Spatio-Temporal Road Graph Enabled
            </span>
            <button
              onClick={() => onNavigate('map')}
              className="text-[#c0c1ff] hover:underline flex items-center gap-1 cursor-pointer font-medium"
            >
              View on Geospatial Map <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right 5 Cols: Live Activity Feed */}
        <div className="lg:col-span-5 bg-[#13131b] border border-[#292932] rounded p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-[#292932]">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-[#38bdf8]" />
                <h3 className="font-semibold text-sm text-[#e4e1ed]">
                  Live Activity & Security Feed
                </h3>
              </div>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/50 px-1.5 py-0.5 rounded border border-emerald-500/30">
                REAL-TIME STREAM
              </span>
            </div>

            <div className="space-y-3 mt-3">
              {data.recent_activity.map((item, idx) => (
                <div
                  key={idx}
                  className="bg-[#1b1b23] border border-[#292932] rounded p-2.5 flex items-start gap-2.5 transition-colors hover:border-[#464554]"
                >
                  <div
                    className={`p-1.5 rounded shrink-0 ${
                      item.severity === 'critical'
                        ? 'bg-rose-950/50 text-rose-400 border border-rose-500/40'
                        : item.severity === 'high'
                        ? 'bg-amber-950/50 text-amber-400 border border-amber-500/40'
                        : 'bg-[#8083ff]/10 text-[#c0c1ff] border border-[#8083ff]/30'
                    }`}
                  >
                    {item.severity === 'critical' ? (
                      <AlertTriangle className="w-4 h-4" />
                    ) : item.activity_type === 'TRAJECTORY' ? (
                      <Layers className="w-4 h-4" />
                    ) : (
                      <Radio className="w-4 h-4" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold text-[#e4e1ed] truncate">
                        {item.title}
                      </h4>
                      <span className="text-[10px] font-mono text-[#908fa0] shrink-0 ml-2">
                        {new Date(item.timestamp).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#c7c4d7] mt-0.5 line-clamp-2">
                      {item.description}
                    </p>
                    {item.camera_name && (
                      <div className="mt-1.5 flex items-center justify-between text-[10px] font-mono">
                        <span className="text-[#908fa0]">Location: {item.camera_name}</span>
                        {item.title.includes('KA') && (
                          <button
                            onClick={() => onSearchPlate('KA01MJ4040')}
                            className="text-[#38bdf8] hover:underline cursor-pointer"
                          >
                            Investigate Vehicle ➔
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[#292932] flex items-center justify-between text-xs text-[#908fa0]">
            <span>Continuous Redis Event Bus Coordinator</span>
            <button
              onClick={() => onNavigate('alerts')}
              className="text-[#c0c1ff] hover:underline flex items-center gap-1 cursor-pointer font-medium"
            >
              All Security Alerts <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Quick Launchpad & Architecture Strip */}
      <div className="bg-[#13131b] border border-[#292932] rounded p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[#908fa0] font-semibold uppercase text-[10px] tracking-wider">
            QUICK ACCESS:
          </span>
          <button
            onClick={() => onNavigate('map')}
            className="px-2.5 py-1 rounded bg-[#1f1f27] hover:bg-[#292932] border border-[#34343d] text-[#e4e1ed] transition-colors cursor-pointer"
          >
            🗺️ Live City GIS Map
          </button>
          <button
            onClick={() => onSearchPlate('KA01AB1234')}
            className="px-2.5 py-1 rounded bg-[#1f1f27] hover:bg-[#292932] border border-[#34343d] text-[#e4e1ed] transition-colors cursor-pointer"
          >
            🔍 Law Enforcement Vehicle Dossier
          </button>
          <button
            onClick={() => onNavigate('watchlist')}
            className="px-2.5 py-1 rounded bg-[#1f1f27] hover:bg-[#292932] border border-[#34343d] text-[#e4e1ed] transition-colors cursor-pointer"
          >
            📋 Blacklist & Stolen Watchlist
          </button>
          <button
            onClick={() => onNavigate('benchmark')}
            className="px-2.5 py-1 rounded bg-[#1f1f27] hover:bg-[#292932] border border-[#34343d] text-[#e4e1ed] transition-colors cursor-pointer"
          >
            📊 Scientific Benchmarking
          </button>
        </div>

        <div className="flex items-center gap-2 font-mono text-[11px] text-[#908fa0]">
          <span>FastAPI + PostGIS + ByteTrack + Redis PubSub</span>
        </div>
      </div>
    </div>
  );
};
