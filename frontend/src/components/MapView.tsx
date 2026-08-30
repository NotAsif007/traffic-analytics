import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import {
  Camera,
  Activity,
  Car,
  AlertTriangle,
  Radio,
  Eye,
  Sliders,
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
    map.flyTo(target.center, target.zoom, { duration: 1.2 });
  }, [selectedCity, map]);
  return null;
};

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
  selectedCity?: string;
  onCityChange?: (city: string) => void;
}

export const MapView: React.FC<MapViewProps> = ({
  data,
  onSelectVehicle,
  selectedCity = 'All',
  onCityChange,
}) => {
  const [selectedCamera, setSelectedCamera] = useState<MapCameraNode | null>(null);
  const [showTrajectories, setShowTrajectories] = useState(true);
  const [showAlerts, setShowAlerts] = useState(true);

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-[#908fa0]">
        <div className="flex items-center gap-2 font-mono text-sm">
          <Radio className="w-4 h-4 animate-spin text-[#c0c1ff]" />
          <span>Rendering Pan-India Geospatial Map Layers...</span>
        </div>
      </div>
    );
  }

  const initialView = CITY_COORDINATES[selectedCity] || CITY_COORDINATES.All;

  return (
    <div className="relative w-full h-full flex overflow-hidden">
      {/* Map Control Bar Overlay */}
      <div className="absolute top-3 left-3 z-[1000] bg-[#13131b]/90 backdrop-blur-md border border-[#292932] rounded p-2.5 flex flex-wrap items-center gap-3 text-xs shadow-2xl">
        <div className="flex items-center gap-1.5 font-mono text-[#c0c1ff] font-semibold border-r border-[#292932] pr-3">
          <Globe2 className="w-4 h-4 text-[#8083ff]" />
          <span>{selectedCity === 'All' ? 'Pan-India Network' : selectedCity}</span>
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
          center={initialView.center}
          zoom={initialView.zoom}
          style={{ width: '100%', height: '100%' }}
          zoomControl={false}
        >
          <MapPanController selectedCity={selectedCity} />

          {/* Esri World Dark Gray Base Tile Layer */}
          <TileLayer
            attribution='&copy; <a href="https://www.esri.com/">Esri</a>, HERE, Garmin, &copy; OpenStreetMap'
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
                ? '#f43f5e'
                : road.current_congestion_index > 1.3
                ? '#f59e0b'
                : '#3b82f6';
            return (
              <Polyline
                key={road.id}
                positions={coords}
                pathOptions={{
                  color,
                  weight: 4,
                  opacity: 0.8,
                  lineCap: 'round',
                }}
              >
                <Popup className="custom-popup">
                  <div className="p-2 space-y-1 bg-[#13131b] text-[#e4e1ed] font-sans">
                    <div className="font-bold text-xs text-[#c0c1ff]">{road.name}</div>
                    <div className="text-[11px] font-mono text-[#908fa0]">
                      Congestion Index: <strong className="text-amber-400">{road.current_congestion_index.toFixed(2)}x</strong>
                    </div>
                  </div>
                </Popup>
              </Polyline>
            );
          })}

          {/* Active Trajectories Polylines */}
          {showTrajectories &&
            data.active_trajectories.map((traj) => (
              <Polyline
                key={traj.trajectory_id}
                positions={traj.coordinates}
                pathOptions={{
                  color: '#8083ff',
                  weight: 3,
                  dashArray: '6, 8',
                  opacity: 0.9,
                }}
              >
                <Popup className="custom-popup">
                  <div className="p-2 space-y-1.5 bg-[#13131b] text-[#e4e1ed] font-sans">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-[#c0c1ff]">
                      <Car className="w-3.5 h-3.5" />
                      <span>{traj.canonical_plate || 'Unidentified Vehicle'}</span>
                    </div>
                    <div className="text-[11px] font-mono text-[#908fa0]">
                      Class: <strong className="text-[#e4e1ed]">{traj.vehicle_class || 'car'}</strong>
                    </div>
                    {traj.current_speed_kmh && (
                      <div className="text-[11px] font-mono text-[#908fa0]">
                        Est. Speed: <strong className="text-emerald-400">{traj.current_speed_kmh.toFixed(1)} km/h</strong>
                      </div>
                    )}
                    <button
                      onClick={() => onSelectVehicle(traj.canonical_plate || '')}
                      className="mt-1 w-full py-1 px-2 rounded bg-[#8083ff] hover:bg-[#8083ff]/90 text-[#0d0096] text-[10px] font-mono font-bold transition-colors cursor-pointer"
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
                    <div style="width: 24px; height: 24px; background: #ef4444; border: 2px solid #ffffff; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 12px #ef4444; animation: bounce 1s infinite;">
                      <span style="color: white; font-size: 11px; font-weight: bold;">!</span>
                    </div>
                  `,
                  iconSize: [24, 24],
                  iconAnchor: [12, 12],
                })}
              >
                <Popup className="custom-popup">
                  <div className="p-2 space-y-1 bg-[#13131b] text-[#e4e1ed] font-sans">
                    <div className="flex items-center gap-1 text-xs font-bold text-rose-400">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>{alert.alert_code}: {alert.alert_type}</span>
                    </div>
                    <p className="text-[11px] text-[#908fa0] leading-tight">{alert.description || alert.title}</p>
                    <div className="text-[10px] font-mono text-rose-300">
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
                  <div className="p-2 space-y-1 bg-[#13131b] text-[#e4e1ed] font-sans">
                    <div className="flex items-center gap-1 font-bold text-xs text-[#c0c1ff]">
                      <Camera className="w-3.5 h-3.5" />
                      <span>{cam.name}</span>
                    </div>
                    <div className="text-[11px] text-[#908fa0] font-mono">
                      Hourly Sightings: <strong className="text-[#e4e1ed]">{cam.observations_last_hour}</strong>
                    </div>
                    <div className="text-[11px] text-[#908fa0] font-mono">
                      GPS: {cam.latitude.toFixed(4)}, {cam.longitude.toFixed(4)}
                    </div>
                    {hasAlert && (
                      <div className="p-1 rounded bg-rose-950/80 border border-rose-500/50 text-rose-400 font-bold text-[10px] flex items-center gap-1">
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

            {/* Live Indian CCTV Camera Stream Player */}
            <CCTVStreamPlayer
              cameraName={selectedCamera.name}
              cameraId={selectedCamera.id}
              intensity={selectedCamera.current_intensity}
              observationsPerHour={selectedCamera.observations_last_hour}
            />

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
              onClick={() => setSelectedCamera(null)}
              className="w-full py-1.5 rounded bg-[#1f1f27] hover:bg-[#292932] text-xs font-mono text-[#c7c4d7] transition-colors cursor-pointer"
            >
              Close Stream
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
