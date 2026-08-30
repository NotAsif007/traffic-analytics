// Complete TypeScript definitions matching FastAPI backend contracts

export interface CongestionHotspot {
  corridor_name: string;
  source_camera_name: string;
  destination_camera_name: string;
  congestion_index: number;
  current_travel_time_s: number;
  baseline_travel_time_s: number;
  severity: 'low' | 'moderate' | 'high' | 'severe';
}

export interface RecentActivityItem {
  activity_type: string;
  title: string;
  description: string;
  timestamp: string;
  camera_name?: string | null;
  severity: string;
}

export interface CityOverviewResponse {
  generated_at: string;
  active_cameras_count: number;
  total_cameras_count: number;
  cameras_online_percentage: number;
  vehicles_observed_today: number;
  current_traffic_level: 'low' | 'moderate' | 'heavy' | 'congested';
  active_alerts_count: number;
  critical_alerts_count: number;
  congestion_hotspots: CongestionHotspot[];
  recent_activity: RecentActivityItem[];
}

export interface MapCameraNode {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  status: 'online' | 'offline' | 'degraded';
  current_intensity: 'low' | 'moderate' | 'high';
  observations_last_hour: number;
  last_observation_time?: string | null;
}

export interface MapRoadSegment {
  id: string;
  name: string;
  geometry_geojson: {
    type: string;
    coordinates: number[][] | number[][][];
  };
  current_congestion_index: number;
}

export interface MapTrajectoryLine {
  trajectory_id: string;
  vehicle_identity_id: string;
  canonical_plate?: string | null;
  coordinates: number[][];
  confidence: number;
  start_time: string;
  last_seen_time: string;
  total_distance_m: number;
  camera_names: string[];
}

export interface MapAlertMarker {
  id: string;
  alert_code: string;
  alert_type: string;
  severity: 'low' | 'moderate' | 'high' | 'critical';
  latitude?: number | null;
  longitude?: number | null;
  camera_name?: string | null;
  title: string;
  timestamp: string;
}

export interface LiveMapResponse {
  generated_at: string;
  cameras: MapCameraNode[];
  road_segments: MapRoadSegment[];
  active_trajectories: MapTrajectoryLine[];
  active_alerts: MapAlertMarker[];
}

export interface CameraVisitTimeline {
  step_number: number;
  camera_id: string;
  camera_name: string;
  latitude: number;
  longitude: number;
  timestamp: string;
  dwell_or_transit_seconds?: number | null;
  segment_speed_kmh?: number | null;
}

export interface PlateObservationEvidence {
  observation_id: string;
  camera_id: string;
  camera_name: string;
  timestamp: string;
  raw_plate_text?: string | null;
  plate_confidence?: number | null;
  detection_confidence: number;
  vehicle_class: string;
  vehicle_color: string;
  image_path?: string | null;
  plate_crop_path?: string | null;
}

export interface VehicleInvestigationResponse {
  identity_id: string;
  canonical_plate?: string | null;
  vehicle_class: string;
  vehicle_color: string;
  overall_confidence: number;
  first_seen_at: string;
  last_seen_at: string;
  total_sightings_count: number;
  last_known_camera_name?: string | null;
  last_known_coordinates?: number[] | null;
  camera_history: CameraVisitTimeline[];
  plate_observations: PlateObservationEvidence[];
  active_alerts: MapAlertMarker[];
}

export interface CameraBrief {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  direction?: string | null;
}

export interface AlertInvestigationResponse {
  alert_id: string;
  alert_code: string;
  alert_type: string;
  severity: 'low' | 'moderate' | 'high' | 'critical';
  status: string;
  confidence: number;
  title: string;
  description: string;
  created_at: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  resolved_at?: string | null;
  resolved_by?: string | null;
  resolution_notes?: string | null;
  vehicle_identity_id?: string | null;
  canonical_plate?: string | null;
  cameras_involved: CameraBrief[];
  evidence: Record<string, any>;
  trajectory_summary?: MapTrajectoryLine | null;
}

export interface DashboardAnalyticsSummaryResponse {
  generated_at: string;
  total_vehicles_past_24h: number;
  hourly_volume_trend: {
    bucket: string;
    total: number;
    classes: Record<string, number>;
  }[];
  top_congested_corridors: CongestionHotspot[];
  top_frequent_routes: {
    route_key: string;
    camera_sequence: string[];
    frequency_count: number;
    avg_travel_time_s: number;
  }[];
  top_od_flows: {
    origin_zone: string;
    destination_zone: string;
    trip_count: number;
    avg_travel_time_s: number;
  }[];
}

export interface AlertItem {
  id: string;
  alert_code: string;
  alert_type: string;
  severity: 'low' | 'moderate' | 'high' | 'critical';
  status: 'NEW' | 'ACKNOWLEDGED' | 'RESOLVED' | 'DISMISSED';
  confidence: number;
  title: string;
  description: string;
  created_at: string;
  camera_id?: string | null;
  camera_name?: string | null;
  vehicle_identity_id?: string | null;
  canonical_plate?: string | null;
  evidence: Record<string, any>;
}

export interface BlacklistEntry {
  id: string;
  plate_number: string;
  reason: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  is_active: boolean;
  valid_from?: string | null;
  valid_until?: string | null;
  created_at: string;
  notes?: string | null;
}

export interface EvaluationReport {
  timestamp: string;
  benchmark_name: string;
  dataset_summary: {
    total_cameras: number;
    total_vehicles: number;
    total_observations: number;
    total_anomalous_events: number;
  };
  anpr: {
    detection_precision: number;
    detection_recall: number;
    detection_f1: number;
    exact_plate_accuracy: number;
    normalized_plate_accuracy: number;
    character_accuracy: number;
    mean_ocr_confidence: number;
  };
  tracking: {
    mota: number;
    idf1: number;
    id_switches: number;
    mostly_tracked_tracks: number;
  };
  association: {
    precision: number;
    recall: number;
    f1: number;
    trajectory_completeness_rate: number;
  };
  alerts: {
    precision: number;
    recall: number;
    f1: number;
    false_positive_rate: number;
  };
  overall_composite_score: number;
}
