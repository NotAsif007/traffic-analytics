import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import {
  Camera,
  Car,
  AlertTriangle,
  Radio,
  Globe2
} from 'lucide-react';
import { LiveMapResponse, MapCameraNode } from '../types/api';
import { CCTVStreamPlayer } from './CCTVStreamPlayer';

// Fix for default Leaflet icon paths in React
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const CITY_COORDINATES: Record<string, { center: [number, number]; zoom: number }> = {
  All: { center: [21.5, 78.9629], zoom: 5 },
  Bengaluru: { center: [12.9716, 77.5946], zoom: 12 },
  'Delhi NCR': { center: [28.5700, 77.2200], zoom: 12 },
  Mumbai: { center: [19.0400, 72.8400], zoom: 12 },
  Hyderabad: { center: [17.4400, 78.3700], zoom: 12 },
  Chennai: { center: [13.0200, 80.2400], zoom: 12 },
  Kolkata: { center: [22.5600, 88.3700], zoom: 12 },
};

// Map Viewport Controller for Smooth FlyTo Transitions
const MapPanController: React.FC<{ selectedCity: string }> = ({ selectedCity }) => {
  const map = useMap();
  useEffect(() => {
    const target = CITY_COORDINATES[selectedCity] || CITY_COORDINATES.All;
    map.flyTo(target.center, target.zoom, { duration: 1.4, easeLinearity: 0.25 });
  }, [selectedCity, map]);
  return null;
};

// Custom camera marker icons
const createCameraIcon = (intensity: string, hasAlert: boolean) => {
  const color = hasAlert ? '#ef4444' : intensity === 'high' ? '#06b6d4' : intensity === 'moderate' ? '#f59e0b' : '#10b981';
  return L.divIcon({
    className: 'custom-camera-marker',
    html: `
      <div style="position: relative; display: flex; align-items: center; justify-content: center; width: 30px; height: 30px; background: rgba(18, 18, 24, 0.95); border: 2px solid ${color}; border-radius: 50%; box-shadow: 0 0 16px ${color}90, inset 0 1px 0 rgba(255,255,255,0.2);">
        <div style="width: 8px; height: 8px; background: ${color}; border-radius: 50%;"></div>
        ${hasAlert ? `<div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; border: 2px solid #ef4444; animation: pulse-ring 1.5s infinite;"></div>` : ''}
      </div>
    `,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
};

interface MapViewProps {
  data: LiveMapResponse | null;
  onSelectVehicle: (plate: string) => void;
  selectedCity?: string;
  onCityChange?: (city: string) => void;
}

export const MapView: React.FC<MapViewProps> = ({
  data,
  onSelectVehicle,
  selectedCity = 'All',
}) => {
  const [selectedCamera, setSelectedCamera] = useState<MapCameraNode | null>(null);
  const [showTrajectories, setShowTrajectories] = useState(true);
  const [showAlerts, setShowAlerts] = useState(true);

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-[#71717a]">
        <div className="flex items-center gap-2 font-mono text-sm">
          <Radio className="w-4 h-4 animate-spin text-emerald-400" />
          <span>Rendering Pan-India Geospatial Map Layers...</span>
        </div>
      </div>
    );
  }

  const initialView = CITY_COORDINATES[selectedCity] || CITY_COORDINATES.All;

  return (
    <div className="relative w-full h-full flex overflow-hidden animate-fade-in">
      {/* Floating Apple Glass Control Bar Overlay */}
      <div className="absolute top-4 left-4 z-[1000] apple-glass rounded-2xl p-3 flex flex-wrap items-center gap-3.5 text-xs shadow-2xl">
        <div className="flex items-center gap-2 font-medium text-white border-r border-white/[0.1] pr-3">
          <Globe2 className="w-4 h-4 text-emerald-400" />
          <span>{selectedCity === 'All' ? 'Pan-India Network' : selectedCity}</span>
        </div>

        <label className="flex items-center gap-2 cursor-pointer text-[#f4f4f5] font-medium select-none">
          <input
            type="checkbox"
            checked={showTrajectories}
            onChange={(e) => setShowTrajectories(e.target.checked)}
            className="rounded-md bg-white/[0.08] border-white/[0.15] text-emerald-500 focus:ring-0 w-3.5 h-3.5 cursor-pointer"
          />
          <span>Trajectories ({data.active_trajectories.length})</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer text-[#f4f4f5] font-medium select-none">
          <input
            type="checkbox"
            checked={showAlerts}
            onChange={(e) => setShowAlerts(e.target.checked)}
            className="rounded-md bg-white/[0.08] border-white/[0.15] text-rose-500 focus:ring-0 w-3.5 h-3.5 cursor-pointer"
          />
          <span className="text-rose-400">Alerts ({data.active_alerts.length})</span>
        </label>

        <div className="flex items-center gap-2.5 pl-2.5 border-l border-white/[0.1] text-xs font-mono text-[#8e8e93]">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> Low
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> Moderate
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400" /> High
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-500" /> Alert
          </span>
        </div>
      </div>

      {/* Main Map Container */}
      <div className="flex-1 h-full w-full">
        <MapContainer
          center={initialView.center}
          zoom={initialView.zoom}
          style={{ width: '100%', height: '100%' }}
          zoomControl={false}
        >
          <MapPanController selectedCity={selectedCity} />

          {/* Esri World Dark Gray Base Tile Layer */}
          <TileLayer
            attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
            maxZoom={16}
          />
          <TileLayer
            attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}"
            maxZoom={16}
          />

          {/* Road Network Lines */}
          {data.road_segments.map((road) => {
            const coords = (road.geometry_geojson.coordinates as number[][]).map(
              (c) => [c[1], c[0]] as [number, number]
            );
            const color =
              road.current_congestion_index > 1.8
                ? '#ef4444'
                : road.current_congestion_index > 1.3
                ? '#f59e0b'
                : '#10b981';
            return (
              <Polyline
                key={road.id}
                positions={coords}
                pathOptions={{
                  color,
                  weight: 4,
                  opacity: 0.85,
                  lineCap: 'round',
                }}
              >
                <Popup className="custom-popup">
                  <div className="p-2 space-y-1 text-[#f4f4f5] font-sans">
                    <div className="font-bold text-xs text-emerald-400">{road.name}</div>
                    <div className="text-xs font-mono text-[#a1a1aa]">
                      Congestion Index: <strong className="text-amber-400">{road.current_congestion_index.toFixed(2)}x</strong>
                    </div>
                  </div>
                </Popup>
              </Polyline>
            );
          })}

          {/* Active Trajectories Polylines (Tech Cyan) */}
          {showTrajectories &&
            data.active_trajectories.map((traj) => (
              <Polyline
                key={traj.trajectory_id}
                positions={traj.coordinates}
                pathOptions={{
                  color: '#06b6d4',
                  weight: 3.5,
                  dashArray: '6, 8',
                  opacity: 0.95,
                }}
              >
                <Popup className="custom-popup">
                  <div className="p-3 space-y-2 text-[#f4f4f5] font-sans">
                    <div className="flex items-center gap-2 text-xs font-bold text-cyan-400">
                      <Car className="w-4 h-4" />
                      <span>{traj.canonical_plate || 'Unidentified Vehicle'}</span>
                    </div>
                    <div className="text-xs font-mono text-[#a1a1aa]">
                      Class: <strong className="text-[#f4f4f5]">{traj.vehicle_class || 'car'}</strong>
                    </div>
                    {traj.current_speed_kmh && (
                      <div className="text-xs font-mono text-[#a1a1aa]">
                        Est. Speed: <strong className="text-emerald-400">{traj.current_speed_kmh.toFixed(1)} km/h</strong>
                      </div>
                    )}
                    <button
                      onClick={() => onSelectVehicle(traj.canonical_plate || '')}
                      className="mt-2 w-full py-1.5 px-3 rounded-xl apple-button-primary text-xs font-semibold transition-all cursor-pointer"
                    >
                      Investigate Dossier
                    </button>
                  </div>
                </Popup>
              </Polyline>
            ))}

          {/* Security Alert Pins */}
          {showAlerts &&
            data.active_alerts.map((alert) => (
              <Marker
                key={alert.alert_id || alert.id}
                position={[alert.latitude, alert.longitude]}
                icon={L.divIcon({
                  className: 'custom-alert-marker',
                  html: `
                    <div style="width: 26px; height: 26px; background: #ef4444; border: 2px solid #ffffff; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 16px #ef4444; animation: bounce 1s infinite;">
                      <span style="color: white; font-size: 12px; font-weight: bold;">!</span>
                    </div>
                  `,
                  iconSize: [26, 26],
                  iconAnchor: [13, 13],
                })}
              >
                <Popup className="custom-popup">
                  <div className="p-3 space-y-1.5 text-[#f4f4f5] font-sans">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-rose-400">
                      <AlertTriangle className="w-4 h-4" />
                      <span>{alert.alert_code}: {alert.alert_type}</span>
                    </div>
                    <p className="text-xs text-[#a1a1aa] leading-tight">{alert.description || alert.title}</p>
                    <div className="text-[11px] font-mono text-rose-300">
                      Severity: <strong className="uppercase">{alert.severity}</strong>
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}

          {/* Camera Nodes */}
          {data.cameras.map((cam) => {
            const hasAlert = data.active_alerts.some(
              (a) => a.camera_name === cam.name
            );
            return (
              <Marker
                key={cam.id}
                position={[cam.latitude, cam.longitude]}
                icon={createCameraIcon(cam.current_intensity, hasAlert)}
                eventHandlers={{
                  click: () => setSelectedCamera(cam),
                }}
              >
                <Popup className="custom-popup">
                  <div className="p-3 space-y-1.5 text-[#f4f4f5] font-sans">
                    <div className="flex items-center gap-2 font-bold text-xs text-emerald-400">
                      <Camera className="w-4 h-4" />
                      <span>{cam.name}</span>
                    </div>
                    <div className="text-xs text-[#a1a1aa] font-mono">
                      Hourly Sightings: <strong className="text-[#f4f4f5]">{cam.observations_last_hour}</strong>
                    </div>
                    <div className="text-xs text-[#71717a] font-mono">
                      GPS: {cam.latitude.toFixed(4)}, {cam.longitude.toFixed(4)}
                    </div>
                    {hasAlert && (
                      <div className="p-1.5 rounded-xl bg-rose-500/20 border border-rose-500/50 text-rose-400 font-semibold text-xs flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5" /> Security Alert Active
                      </div>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>

      {/* Right Telemetry Drawer with Apple Glass sliding transition */}
      {selectedCamera && (
        <div className="w-[440px] max-w-[95vw] apple-glass border-l border-white/[0.1] p-5 flex flex-col justify-between z-[1000] overflow-y-auto shadow-2xl shrink-0 animate-scale-in">
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  <Camera className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-[#f4f4f5] leading-tight">{selectedCamera.name}</h3>
                  <span className="text-[10px] font-mono text-[#8e8e93]">SENSOR: {selectedCamera.id.substring(0, 13)}...</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedCamera(null)}
                className="w-7 h-7 rounded-full bg-white/[0.08] hover:bg-white/[0.15] text-[#a1a1aa] hover:text-[#f4f4f5] flex items-center justify-center cursor-pointer text-xs transition-all active:scale-90"
                title="Close Drawer"
              >
                ✕
              </button>
            </div>

            {/* Live CCTV Stream Player with Tabs */}
            <CCTVStreamPlayer
              cameraName={selectedCamera.name}
              cameraId={selectedCamera.id}
              intensity={selectedCamera.current_intensity}
              observationsPerHour={selectedCamera.observations_last_hour}
            />

            {/* Camera Metrics Grid */}
            <div className="grid grid-cols-2 gap-2.5 text-xs">
              <div className="apple-subcard p-3 rounded-2xl">
                <span className="text-[10px] font-medium text-[#8e8e93] uppercase block">Throughput Rate</span>
                <div className="flex items-baseline gap-1.5 mt-1">
                  <span className="text-lg font-mono font-bold text-[#f4f4f5]">
                    {selectedCamera.observations_last_hour}
                  </span>
                  <span className="text-xs text-[#8e8e93]">veh/hr</span>
                </div>
              </div>

              <div className="apple-subcard p-3 rounded-2xl">
                <span className="text-[10px] font-medium text-[#8e8e93] uppercase block">Traffic Intensity</span>
                <div className="flex items-baseline gap-1.5 mt-1">
                  <span className="text-lg font-bold text-cyan-400 uppercase">
                    {selectedCamera.current_intensity}
                  </span>
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                </div>
              </div>
            </div>

            {/* Coordinates & Technical Specs Card */}
            <div className="space-y-2 text-xs font-mono apple-subcard p-3.5 rounded-2xl">
              <div className="flex justify-between py-1 border-b border-white/[0.05] text-[#8e8e93]">
                <span>GPS Latitude:</span>
                <span className="text-[#f4f4f5] font-semibold">{selectedCamera.latitude.toFixed(5)}° N</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/[0.05] text-[#8e8e93]">
                <span>GPS Longitude:</span>
                <span className="text-[#f4f4f5] font-semibold">{selectedCamera.longitude.toFixed(5)}° E</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/[0.05] text-[#8e8e93]">
                <span>Heading:</span>
                <span className="text-emerald-400 font-semibold">BIDIRECTIONAL</span>
              </div>
              <div className="flex justify-between py-1 text-[#8e8e93]">
                <span>Hardware State:</span>
                <span className="text-emerald-400 font-bold uppercase flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  {selectedCamera.status}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-white/[0.08]">
            <button
              onClick={() => setSelectedCamera(null)}
              className="w-full py-2.5 rounded-xl bg-white/[0.08] hover:bg-white/[0.12] text-xs font-semibold text-[#f4f4f5] transition-all cursor-pointer active:scale-95"
            >
              Close Camera View
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
