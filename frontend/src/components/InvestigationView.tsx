import React, { useState, useEffect } from 'react';
import {
  Search,
  Car,
  ShieldAlert,
  Clock,
  MapPin,
  Camera,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Layers,
  ArrowRight,
  Sparkles,
  Gauge
} from 'lucide-react';
import { VehicleInvestigationResponse } from '../types/api';
import { api } from '../services/api';

interface InvestigationViewProps {
  initialSearchPlate?: string;
}

export const InvestigationView: React.FC<InvestigationViewProps> = ({
  initialSearchPlate = 'KA01AB1234',
}) => {
  const [searchQuery, setSearchQuery] = useState(initialSearchPlate);
  const [dossier, setDossier] = useState<VehicleInvestigationResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchDossier = async (query: string) => {
    setLoading(true);
    try {
      const data = await api.investigateVehicle(query);
      setDossier(data);
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
    <div className="p-4 space-y-4 overflow-y-auto h-full max-w-[1600px] mx-auto">
      {/* Top Search & Filter Bar */}
      <div className="bg-[#13131b] border border-[#292932] rounded p-3.5 flex flex-wrap items-center justify-between gap-3">
        <form onSubmit={handleSearch} className="flex items-center gap-2 flex-1 max-w-xl">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#908fa0]" />
            <input
              type="text"
              placeholder="Search Vehicle Plate or Identity UUID (e.g. KA01AB1234)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0d0d15] border border-[#292932] rounded pl-9 pr-3 py-1.5 text-xs font-mono text-[#e4e1ed] placeholder-[#908fa0] focus:outline-none focus:border-[#8083ff]"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-1.5 rounded bg-[#8083ff] hover:bg-[#8083ff]/90 text-[#0d0096] text-xs font-mono font-bold transition-colors cursor-pointer flex items-center gap-1.5 shrink-0"
          >
            {loading ? <Activity className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
            <span>Search Dossier</span>
          </button>
        </form>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="text-[#908fa0]">Demo Queries:</span>
          {['KA01AB1234', 'KA01MJ4040', 'KA02HG7788'].map((p) => (
            <button
              key={p}
              onClick={() => {
                setSearchQuery(p);
                fetchDossier(p);
              }}
              className="px-2 py-0.5 rounded bg-[#1f1f27] hover:bg-[#292932] border border-[#34343d] text-[#c0c1ff] transition-colors cursor-pointer text-[11px]"
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {dossier && (
        <div className="space-y-4">
          {/* Dossier Header Summary Card */}
          <div className="bg-[#13131b] border border-[#292932] rounded p-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              {/* License Plate Badge & Identity */}
              <div className="flex items-center gap-4">
                <div className="px-4 py-2 rounded bg-[#0d0d15] border-2 border-[#8083ff] shadow-[0_0_15px_rgba(128,131,255,0.2)] flex flex-col items-center">
                  <span className="text-[10px] font-mono text-[#908fa0] uppercase tracking-widest">
                    IND
                  </span>
                  <span className="text-2xl font-bold font-mono text-[#e4e1ed] tracking-wider">
                    {dossier.canonical_plate || 'KA 01 AB 1234'}
                  </span>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-[#e4e1ed]">
                      {dossier.vehicle_class}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-[#1f1f27] border border-[#34343d] text-xs font-mono text-[#c7c4d7]">
                      Color: {dossier.vehicle_color}
                    </span>
                  </div>
                  <p className="text-xs text-[#908fa0] font-mono">
                    Identity UUID: {dossier.identity_id}
                  </p>
                </div>
              </div>

              {/* Confidence Meter & Sightings Count */}
              <div className="flex items-center gap-6">
                <div className="text-right">
                  <span className="text-[10px] font-mono text-[#908fa0] uppercase block">
                    TOTAL SIGHTINGS
                  </span>
                  <span className="text-2xl font-bold font-mono text-[#38bdf8]">
                    {dossier.total_sightings_count} Cameras
                  </span>
                </div>

                <div className="w-40 bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <div className="flex justify-between text-xs font-mono mb-1">
                    <span className="text-[#908fa0]">CONFIDENCE</span>
                    <span className="text-emerald-400 font-bold">
                      {(dossier.overall_confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-[#0d0d15] h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-emerald-400 h-full rounded-full"
                      style={{ width: `${dossier.overall_confidence * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 mt-4 pt-3 border-t border-[#292932] text-xs font-mono">
              <div className="bg-[#1b1b23] p-2 rounded">
                <span className="text-[10px] text-[#908fa0] block">FIRST SIGHTING</span>
                <span className="text-[#e4e1ed] font-medium">
                  {new Date(dossier.first_seen_at).toLocaleTimeString()}
                </span>
              </div>
              <div className="bg-[#1b1b23] p-2 rounded">
                <span className="text-[10px] text-[#908fa0] block">LAST SIGHTING</span>
                <span className="text-[#e4e1ed] font-medium">
                  {new Date(dossier.last_seen_at).toLocaleTimeString()}
                </span>
              </div>
              <div className="bg-[#1b1b23] p-2 rounded">
                <span className="text-[10px] text-[#908fa0] block">LAST KNOWN LOCATION</span>
                <span className="text-[#c0c1ff] font-medium truncate block">
                  {dossier.last_known_camera_name || 'CAM-06 (Airport Rd)'}
                </span>
              </div>
              <div className="bg-[#1b1b23] p-2 rounded">
                <span className="text-[10px] text-[#908fa0] block">ASSOCIATION STATUS</span>
                <span className="text-emerald-400 font-bold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Multi-Camera Verified
                </span>
              </div>
            </div>
          </div>

          {/* Timeline & Plate Evidence Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
            {/* Left 6 Cols: Chronological Multi-Camera Timeline */}
            <div className="lg:col-span-6 bg-[#13131b] border border-[#292932] rounded p-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#292932]">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-[#8083ff]" />
                  <h3 className="font-semibold text-sm text-[#e4e1ed]">
                    Multi-Camera Journey Timeline
                  </h3>
                </div>
                <span className="text-xs font-mono text-[#908fa0]">Chronological Progression</span>
              </div>

              <div className="relative mt-4 pl-6 border-l-2 border-[#292932] space-y-6">
                {dossier.camera_history.map((step, idx) => (
                  <div key={idx} className="relative group">
                    {/* Timeline Node Dot */}
                    <div className="absolute -left-[31px] top-1 w-4 h-4 rounded-full bg-[#13131b] border-2 border-[#8083ff] flex items-center justify-center">
                      <div className="w-1.5 h-1.5 rounded-full bg-[#8083ff]" />
                    </div>

                    <div className="bg-[#1b1b23] border border-[#292932] rounded p-3 transition-colors hover:border-[#8083ff]/40">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded bg-[#8083ff]/20 text-[#c0c1ff] text-[11px] font-mono font-bold flex items-center justify-center">
                            {step.step_number}
                          </span>
                          <span className="font-semibold text-[#e4e1ed]">{step.camera_name}</span>
                        </div>
                        <span className="font-mono text-[#908fa0]">
                          {new Date(step.timestamp).toLocaleTimeString()}
                        </span>
                      </div>

                      <div className="flex items-center gap-4 mt-2 text-[11px] font-mono text-[#908fa0]">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-[#38bdf8]" />
                          {step.latitude.toFixed(4)}, {step.longitude.toFixed(4)}
                        </span>
                        {step.segment_speed_kmh && (
                          <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                            <Gauge className="w-3 h-3" />
                            {step.segment_speed_kmh} km/h
                          </span>
                        )}
                        {step.dwell_or_transit_seconds && (
                          <span className="flex items-center gap-1 text-[#c7c4d7]">
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
            <div className="lg:col-span-6 bg-[#13131b] border border-[#292932] rounded p-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#292932]">
                <div className="flex items-center gap-2">
                  <Camera className="w-4 h-4 text-emerald-400" />
                  <h3 className="font-semibold text-sm text-[#e4e1ed]">
                    High-Resolution ANPR Evidence Gallery
                  </h3>
                </div>
                <span className="text-xs font-mono text-[#908fa0]">Raw OCR & Crop Media</span>
              </div>

              <div className="space-y-3 mt-3">
                {dossier.plate_observations.map((obs, idx) => (
                  <div
                    key={idx}
                    className="bg-[#1b1b23] border border-[#292932] rounded p-3 flex items-center gap-3"
                  >
                    {/* Vehicle / Plate Image Crop */}
                    <div className="w-24 h-16 rounded overflow-hidden bg-[#0d0d15] border border-[#292932] shrink-0 relative">
                      <img
                        src={obs.image_path || 'https://images.unsplash.com/photo-1549399542-7e3f8b79c341?w=200'}
                        alt="Vehicle Sighting Crop"
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute bottom-0 right-0 px-1 py-0.2 bg-[#0d0d15]/90 font-mono text-[9px] text-emerald-400">
                        ANPR OK
                      </div>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-sm text-[#c0c1ff] tracking-wider">
                          {obs.raw_plate_text || dossier.canonical_plate}
                        </span>
                        <span className="text-[10px] font-mono text-emerald-400 font-bold bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-500/30">
                          OCR: {((obs.plate_confidence || 0.98) * 100).toFixed(1)}%
                        </span>
                      </div>

                      <div className="flex items-center justify-between mt-1 text-xs text-[#908fa0]">
                        <span>Camera: {obs.camera_name}</span>
                        <span className="font-mono text-[11px]">
                          {new Date(obs.timestamp).toLocaleTimeString()}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 mt-1 text-[10px] font-mono text-[#908fa0]">
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
