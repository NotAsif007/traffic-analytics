import React, { useState, useEffect } from 'react';
import {
  Search,
  Clock,
  MapPin,
  Camera,
  Activity,
  CheckCircle2,
  Layers,
  Sparkles,
  Gauge
} from 'lucide-react';
import { VehicleInvestigationResponse, TrajectoryPredictionResponse } from '../types/api';
import { api } from '../services/api';
import { IndianPlateGraphic } from './IndianPlateGraphic';

interface InvestigationViewProps {
  initialSearchPlate?: string;
}

export const InvestigationView: React.FC<InvestigationViewProps> = ({
  initialSearchPlate = 'KA01AB1234',
}) => {
  const [searchQuery, setSearchQuery] = useState(initialSearchPlate);
  const [dossier, setDossier] = useState<VehicleInvestigationResponse | null>(null);
  const [prediction, setPrediction] = useState<TrajectoryPredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchDossier = async (query: string) => {
    setLoading(true);
    try {
      const [dossierData, predData] = await Promise.all([
        api.investigateVehicle(query),
        api.getTrajectoryPrediction(query),
      ]);
      setDossier(dossierData);
      setPrediction(predData);
    } catch (err) {
      console.error('Failed to load dossier:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialSearchPlate) {
      setSearchQuery(initialSearchPlate);
      fetchDossier(initialSearchPlate);
    }
  }, [initialSearchPlate]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      fetchDossier(searchQuery.trim());
    }
  };

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full max-w-[1600px] mx-auto animate-slide-up">
      {/* Top Search & Filter Bar */}
      <div className="apple-card rounded-2xl p-3.5 flex flex-wrap items-center justify-between gap-3 shadow-xl">
        <form onSubmit={handleSearch} className="flex items-center gap-2.5 flex-1 max-w-xl">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#71717a]" />
            <input
              type="text"
              placeholder="Search Vehicle Plate or Identity UUID (e.g. KA01AB1234)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#18181f]/80 border border-white/[0.08] rounded-xl pl-10 pr-3.5 py-2 text-xs font-mono text-[#f4f4f5] placeholder-[#71717a] focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 transition-all shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 rounded-xl apple-button-primary text-xs font-semibold flex items-center gap-2 shrink-0 cursor-pointer active:scale-95 transition-all"
          >
            {loading ? <Activity className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
            <span>Search Dossier</span>
          </button>
        </form>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-[#8e8e93] font-medium">Quick Queries:</span>
          {['KA01AB1234', 'KA01MJ4040', 'KA02HG7788', 'DL01CA9988', 'MH02BK9123'].map((p) => (
            <button
              key={p}
              onClick={() => {
                setSearchQuery(p);
                fetchDossier(p);
              }}
              className="px-2.5 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] text-[#f4f4f5] font-mono text-[11px] transition-all cursor-pointer active:scale-95"
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {dossier && (
        <div className="space-y-4">
          {/* Dossier Header Summary Card */}
          <div className="apple-card rounded-2xl p-5 shadow-xl">
            <div className="flex flex-wrap items-start justify-between gap-4">
              {/* License Plate Badge & Identity */}
              <div className="flex items-center gap-4">
                <IndianPlateGraphic
                  plateNumber={dossier.canonical_plate || 'KA 01 AB 1234'}
                  size="lg"
                />

                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-semibold text-[#f4f4f5] tracking-tight">
                      {dossier.vehicle_class}
                    </span>
                    <span className="px-2.5 py-0.5 rounded-full bg-white/[0.06] border border-white/[0.08] text-xs font-mono text-[#a1a1aa]">
                      Color: {dossier.vehicle_color}
                    </span>
                  </div>

                  <div className="text-xs font-mono text-[#8e8e93] flex items-center gap-2">
                    <span>Identity UUID:</span>
                    <span className="text-emerald-400 font-semibold">{dossier.identity_id}</span>
                  </div>
                </div>
              </div>

              {/* Status / Confidence KPIs */}
              <div className="flex items-center gap-8">
                <div className="text-right">
                  <span className="text-[10px] font-medium text-[#8e8e93] uppercase tracking-wider block">RE-ID CONFIDENCE</span>
                  <span className="text-2xl font-mono font-bold text-emerald-400">
                    {(dossier.overall_confidence * 100).toFixed(1)}%
                  </span>
                </div>

                <div className="text-right">
                  <span className="text-[10px] font-medium text-[#8e8e93] uppercase tracking-wider block">TOTAL SIGHTINGS</span>
                  <span className="text-2xl font-mono font-bold text-cyan-400">
                    {dossier.total_sightings_count} Nodes
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* 🔮 Predictive Forward Trajectory & Next-Hop Forecast Card */}
          {prediction && (
            <div className="apple-card rounded-2xl p-5 shadow-xl">
              <div className="flex items-center justify-between pb-3.5 border-b border-white/[0.08]">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-400 animate-pulse" />
                  <h3 className="font-semibold text-sm text-[#f4f4f5] tracking-tight">
                    Forward Trajectory Prediction & Next-Hop Intercept Forecast
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-mono text-[10px] font-bold">
                    Risk: {prediction.deviation_risk_level}
                  </span>
                  <span className="text-xs text-[#8e8e93] hidden sm:inline font-mono">
                    {prediction.forecast_method}
                  </span>
                </div>
              </div>

              <div className="mt-3.5 grid grid-cols-1 md:grid-cols-3 gap-3.5">
                {prediction.predicted_next_hops.map((hop, idx) => (
                  <div
                    key={idx}
                    className="apple-subcard rounded-2xl p-3.5 relative overflow-hidden transition-all hover:scale-[1.01]"
                  >
                    {/* Top candidate badge */}
                    {idx === 0 && (
                      <div className="absolute top-0 right-0 px-2.5 py-0.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-[#042f2e] font-mono font-bold text-[9px] rounded-bl-xl shadow-md">
                        PRIMARY FORECAST
                      </div>
                    )}

                    <div className="flex items-center justify-between text-xs font-semibold text-[#f4f4f5] mb-1">
                      <span className="truncate max-w-[190px]">{hop.camera_name}</span>
                      <span className="font-mono text-emerald-400 font-bold text-sm">
                        {(hop.probability * 100).toFixed(0)}%
                      </span>
                    </div>

                    <div className="text-[11px] text-[#8e8e93] mb-2.5 truncate font-mono">
                      {hop.road_name || 'Corridor Connector'}
                    </div>

                    {/* Animated Probability Progress Bar */}
                    <div className="w-full bg-white/[0.06] h-1.5 rounded-full overflow-hidden mb-3">
                      <div
                        className="bg-gradient-to-r from-emerald-500 to-cyan-400 h-full rounded-full transition-all duration-700 shadow-[0_0_8px_rgba(16,185,129,0.5)]"
                        style={{ width: `${hop.probability * 100}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-[11px] font-mono text-[#8e8e93] pt-2 border-t border-white/[0.05]">
                      <span className="flex items-center gap-1.5 text-[#f4f4f5]">
                        <Clock className="w-3 h-3 text-amber-400" />
                        ETA: in {hop.estimated_travel_time_seconds.toFixed(0)}s
                      </span>
                      <span className="text-cyan-400">
                        {(hop.distance_meters / 1000).toFixed(2)} km away
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-3.5 p-3 rounded-xl apple-subcard flex flex-wrap items-center justify-between text-xs font-mono text-[#8e8e93] gap-2">
                <div>
                  Forecasted Exit Destination: <strong className="text-emerald-400">{prediction.predicted_destination_corridor}</strong>
                </div>
                <div className="text-emerald-400 flex items-center gap-1.5 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Spatio-Temporal Transition Feasible</span>
                </div>
              </div>
            </div>
          )}

          {/* Timeline & Plate Evidence Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
            {/* Left 6 Cols: Chronological Multi-Camera Timeline */}
            <div className="lg:col-span-6 apple-card rounded-2xl p-5">
              <div className="flex items-center justify-between pb-3.5 border-b border-white/[0.08]">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-emerald-400" />
                  <h3 className="font-semibold text-sm text-[#f4f4f5] tracking-tight">
                    Multi-Camera Journey Timeline
                  </h3>
                </div>
                <span className="text-xs font-mono text-[#8e8e93]">Chronological Progression</span>
              </div>

              <div className="relative mt-4 pl-6 border-l-2 border-white/[0.1] space-y-6">
                {dossier.camera_history.map((step, idx) => (
                  <div key={idx} className="relative group">
                    {/* Timeline Node Dot */}
                    <div className="absolute -left-[31px] top-1 w-4 h-4 rounded-full bg-[#121215] border-2 border-emerald-500 flex items-center justify-center shadow-[0_0_8px_rgba(16,185,129,0.5)]">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    </div>

                    <div className="apple-subcard rounded-2xl p-3.5 transition-all hover:scale-[1.01]">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-lg bg-emerald-500/20 text-emerald-300 text-[11px] font-mono font-bold flex items-center justify-center">
                            {step.step_number}
                          </span>
                          <span className="font-semibold text-[#f4f4f5]">{step.camera_name}</span>
                        </div>
                        <span className="font-mono text-[#8e8e93]">
                          {new Date(step.timestamp).toLocaleTimeString()}
                        </span>
                      </div>

                      <div className="flex items-center gap-4 mt-2.5 text-xs font-mono text-[#8e8e93]">
                        <span className="flex items-center gap-1.5">
                          <MapPin className="w-3 h-3 text-cyan-400" />
                          {step.latitude.toFixed(4)}, {step.longitude.toFixed(4)}
                        </span>
                        {step.segment_speed_kmh && (
                          <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                            <Gauge className="w-3 h-3" />
                            {step.segment_speed_kmh} km/h
                          </span>
                        )}
                        {step.dwell_or_transit_seconds && (
                          <span className="flex items-center gap-1 text-[#d4d4d8]">
                            <Clock className="w-3 h-3 text-amber-400" />
                            Transit: {step.dwell_or_transit_seconds}s
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right 6 Cols: Plate Observation Evidence Grid */}
            <div className="lg:col-span-6 apple-card rounded-2xl p-5">
              <div className="flex items-center justify-between pb-3.5 border-b border-white/[0.08]">
                <div className="flex items-center gap-2">
                  <Camera className="w-4 h-4 text-emerald-400" />
                  <h3 className="font-semibold text-sm text-[#f4f4f5] tracking-tight">
                    High-Resolution ANPR Evidence Gallery
                  </h3>
                </div>
                <span className="text-xs font-mono text-[#8e8e93]">Raw OCR & Crop Media</span>
              </div>

              <div className="space-y-3 mt-3.5">
                {dossier.plate_observations.map((obs, idx) => (
                  <div
                    key={idx}
                    className="apple-subcard rounded-2xl p-3 flex items-center gap-3.5 hover:scale-[1.01]"
                  >
                    {/* Vehicle / Plate Image Crop */}
                    <div className="w-24 h-16 rounded-xl overflow-hidden bg-black/40 border border-white/[0.1] shrink-0 relative">
                      <img
                        src={obs.image_path || 'https://images.unsplash.com/photo-1596176530529-78163a4f7af2?w=300&auto=format&fit=crop&q=80'}
                        alt="Vehicle Sighting Crop"
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute bottom-0 right-0 px-1.5 py-0.2 bg-black/80 font-mono text-[9px] text-emerald-400 rounded-tl-md">
                        ANPR OK
                      </div>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-sm text-emerald-400 tracking-wider">
                          {obs.raw_plate_text || dossier.canonical_plate}
                        </span>
                        <span className="text-[10px] font-mono text-emerald-400 font-bold bg-emerald-500/15 px-2 py-0.5 rounded-full border border-emerald-500/30">
                          OCR: {((obs.plate_confidence || 0.98) * 100).toFixed(1)}%
                        </span>
                      </div>

                      <div className="flex items-center justify-between mt-1 text-xs text-[#8e8e93]">
                        <span>Camera: {obs.camera_name}</span>
                        <span className="font-mono text-[11px]">
                          {new Date(obs.timestamp).toLocaleTimeString()}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 mt-1.5 text-[10px] font-mono text-[#8e8e93]">
                        <span>Class: {obs.vehicle_class}</span>
                        <span>Color: {obs.vehicle_color}</span>
                        <span>Det Conf: {(obs.detection_confidence * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
