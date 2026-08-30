import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import {
  BarChart3,
  TrendingUp,
  Activity,
  Flame,
  ArrowRight,
  ShieldCheck,
  CheckCircle,
  Clock,
  Compass
} from 'lucide-react';
import { DashboardAnalyticsSummaryResponse } from '../types/api';
import { api } from '../services/api';

export const AnalyticsView: React.FC = () => {
  const [data, setData] = useState<DashboardAnalyticsSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadAnalytics = async () => {
      try {
        const res = await api.getAnalyticsSummary();
        setData(res);
      } catch (err) {
        console.error('Failed to load analytics:', err);
      } finally {
        setLoading(false);
      }
    };
    loadAnalytics();
  }, []);

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-full text-[#908fa0]">
        <div className="flex items-center gap-2 font-mono text-sm">
          <Activity className="w-4 h-4 animate-spin text-[#c0c1ff]" />
          <span>Computing Pure Stored-Data Traffic Analytics...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full max-w-[1600px] mx-auto">
      {/* Top Banner KPI */}
      <div className="bg-[#13131b] border border-[#292932] rounded p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-[#8083ff]/10 text-[#c0c1ff]">
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-bold text-sm text-[#e4e1ed]">
              Urban Traffic Intelligence & Fundamental Flow Analytics
            </h2>
            <p className="text-xs font-mono text-[#908fa0]">
              Greenshields Density, Hourly Aggregations & Origin-Destination Matrices
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6 font-mono text-xs">
          <div>
            <span className="text-[10px] text-[#908fa0] uppercase block">TOTAL VOLUME (24H)</span>
            <span className="text-lg font-bold text-[#e4e1ed]">
              {data.total_vehicles_past_24h.toLocaleString()} Vehicles
            </span>
          </div>
          <div className="border-l border-[#292932] pl-6">
            <span className="text-[10px] text-[#908fa0] uppercase block">FLOW MODEL</span>
            <span className="text-emerald-400 font-bold">k = q / v_s (Calibrated)</span>
          </div>
        </div>
      </div>

      {/* Hourly Volume Chart */}
      <div className="bg-[#13131b] border border-[#292932] rounded p-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#292932]">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-[#38bdf8]" />
            <h3 className="font-semibold text-sm text-[#e4e1ed]">
              24-Hour Traffic Volume Trend by Time Bucket
            </h3>
          </div>
          <span className="text-xs font-mono text-[#908fa0]">Hourly Throughput</span>
        </div>

        <div className="h-64 mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data.hourly_volume_trend}>
              <defs>
                <linearGradient id="volGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8083ff" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#8083ff" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="bucket"
                stroke="#464554"
                tick={{ fill: '#908fa0', fontSize: 11, fontFamily: 'monospace' }}
              />
              <YAxis
                stroke="#464554"
                tick={{ fill: '#908fa0', fontSize: 11, fontFamily: 'monospace' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#13131b',
                  borderColor: '#292932',
                  borderRadius: 6,
                  fontSize: 12,
                  fontFamily: 'monospace',
                }}
              />
              <Area
                type="monotone"
                dataKey="total"
                stroke="#8083ff"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#volGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Grid: Congested Corridors & OD Movement Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Left 6 Cols: Top Congested Corridors */}
        <div className="lg:col-span-6 bg-[#13131b] border border-[#292932] rounded p-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#292932]">
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-rose-400" />
              <h3 className="font-semibold text-sm text-[#e4e1ed]">
                Top Delay Corridors (Congestion Index)
              </h3>
            </div>
            <span className="text-xs font-mono text-[#908fa0]">Current vs Baseline</span>
          </div>

          <div className="space-y-3 mt-3">
            {data.top_congested_corridors.map((c, idx) => (
              <div key={idx} className="bg-[#1b1b23] p-3 rounded border border-[#292932] space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-[#e4e1ed]">{c.corridor_name}</span>
                  <span className="font-mono text-[#c0c1ff] font-bold">
                    {c.congestion_index.toFixed(2)}x Delay
                  </span>
                </div>
                <div className="flex items-center gap-3 text-[11px] font-mono text-[#908fa0]">
                  <div className="flex-1 bg-[#0d0d15] h-2 rounded-full overflow-hidden flex">
                    <div
                      className="bg-rose-500 h-full"
                      style={{ width: `${Math.min(c.congestion_index * 40, 100)}%` }}
                    />
                  </div>
                  <span>{c.current_travel_time_s}s (Normal: {c.baseline_travel_time_s}s)</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right 6 Cols: Origin-Destination Matrix */}
        <div className="lg:col-span-6 bg-[#13131b] border border-[#292932] rounded p-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#292932]">
            <div className="flex items-center gap-2">
              <Compass className="w-4 h-4 text-[#38bdf8]" />
              <h3 className="font-semibold text-sm text-[#e4e1ed]">
                Origin-Destination (OD) Matrix
              </h3>
            </div>
            <span className="text-xs font-mono text-[#908fa0]">Zone Movement Counts</span>
          </div>

          <div className="space-y-2.5 mt-3">
            {data.top_od_flows.map((od, idx) => (
              <div
                key={idx}
                className="bg-[#1b1b23] p-3 rounded border border-[#292932] flex items-center justify-between text-xs font-mono"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5 text-[#e4e1ed] font-semibold">
                    <span>{od.origin_zone}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-[#8083ff]" />
                    <span>{od.destination_zone}</span>
                  </div>
                  <span className="text-[10px] text-[#908fa0]">
                    Avg Travel Time: {Math.round(od.avg_travel_time_s / 60)} mins
                  </span>
                </div>

                <div className="text-right">
                  <span className="text-sm font-bold text-[#c0c1ff]">
                    {od.trip_count} Trips
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Frequent Routes Progression */}
      <div className="bg-[#13131b] border border-[#292932] rounded p-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#292932]">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <h3 className="font-semibold text-sm text-[#e4e1ed]">
              Frequently Observed Vehicle Corridors
            </h3>
          </div>
          <span className="text-xs font-mono text-[#908fa0]">Reconstructed Trajectory Chains</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
          {data.top_frequent_routes.map((route, idx) => (
            <div key={idx} className="bg-[#1b1b23] p-3 rounded border border-[#292932] space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-emerald-400 font-bold">Rank #{idx + 1}</span>
                <span className="text-[#e4e1ed] font-bold">{route.frequency_count} vehicles</span>
              </div>
              <div className="flex flex-wrap items-center gap-1">
                {route.camera_sequence.map((cam, cIdx) => (
                  <React.Fragment key={cIdx}>
                    <span className="px-1.5 py-0.5 rounded bg-[#0d0d15] border border-[#292932] text-[11px] font-mono text-[#c0c1ff]">
                      {cam}
                    </span>
                    {cIdx < route.camera_sequence.length - 1 && (
                      <span className="text-[#908fa0] text-xs">➔</span>
                    )}
                  </React.Fragment>
                ))}
              </div>
              <div className="text-[10px] font-mono text-[#908fa0]">
                Avg Corridor Time: {route.avg_travel_time_s}s
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
