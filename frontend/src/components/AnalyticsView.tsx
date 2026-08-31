import React, { useState, useEffect } from 'react';
import {
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
      <div className="flex items-center justify-center h-full text-[#71717a]">
        <div className="flex items-center gap-2 font-mono text-sm">
          <Activity className="w-4 h-4 animate-spin text-emerald-400" />
          <span>Computing Stored-Data Traffic Analytics...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full max-w-[1600px] mx-auto animate-slide-up">
      {/* Top Banner KPI */}
      <div className="apple-card rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-semibold text-sm text-[#f4f4f5] tracking-tight">
              Urban Traffic Intelligence & Flow Analytics
            </h2>
            <p className="text-xs text-[#8e8e93]">
              Greenshields Density, Hourly Aggregations & Origin-Destination Matrices
            </p>
          </div>
        </div>

        <div className="flex items-center gap-8 font-mono text-xs">
          <div>
            <span className="text-[10px] text-[#8e8e93] uppercase tracking-wider block font-sans">TOTAL VOLUME (24H)</span>
            <span className="text-xl font-bold text-[#f4f4f5]">
              {data.total_vehicles_past_24h.toLocaleString()} Vehicles
            </span>
          </div>
          <div className="border-l border-white/[0.08] pl-8">
            <span className="text-[10px] text-[#8e8e93] uppercase tracking-wider block font-sans">FLOW MODEL</span>
            <span className="text-emerald-400 font-bold">k = q / v_s (Calibrated)</span>
          </div>
        </div>
      </div>

      {/* Hourly Volume Chart */}
      <div className="apple-card rounded-2xl p-5 shadow-xl">
        <div className="flex items-center justify-between pb-3.5 border-b border-white/[0.08]">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            <h3 className="font-semibold text-sm text-[#f4f4f5] tracking-tight">
              24-Hour Traffic Volume Trend by Time Bucket
            </h3>
          </div>
          <span className="text-xs font-mono text-[#8e8e93]">Hourly Throughput</span>
        </div>

        <div className="h-64 mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data.hourly_volume_trend}>
              <defs>
                <linearGradient id="volGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="bucket"
                stroke="#3f3f46"
                tick={{ fill: '#8e8e93', fontSize: 11, fontFamily: 'monospace' }}
              />
              <YAxis
                stroke="#3f3f46"
                tick={{ fill: '#8e8e93', fontSize: 11, fontFamily: 'monospace' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(18, 18, 22, 0.95)',
                  borderColor: 'rgba(255, 255, 255, 0.12)',
                  borderRadius: 12,
                  fontSize: 12,
                  fontFamily: 'monospace',
                  color: '#f4f4f5',
                  boxShadow: '0 10px 30px rgba(0, 0, 0, 0.5)',
                }}
              />
              <Area
                type="monotone"
                dataKey="total"
                stroke="#10b981"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#volGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Grid: Congested Corridors & OD Movement Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
        {/* Left 6 Cols: Top Congested Corridors */}
        <div className="lg:col-span-6 apple-card rounded-2xl p-5 shadow-xl">
          <div className="flex items-center justify-between pb-3.5 border-b border-white/[0.08]">
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-rose-400" />
              <h3 className="font-semibold text-sm text-[#f4f4f5] tracking-tight">
                Top Delay Corridors (Congestion Index)
              </h3>
            </div>
            <span className="text-xs font-mono text-[#8e8e93]">Current vs Baseline</span>
          </div>

          <div className="space-y-3 mt-3.5">
            {(!data.top_congested_corridors || data.top_congested_corridors.length === 0) ? (
              <div className="p-4 text-center rounded-xl apple-subcard text-xs font-mono text-[#8e8e93]">
                All corridors operating smoothly in Free Flow (LOS A).
              </div>
            ) : (
              data.top_congested_corridors.map((c, idx) => (
                <div key={idx} className="apple-subcard p-3.5 rounded-2xl space-y-2 hover:scale-[1.01]">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-[#f4f4f5]">{c.corridor_name}</span>
                    <span className="font-mono text-cyan-400 font-bold">
                      {(c.congestion_index || 1).toFixed(2)}x Delay
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs font-mono text-[#8e8e93]">
                    <div className="flex-1 bg-white/[0.06] h-2 rounded-full overflow-hidden flex">
                      <div
                        className="bg-rose-500 h-full rounded-full"
                        style={{ width: `${Math.min((c.congestion_index || 1) * 40, 100)}%` }}
                      />
                    </div>
                    <span>{c.current_travel_time_s || 0}s (Normal: {c.baseline_travel_time_s || 0}s)</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right 6 Cols: Origin-Destination Matrix */}
        <div className="lg:col-span-6 apple-card rounded-2xl p-5 shadow-xl">
          <div className="flex items-center justify-between pb-3.5 border-b border-white/[0.08]">
            <div className="flex items-center gap-2">
              <Compass className="w-4 h-4 text-cyan-400" />
              <h3 className="font-semibold text-sm text-[#f4f4f5] tracking-tight">
                Origin-Destination (OD) Matrix
              </h3>
            </div>
            <span className="text-xs font-mono text-[#8e8e93]">Zone Movement Counts</span>
          </div>

          <div className="space-y-2.5 mt-3.5">
            {(!data.top_od_flows || data.top_od_flows.length === 0) ? (
              <div className="p-4 text-center rounded-xl apple-subcard text-xs font-mono text-[#8e8e93]">
                No cross-zone trip matrices recorded yet.
              </div>
            ) : (
              data.top_od_flows.map((od: any, idx: number) => {
                const origin = od.origin_zone || od.origin_camera_name || 'Origin Zone';
                const dest = od.destination_zone || od.destination_camera_name || 'Destination Zone';
                const trips = od.trip_count ?? 0;
                const duration = od.avg_travel_time_s ?? od.average_duration_seconds ?? 0;

                return (
                  <div
                    key={idx}
                    className="apple-subcard p-3 rounded-xl flex items-center justify-between text-xs font-mono hover:scale-[1.01]"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2 text-[#f4f4f5] font-semibold">
                        <span>{origin}</span>
                        <ArrowRight className="w-3.5 h-3.5 text-emerald-400" />
                        <span>{dest}</span>
                      </div>
                      <span className="text-[10px] text-[#8e8e93]">
                        Avg Travel Time: {Math.round(duration / 60)} mins
                      </span>
                    </div>

                    <div className="text-right">
                      <span className="text-sm font-bold text-emerald-400">
                        {trips} Trips
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Top Frequent Routes Progression */}
      <div className="apple-card rounded-2xl p-5 shadow-xl">
        <div className="flex items-center justify-between pb-3.5 border-b border-white/[0.08]">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <h3 className="font-semibold text-sm text-[#f4f4f5] tracking-tight">
              Frequently Observed Vehicle Corridors
            </h3>
          </div>
          <span className="text-xs font-mono text-[#8e8e93]">Reconstructed Trajectory Chains</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 mt-3.5">
          {(!data.top_frequent_routes || data.top_frequent_routes.length === 0) ? (
            <div className="col-span-3 p-4 text-center rounded-xl apple-subcard text-xs font-mono text-[#8e8e93]">
              Multi-camera route reconstructions currently building from real-time stream.
            </div>
          ) : (
            data.top_frequent_routes.map((route: any, idx: number) => {
              const sequence: string[] = Array.isArray(route.camera_sequence)
                ? route.camera_sequence
                : Array.isArray(route.route_camera_names)
                ? route.route_camera_names
                : route.route_summary
                ? [route.route_summary]
                : ['Corridor Hub'];
              const count = route.frequency_count ?? route.trip_count ?? 1;
              const duration = route.avg_travel_time_s ?? route.average_duration_seconds ?? 0;

              return (
                <div key={idx} className="apple-subcard p-3.5 rounded-2xl space-y-2 hover:scale-[1.01]">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-emerald-400 font-bold">Rank #{idx + 1}</span>
                    <span className="text-[#f4f4f5] font-bold">{count} vehicles</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {sequence.map((cam, cIdx) => (
                      <React.Fragment key={cIdx}>
                        <span className="px-2 py-0.5 rounded-lg bg-white/[0.06] border border-white/[0.08] text-[11px] font-mono text-emerald-400">
                          {cam}
                        </span>
                        {cIdx < sequence.length - 1 && (
                          <span className="text-[#8e8e93] text-xs">➔</span>
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                  <div className="text-[10px] font-mono text-[#8e8e93]">
                    Avg Corridor Time: {duration}s
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
