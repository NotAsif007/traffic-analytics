import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';
import {
  Camera,
  Activity,
  Car,
  AlertTriangle,
  Info,
  Radio,
  Eye,
  Sliders
} from 'lucide-react';
import { LiveMapResponse, MapCameraNode } from '../types/api';

// Fix for default Leaflet icon paths in React
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom camera marker icons
const createCameraIcon = (intensity: string, hasAlert: boolean) => {
  const color = hasAlert ? '#ef4444' : intensity === 'high' ? '#38bdf8' : intensity === 'moderate' ? '#f59e0b' : '#10b981';
  return L.divIcon({
    className: 'custom-camera-marker',
    html: `
      <div style="position: relative; display: flex; align-items: center; justify-content: center; width: 28px; height: 28px; background: #13131b; border: 2px solid ${color}; border-radius: 50%; box-shadow: 0 0 10px ${color}80;">
        <div style="width: 8px; height: 8px; background: ${color}; border-radius: 50%;"></div>
        ${hasAlert ? `<div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; border: 2px solid #ef4444; animation: pulse-ring 1.5s infinite;"></div>` : ''}
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

interface MapViewProps {
  data: LiveMapResponse | null;
  onSelectVehicle: (plate: string) => void;
}

export const MapView: React.FC<MapViewProps> = ({ data, onSelectVehicle }) => {
  const [selectedCamera, setSelectedCamera] = useState<MapCameraNode | null>(null);
  const [showTrajectories, setShowTrajectories] = useState(true);
  const [showAlerts, setShowAlerts] = useState(true);

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-[#908fa0]">
        <div className="flex items-center gap-2 font-mono text-sm">
          <Radio className="w-4 h-4 animate-spin text-[#c0c1ff]" />
          <span>Rendering Geospatial Map Layers...</span>
        </div>
      </div>
    );
  }

  // Bangalore center default
  const defaultCenter: [number, number] = [12.9716, 77.5946];

  return (
    <div className="relative w-full h-full flex overflow-hidden">
      {/* Map Control Bar Overlay */}
      <div className="absolute top-3 left-3 z-[1000] bg-[#13131b]/90 backdrop-blur-md border border-[#292932] rounded p-2.5 flex items-center gap-3 text-xs shadow-2xl">
        <div className="flex items-center gap-1.5 font-mono text-[#c0c1ff] font-semibold border-r border-[#292932] pr-3">
          <Activity className="w-4 h-4 text-[#38bdf8]" />
          <span>GIS LAYERS</span>
        </div>

        <label className="flex items-center gap-1.5 cursor-pointer text-[#e4e1ed] font-medium">
          <input
            type="checkbox"
            checked={showTrajectories}
            onChange={(e) => setShowTrajectories(e.target.checked)}
            className="rounded bg-[#0d0d15] border-[#292932] text-[#8083ff] focus:ring-0 w-3.5 h-3.5"
          />
          <span>Active Trajectories ({data.active_trajectories.length})</span>
        </label>

        <label className="flex items-center gap-1.5 cursor-pointer text-[#e4e1ed] font-medium">
          <input
            type="checkbox"
            checked={showAlerts}
            onChange={(e) => setShowAlerts(e.target.checked)}
            className="rounded bg-[#0d0d15] border-[#292932] text-rose-500 focus:ring-0 w-3.5 h-3.5"
          />
          <span className="text-rose-400">Security Alerts ({data.active_alerts.length})</span>
        </label>

        <div className="flex items-center gap-2 pl-2 border-l border-[#292932] text-[11px] font-mono text-[#908fa0]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> Low
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> Moderate
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[#38bdf8]" /> High
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-rose-500" /> Alert
          </span>
        </div>
      </div>

      {/* Main Map Container */}
      <div className="flex-1 h-full w-full">
        <MapContainer
          center={defaultCenter}
          zoom={13}
          style={{ width: '100%', height: '100%' }}
          zoomControl={false}
        >
          {/* CartoDB Dark Matter Tile Layer */}
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* Road Network Lines */}
          {data.road_segments.map((road) => {
            const coords = (road.geometry_geojson.coordinates as number[][]).map(
              (c) => [c[1], c[0]] as [number, number]
            );
            const color =
              road.current_congestion_index > 1.8
                ? '#f43f5e'
                : road.current_congestion_index > 1.3
                ? '#f59e0b'
                : '#3b82f6';
            return (
              <Polyline
                key={road.id}
                positions={coords}
                pathOptions={{ color, weight: 4, opacity: 0.7, dashArray: '4, 4' }}
              />
            );
          })}

          {/* Active Vehicle Trajectories */}
          {showTrajectories &&
            data.active_trajectories.map((traj) => {
              const positions = traj.coordinates.map((c) => [c[1], c[0]] as [number, number]);
              return (
                <React.Fragment key={traj.trajectory_id}>
                  <Polyline
                    positions={positions}
                    pathOptions={{ color: '#c0c1ff', weight: 4, opacity: 0.9 }}
                  />
                  {positions.length > 0 && (
                    <Marker
                      position={positions[positions.length - 1]}
                      icon={L.divIcon({
                        className: 'vehicle-plate-pill',
                        html: `<div style="background: #13131b; color: #c0c1ff; border: 1px solid #8083ff; font-family: monospace; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.8); white-space: nowrap; transform: translate(-50%, -100%); cursor: pointer;">🚗 ${traj.canonical_plate || 'KA01AB1234'}</div>`,
                        iconSize: [80, 20],
                      })}
                      eventHandlers={{
                        click: () => traj.canonical_plate && onSelectVehicle(traj.canonical_plate),
                      }}
                    />
                  )}
                </React.Fragment>
              );
            })}

          {/* Camera Node Markers */}
          {data.cameras.map((cam) => {
            const hasAlert = data.active_alerts.some((a) => a.camera_name === cam.name);
            return (
              <Marker
                key={cam.id}
                position={[cam.latitude, cam.longitude]}
                icon={createCameraIcon(cam.current_intensity, hasAlert)}
                eventHandlers={{
                  click: () => setSelectedCamera(cam),
                }}
              >
                <Popup>
                  <div className="p-2 space-y-1 text-xs">
                    <div className="flex items-center justify-between font-bold text-sm text-[#c0c1ff]">
                      <span>{cam.name}</span>
                      <span
                        className={`text-[10px] font-mono px-1 py-0.5 rounded uppercase ${
                          cam.status === 'online' ? 'bg-emerald-950 text-emerald-400' : 'bg-rose-950 text-rose-400'
                        }`}
                      >
                        {cam.status}
                      </span>
                    </div>
                    <div className="text-[11px] text-[#908fa0] font-mono">
                      Hourly Sightings: <strong className="text-[#e4e1ed]">{cam.observations_last_hour}</strong>
                    </div>
                    <div className="text-[11px] text-[#908fa0] font-mono">
                      GPS: {cam.latitude.toFixed(4)}, {cam.longitude.toFixed(4)}
                    </div>
                    {hasAlert && (
                      <div className="p-1 rounded bg-rose-950/80 border border-rose-500/50 text-rose-400 font-bold text-[10px] flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" /> Security Alert Active
                      </div>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>

      {/* Right Telemetry Drawer for Selected Camera */}
      {selectedCamera && (
        <div className="w-80 bg-[#13131b] border-l border-[#292932] p-4 flex flex-col justify-between z-[1000] overflow-y-auto">
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#292932]">
              <div className="flex items-center gap-2">
                <Camera className="w-4 h-4 text-[#38bdf8]" />
                <h3 className="font-semibold text-sm text-[#e4e1ed]">{selectedCamera.name}</h3>
              </div>
              <button
                onClick={() => setSelectedCamera(null)}
                className="text-[#908fa0] hover:text-[#e4e1ed] cursor-pointer text-xs"
              >
                ✕
              </button>
            </div>

            {/* Live Camera Stream Mock Preview */}
            <div className="relative rounded overflow-hidden border border-[#292932] aspect-video bg-[#0d0d15] flex items-center justify-center">
              <img
                src="https://images.unsplash.com/photo-1549399542-7e3f8b79c341?w=500"
                alt="Camera Stream"
                className="w-full h-full object-cover opacity-80"
              />
              <div className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-[#0d0d15]/80 font-mono text-[10px] text-emerald-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>RTSP LIVE</span>
              </div>
              <div className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-[#0d0d15]/80 font-mono text-[10px] text-[#908fa0]">
                30 FPS • 1080p
              </div>
            </div>

            {/* Camera Metrics Grid */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                <span className="text-[10px] font-mono text-[#908fa0] block">THROUGHPUT</span>
                <span className="text-sm font-mono font-bold text-[#e4e1ed]">
                  {selectedCamera.observations_last_hour} / hr
                </span>
              </div>
              <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                <span className="text-[10px] font-mono text-[#908fa0] block">INTENSITY</span>
                <span className="text-sm font-mono font-bold text-[#38bdf8] uppercase">
                  {selectedCamera.current_intensity}
                </span>
              </div>
            </div>

            {/* Coordinates & Technical Specs */}
            <div className="space-y-2 text-xs font-mono bg-[#1b1b23] p-3 rounded border border-[#292932]">
              <div className="flex justify-between text-[#908fa0]">
                <span>Latitude:</span>
                <span className="text-[#e4e1ed]">{selectedCamera.latitude.toFixed(5)}</span>
              </div>
              <div className="flex justify-between text-[#908fa0]">
                <span>Longitude:</span>
                <span className="text-[#e4e1ed]">{selectedCamera.longitude.toFixed(5)}</span>
              </div>
              <div className="flex justify-between text-[#908fa0]">
                <span>Direction:</span>
                <span className="text-[#e4e1ed]">BIDIRECTIONAL</span>
              </div>
              <div className="flex justify-between text-[#908fa0]">
                <span>Status:</span>
                <span className="text-emerald-400 font-bold uppercase">{selectedCamera.status}</span>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-[#292932] space-y-2">
            <button
              onClick={() => onSelectVehicle('KA01AB1234')}
              className="w-full py-2 rounded bg-[#8083ff] hover:bg-[#8083ff]/90 text-[#0d0096] font-bold text-xs font-mono transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <Eye className="w-3.5 h-3.5" /> Inspect Camera Sightings
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
