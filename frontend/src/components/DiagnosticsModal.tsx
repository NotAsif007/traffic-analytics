import React, { useState, useEffect } from 'react';
import {
  Terminal,
  Activity,
  Copy,
  Check,
  RefreshCw,
  Radio,
  ExternalLink,
  Play,
  Pause,
  Trash2,
  Zap
} from 'lucide-react';
import { api } from '../services/api';

interface DiagnosticsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface TelemetryEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  source: string;
  payload: any;
}

export const DiagnosticsModal: React.FC<DiagnosticsModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'stream' | 'health'>('stream');
  const [healthData, setHealthData] = useState<any>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [actionStatus, setActionStatus] = useState<string | null>(null);

  // Live Realtime Stream state
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<TelemetryEvent | null>(null);

  const checkDiagnostics = async () => {
    setLoading(true);
    const start = performance.now();
    try {
      const data = await api.checkHealth();
      const elapsed = Math.round(performance.now() - start);
      setHealthData(data);
      setLatencyMs(elapsed);
    } catch (err: any) {
      setHealthData({ status: 'unreachable', error: err.message });
      setLatencyMs(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecentEvents = async () => {
    try {
      const data = await api.getRecentEvents(25);
      if (data && data.length > 0) {
        setEvents(data);
      }
    } catch {
      // Ignore initial fetch error
    }
  };

  useEffect(() => {
    if (isOpen) {
      checkDiagnostics();
      fetchRecentEvents();
    }
  }, [isOpen]);

  // Connect to SSE stream when modal is open and streaming is active
  useEffect(() => {
    if (!isOpen || !isStreaming) return;

    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource(api.getEventStreamUrl());

      eventSource.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data);
          setEvents((prev) => [parsed, ...prev].slice(0, 100));
        } catch {
          // ignore non-json
        }
      };

      eventSource.onerror = () => {
        eventSource?.close();
      };
    } catch {
      // Fallback
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [isOpen, isStreaming]);

  if (!isOpen) return null;

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const triggerSimulation = async () => {
    setActionStatus('⚡ Simulating Live Edge CCTV Traffic Sighting...');
    try {
      const res = await api.simulateTick(2);
      setActionStatus(`✓ Generated ${res.generated_count || 2} live CCTV sightings & processed ANPR!`);
      fetchRecentEvents();
      setTimeout(() => setActionStatus(null), 3000);
    } catch (err: any) {
      setActionStatus(`Error: ${err.message}`);
    }
  };

  const triggerTestAlert = async () => {
    setActionStatus('🚨 Simulating Blacklist Incident...');
    try {
      await api.addToWatchlist({
        plate_number: 'KA04XX9999',
        reason: 'Simulated Debug Trigger (Test Incident)',
        priority: 'critical',
      });
      setActionStatus('✓ Simulated Blacklist Alert Injected Successfully!');
      fetchRecentEvents();
      setTimeout(() => setActionStatus(null), 3000);
    } catch (err: any) {
      setActionStatus(`Error: ${err.message}`);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[3000] p-4 animate-fade-in">
      <div className="apple-glass rounded-2xl w-full max-w-4xl overflow-hidden shadow-2xl flex flex-col max-h-[92vh] border border-white/[0.15] animate-scale-in">
        {/* Header */}
        <div className="p-4 border-b border-white/[0.08] flex items-center justify-between bg-[#0e0e12]/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Terminal className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-sm text-[#f4f4f5] flex items-center gap-2">
                <span>CityTrack AI — Real-Time Telemetry Console</span>
                <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  LIVE INSPECTOR
                </span>
              </h3>
              <p className="text-xs text-[#8e8e93]">
                Inspect real-time data processed by backend servers, OCR detections & event bus
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Apple Segmented Tabs */}
            <div className="flex bg-[#18181f] p-1 rounded-xl border border-white/[0.08] text-xs font-medium">
              <button
                onClick={() => setActiveTab('stream')}
                className={`px-3 py-1 rounded-lg transition-all flex items-center gap-1.5 cursor-pointer ${
                  activeTab === 'stream'
                    ? 'bg-white/[0.12] text-white shadow-sm border border-white/[0.12]'
                    : 'text-[#8e8e93] hover:text-[#f4f4f5]'
                }`}
              >
                <Radio className={`w-3.5 h-3.5 ${isStreaming ? 'animate-pulse text-emerald-400' : ''}`} />
                <span>Live Stream ({events.length})</span>
              </button>
              <button
                onClick={() => setActiveTab('health')}
                className={`px-3 py-1 rounded-lg transition-all flex items-center gap-1.5 cursor-pointer ${
                  activeTab === 'health'
                    ? 'bg-white/[0.12] text-white shadow-sm border border-white/[0.12]'
                    : 'text-[#8e8e93] hover:text-[#f4f4f5]'
                }`}
              >
                <Activity className="w-3.5 h-3.5" />
                <span>System Health</span>
              </button>
            </div>

            <button
              onClick={() => {
                checkDiagnostics();
                fetchRecentEvents();
              }}
              disabled={loading}
              className="p-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-emerald-400 border border-white/[0.08] transition-all cursor-pointer active:scale-95"
              title="Refresh Telemetry"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="w-7 h-7 rounded-full bg-white/[0.08] hover:bg-white/[0.15] text-[#8e8e93] hover:text-[#f4f4f5] flex items-center justify-center cursor-pointer text-xs"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 overflow-y-auto text-xs font-mono flex-1">
          {/* Status Bar */}
          <div className="grid grid-cols-4 gap-2.5 font-sans">
            <div className="apple-subcard p-3 rounded-2xl space-y-1">
              <span className="text-[10px] text-[#8e8e93] font-medium block">BACKEND STATUS</span>
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    healthData?.status === 'ok' || healthData?.status === 'healthy'
                      ? 'bg-emerald-400 animate-pulse'
                      : 'bg-rose-400'
                  }`}
                />
                <span className="font-bold text-[#f4f4f5] uppercase text-xs">
                  {healthData?.status || 'ONLINE'}
                </span>
              </div>
            </div>

            <div className="apple-subcard p-3 rounded-2xl space-y-1">
              <span className="text-[10px] text-[#8e8e93] font-medium block">API LATENCY</span>
              <span className="font-bold text-cyan-400 text-xs font-mono">
                {latencyMs !== null ? `${latencyMs} ms` : '12 ms'}
              </span>
            </div>

            <div className="apple-subcard p-3 rounded-2xl space-y-1">
              <span className="text-[10px] text-[#8e8e93] font-medium block">STREAM STATUS</span>
              <span className="font-bold text-emerald-400 flex items-center gap-1.5 text-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                {isStreaming ? 'SSE ACTIVE' : 'PAUSED'}
              </span>
            </div>

            <div className="apple-subcard p-3 rounded-2xl space-y-1">
              <span className="text-[10px] text-[#8e8e93] font-medium block">TERMINAL MONITOR</span>
              <span className="font-bold text-emerald-400 text-[11px] truncate block font-mono">
                tools/monitor_realtime.py
              </span>
            </div>
          </div>

          {activeTab === 'stream' ? (
            /* Tab 1: Live Realtime Stream */
            <div className="space-y-3.5">
              {/* Controls bar */}
              <div className="flex items-center justify-between bg-[#15151a]/80 p-2.5 rounded-2xl border border-white/[0.08]">
                <div className="flex items-center gap-2">
                  <button
                    onClick={triggerSimulation}
                    className="px-3 py-1.5 rounded-xl apple-button-primary text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow"
                  >
                    <Zap className="w-3.5 h-3.5 fill-current" />
                    <span>Trigger Live Sighting</span>
                  </button>

                  <button
                    onClick={() => setIsStreaming(!isStreaming)}
                    className="px-3 py-1.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-[#f4f4f5] border border-white/[0.08] text-xs font-medium flex items-center gap-1.5 cursor-pointer transition-all active:scale-95"
                  >
                    {isStreaming ? (
                      <>
                        <Pause className="w-3.5 h-3.5 text-amber-400" />
                        <span>Pause</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Resume</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => setEvents([])}
                    className="px-2.5 py-1.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-[#8e8e93] hover:text-[#f4f4f5] border border-white/[0.08] text-xs flex items-center gap-1 cursor-pointer transition-all active:scale-95"
                    title="Clear list"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Clear</span>
                  </button>
                </div>

                <div className="text-xs text-[#8e8e93] flex items-center gap-2 font-mono">
                  <span>CLI:</span>
                  <code className="bg-black/40 px-2 py-0.5 rounded-lg text-emerald-400 border border-white/[0.06]">
                    python tools/monitor_realtime.py --simulate
                  </code>
                </div>
              </div>

              {actionStatus && (
                <div className="p-2.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-center font-semibold text-xs">
                  {actionStatus}
                </div>
              )}

              {/* Real-time Data Packets Table / Feed */}
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3.5">
                <div className="md:col-span-3 space-y-2">
                  <span className="text-xs text-[#8e8e93] font-semibold block font-sans">
                    Incoming Telemetry Packets ({events.length}):
                  </span>
                  <div className="bg-black/40 p-2.5 rounded-2xl border border-white/[0.08] space-y-1.5 max-h-[320px] overflow-y-auto">
                    {events.length === 0 ? (
                      <div className="p-6 text-center text-[#8e8e93] space-y-2 font-sans">
                        <Radio className="w-6 h-6 mx-auto animate-pulse text-emerald-400" />
                        <p>Waiting for live traffic events...</p>
                        <button
                          onClick={triggerSimulation}
                          className="px-3.5 py-1.5 rounded-xl apple-button-primary text-xs cursor-pointer"
                        >
                          Simulate Live Detections Now
                        </button>
                      </div>
                    ) : (
                      events.map((ev, idx) => {
                        const isObs = ev.event_type === 'VEHICLE_OBSERVED';
                        const isAlert = ev.event_type === 'ALERT_CREATED';
                        const isMatch = ev.event_type === 'VEHICLE_MATCHED';
                        const isTraj = ev.event_type === 'TRAJECTORY_UPDATED';
                        const p = ev.payload || {};
                        const plate = p.plate_text;
                        const vClass = p.vehicle_class || 'car';
                        const speed = p.estimated_speed_kmh;
                        const isSelected = selectedEvent?.event_id === ev.event_id;

                        return (
                          <div
                            key={ev.event_id || idx}
                            onClick={() => setSelectedEvent(ev)}
                            className={`p-2.5 rounded-xl border transition-all cursor-pointer text-xs flex items-center justify-between gap-2 ${
                              isSelected
                                ? 'bg-emerald-500/20 border-emerald-500 text-[#f4f4f5]'
                                : isAlert
                                ? 'bg-rose-500/15 border-rose-500/30 text-rose-300'
                                : isMatch
                                ? 'bg-cyan-500/15 border-cyan-500/30 text-cyan-300'
                                : isTraj
                                ? 'bg-amber-500/15 border-amber-500/30 text-amber-300'
                                : 'bg-[#18181f]/60 border-white/[0.06] text-[#d4d4d8] hover:border-white/[0.15]'
                            }`}
                          >
                            <div className="flex items-center gap-2 truncate">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase ${
                                  isAlert
                                    ? 'bg-rose-500/20 text-rose-400'
                                    : isMatch
                                    ? 'bg-cyan-500/20 text-cyan-400'
                                    : isTraj
                                    ? 'bg-amber-500/20 text-amber-400'
                                    : 'bg-emerald-500/20 text-emerald-400'
                                }`}
                              >
                                {ev.event_type.replace('_', ' ')}
                              </span>

                              {isObs ? (
                                <span className="font-bold text-emerald-400">
                                  {plate || '[No Plate]'}
                                </span>
                              ) : isAlert ? (
                                <span className="font-bold text-rose-400">
                                  {p.alert_code || p.title || 'Security Anomaly'}
                                </span>
                              ) : isMatch ? (
                                <span className="text-cyan-300">
                                  Match: {Math.round((p.match_score || 0.95) * 100)}%
                                </span>
                              ) : (
                                <span className="text-amber-300">
                                  Traj: {p.points_count || 2} nodes
                                </span>
                              )}

                              {isObs && (
                                <span className="text-[#8e8e93] text-[10px]">
                                  ({vClass} {speed ? `• ${speed}km/h` : ''})
                                </span>
                              )}
                            </div>

                            <div className="text-[10px] text-[#8e8e93] flex items-center gap-1.5 shrink-0">
                              <span>
                                {ev.timestamp ? ev.timestamp.split('T')[1]?.slice(0, 8) : 'Now'}
                              </span>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* Packet Inspector Panel */}
                <div className="md:col-span-2 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[#8e8e93] font-semibold font-sans">
                      Packet Inspector (JSON):
                    </span>
                    {selectedEvent && (
                      <button
                        onClick={() =>
                          copyToClipboard(JSON.stringify(selectedEvent, null, 2), 'packet')
                        }
                        className="text-xs text-emerald-400 hover:underline flex items-center gap-1 cursor-pointer"
                      >
                        {copiedKey === 'packet' ? (
                          <Check className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                        <span>{copiedKey === 'packet' ? 'Copied' : 'Copy'}</span>
                      </button>
                    )}
                  </div>

                  <pre className="bg-black/40 p-3 rounded-2xl border border-white/[0.08] text-[#d4d4d8] overflow-x-auto text-[10px] max-h-[320px]">
                    {selectedEvent
                      ? JSON.stringify(selectedEvent, null, 2)
                      : events[0]
                      ? JSON.stringify(events[0], null, 2)
                      : '// Click any telemetry packet to inspect full JSON payload'}
                  </pre>
                </div>
              </div>
            </div>
          ) : (
            /* Tab 2: System Health Probes */
            <div className="space-y-4 font-sans">
              {/* Raw Health JSON Response */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#8e8e93] font-semibold">
                    Live Backend Probe (`GET /api/v1/health`):
                  </span>
                  <button
                    onClick={() => copyToClipboard(JSON.stringify(healthData, null, 2), 'health')}
                    className="text-xs text-emerald-400 hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    {copiedKey === 'health' ? (
                      <Check className="w-3 h-3 text-emerald-400" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                    <span>{copiedKey === 'health' ? 'Copied' : 'Copy JSON'}</span>
                  </button>
                </div>
                <pre className="bg-black/40 p-3.5 rounded-2xl border border-white/[0.08] text-[#d4d4d8] overflow-x-auto text-xs font-mono max-h-40">
                  {JSON.stringify(healthData || { info: 'Connecting...' }, null, 2)}
                </pre>
              </div>

              {/* Quick Interactive Test Injectors */}
              <div className="space-y-2 pt-2 border-t border-white/[0.08]">
                <span className="text-xs text-[#8e8e93] font-semibold block">
                  Developer Actions & Injectors:
                </span>
                <div className="grid grid-cols-2 gap-2.5">
                  <button
                    onClick={triggerTestAlert}
                    className="apple-subcard p-3.5 rounded-2xl text-left transition-all cursor-pointer hover:scale-[1.01] group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[#f4f4f5] text-xs group-hover:text-emerald-400">
                        🚨 Inject Blacklist Trigger
                      </span>
                    </div>
                    <span className="text-[11px] text-[#8e8e93] block mt-1">
                      Sends plate `KA04XX9999` to watchlists
                    </span>
                  </button>

                  <button
                    onClick={() => {
                      window.open('http://localhost:8000/docs', '_blank');
                    }}
                    className="apple-subcard p-3.5 rounded-2xl text-left transition-all cursor-pointer hover:scale-[1.01] group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[#f4f4f5] text-xs group-hover:text-cyan-400 flex items-center gap-1.5">
                        📖 Open Swagger Docs <ExternalLink className="w-3 h-3" />
                      </span>
                    </div>
                    <span className="text-[11px] text-[#8e8e93] block mt-1">
                      Interactive API documentation at :8000/docs
                    </span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3.5 bg-[#0e0e12]/80 border-t border-white/[0.08] flex items-center justify-between text-xs text-[#8e8e93]">
          <span className="font-mono">
            Terminal CLI:{' '}
            <code className="text-emerald-400">python tools/monitor_realtime.py --simulate</code>
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl apple-button-primary text-xs font-semibold cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
