export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

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
  activity_type: 'ALERT' | 'TRAJECTORY' | 'CAMERA_STATUS' | 'CONGESTION';
  title: string;
  description: string;
  timestamp: string;
  camera_name?: string | null;
  severity?: 'low' | 'moderate' | 'high' | 'critical';
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
  identity_id?: string;
  vehicle_identity_id?: string;
  canonical_plate?: string | null;
  vehicle_class?: string | null;
  confidence?: number;
  status?: string;
  coordinates: [number, number][];
  current_speed_kmh?: number | null;
  start_time?: string;
  last_seen_time?: string;
  total_distance_m?: number;
  camera_names?: string[];
}

export interface MapAlertMarker {
  id?: string;
  alert_id?: string;
  alert_code: string;
  alert_type: string;
  title?: string;
  severity: 'low' | 'moderate' | 'high' | 'critical';
  latitude: number;
  longitude: number;
  camera_name?: string | null;
  description?: string;
  created_at?: string;
  timestamp?: string;
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
  cameras_involved: CameraBrief[];
  resolution_notes?: string | null;
}

export interface HourlyVolumePoint {
  bucket: string;
  total: number;
  cars?: number;
  two_wheelers?: number;
  buses?: number;
  trucks?: number;
  classes?: {
    car?: number;
    bike?: number;
    two_wheeler?: number;
    bus?: number;
    truck?: number;
    auto_rickshaw?: number;
  };
}

export interface OriginDestinationFlow {
  origin_zone: string;
  destination_zone: string;
  trip_count: number;
  avg_travel_time_s: number;
}

export interface FrequentRoute {
  route_key?: string;
  camera_sequence: string[];
  frequency_count: number;
  avg_travel_time_s: number;
}

export interface DashboardAnalyticsSummaryResponse {
  generated_at: string;
  total_vehicles_past_24h: number;
  hourly_volume_trend: HourlyVolumePoint[];
  top_congested_corridors: CongestionHotspot[];
  top_od_flows: OriginDestinationFlow[];
  top_frequent_routes: FrequentRoute[];
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
  // Backend may return either field name for the timestamp
  timestamp?: string;
  evaluation_timestamp?: string;
  benchmark_name: string;
  dataset_summary: {
    total_cameras: number;
    total_vehicles: number;
    total_observations: number;
    // backend field: total_anomalous_events or blacklisted_vehicles
    total_anomalous_events?: number;
    blacklisted_vehicles?: number;
  };
  anpr: {
    detection_precision: number;
    detection_recall: number;
    detection_f1: number;
    exact_plate_accuracy: number;
    normalized_plate_accuracy: number;
    // backend field name: average_character_accuracy
    character_accuracy?: number;
    average_character_accuracy?: number;
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
    // backend field name: f1_score
    f1?: number;
    f1_score?: number;
    trajectory_completeness_rate: number;
  };
  alerts: {
    precision: number;
    recall: number;
    // backend field name: f1_score
    f1?: number;
    f1_score?: number;
    false_positive_rate: number;
  };
  // backend field name: overall_system_score
  overall_composite_score?: number;
  overall_system_score?: number;
}

export interface DatasetSummary {
  dataset_name: string;
  dataset_code: string;
  description: string;
  total_frames_or_sequences: number;
  total_observations: number;
  unique_vehicles: number;
  supported_classes: string[];
  has_license_plates: boolean;
  has_multi_camera_ids: boolean;
}

export interface IndianANPRMetrics {
  total_samples: number;
  exact_match_accuracy: number;
  normalized_match_accuracy: number;
  state_code_accuracy: number;
  character_accuracy: number;
  mean_ocr_confidence: number;
  hsrp_recognition_rate: number;
}

export interface IndianClassMetrics {
  vehicle_class: string;
  sample_count: number;
  precision: number;
  recall: number;
  f1_score: number;
}

export interface MultiCameraTrackingMetrics {
  total_global_vehicles: number;
  total_camera_handovers: number;
  successful_associations: number;
  association_precision: number;
  association_recall: number;
  cross_camera_f1: number;
  trajectory_completeness: number;
}

export interface RealDatasetEvaluationReport {
  timestamp: string;
  datasets_evaluated: string[];
  anpr_metrics: IndianANPRMetrics;
  classification_breakdown: IndianClassMetrics[];
  overall_mean_classification_f1: number;
  multicamera_metrics: MultiCameraTrackingMetrics;
  robustness_score: number;
  composite_indian_readiness_score: number;
}

export interface PredictedNextHop {
  camera_id: string;
  camera_name: string;
  road_name?: string | null;
  probability: number;
  distance_meters: number;
  estimated_travel_time_seconds: number;
  estimated_arrival_time: string;
  confidence_score: number;
}

export interface TrajectoryPredictionResponse {
  trajectory_id: string;
  vehicle_identity_id: string;
  current_camera_id: string;
  current_camera_name: string;
  last_seen_timestamp: string;
  current_speed_kmh?: number | null;
  predicted_next_hops: PredictedNextHop[];
  predicted_destination_corridor?: string | null;
  deviation_risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  forecast_method: string;
}

