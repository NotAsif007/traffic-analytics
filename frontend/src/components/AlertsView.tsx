import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  CheckCircle,
  XCircle,
  Eye,
  Clock,
  MapPin,
  FileText,
  Filter,
  Check,
  X
} from 'lucide-react';
import { AlertItem, AlertInvestigationResponse } from '../types/api';
import { api } from '../services/api';

export const AlertsView: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<AlertInvestigationResponse | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [resolveModalOpen, setResolveModalOpen] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [actingAlertId, setActingAlertId] = useState<string | null>(null);

  const loadAlerts = async () => {
    try {
      const data = await api.listAlerts();
      setAlerts(data);
    } catch (err) {
      console.error('Failed to load alerts:', err);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const handleInspect = async (alertId: string) => {
    try {
      const inv = await api.investigateAlert(alertId);
      setSelectedAlert(inv);
    } catch (err) {
      console.error('Failed to inspect alert:', err);
    }
  };

  const handleAcknowledge = async (alertId: string) => {
    await api.acknowledgeAlert(alertId);
    setAlerts((prev) =>
      prev.map((a) => (a.id === alertId ? { ...a, status: 'ACKNOWLEDGED' } : a))
    );
    if (selectedAlert && selectedAlert.alert_id === alertId) {
      setSelectedAlert({ ...selectedAlert, status: 'ACKNOWLEDGED' });
    }
  };

  const handleOpenResolve = (alertId: string) => {
    setActingAlertId(alertId);
    setResolutionNotes('');
    setResolveModalOpen(true);
  };

  const handleConfirmResolve = async () => {
    if (!actingAlertId) return;
    await api.resolveAlert(actingAlertId, resolutionNotes);
    setAlerts((prev) =>
      prev.map((a) => (a.id === actingAlertId ? { ...a, status: 'RESOLVED' } : a))
    );
    if (selectedAlert && selectedAlert.alert_id === actingAlertId) {
      setSelectedAlert({
        ...selectedAlert,
        status: 'RESOLVED',
        resolution_notes: resolutionNotes,
      });
    }
    setResolveModalOpen(false);
  };

  const handleDismiss = async (alertId: string) => {
    await api.dismissAlert(alertId);
    setAlerts((prev) =>
      prev.map((a) => (a.id === alertId ? { ...a, status: 'DISMISSED' } : a))
    );
    if (selectedAlert && selectedAlert.alert_id === alertId) {
      setSelectedAlert({ ...selectedAlert, status: 'DISMISSED' });
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (filterSeverity !== 'all' && a.severity !== filterSeverity) return false;
    if (filterStatus !== 'all' && a.status !== filterStatus) return false;
    return true;
  });

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full max-w-[1600px] mx-auto">
      {/* Header & Filter Controls */}
      <div className="bg-[#13131b] border border-[#292932] rounded p-3.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-rose-400" />
          <h2 className="font-bold text-sm text-[#e4e1ed]">
            Security & Anomaly Alert Center
          </h2>
          <span className="px-2 py-0.5 rounded bg-[#1f1f27] border border-[#34343d] text-xs font-mono text-[#908fa0]">
            {filteredAlerts.length} Active Events
          </span>
        </div>

        {/* Filter Dropdowns */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 font-mono text-[#908fa0]">
            <Filter className="w-3.5 h-3.5" />
            <span>Severity:</span>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="bg-[#0d0d15] border border-[#292932] rounded px-2 py-1 text-xs text-[#e4e1ed] focus:outline-none focus:border-[#8083ff]"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="moderate">Moderate</option>
              <option value="low">Low</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 font-mono text-[#908fa0]">
            <span>Status:</span>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-[#0d0d15] border border-[#292932] rounded px-2 py-1 text-xs text-[#e4e1ed] focus:outline-none focus:border-[#8083ff]"
            >
              <option value="all">All Statuses</option>
              <option value="NEW">NEW</option>
              <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
              <option value="RESOLVED">RESOLVED</option>
              <option value="DISMISSED">DISMISSED</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Alert Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Left 7 Cols: Alert Table List */}
        <div className="lg:col-span-7 bg-[#13131b] border border-[#292932] rounded overflow-hidden flex flex-col">
          <div className="p-3 border-b border-[#292932] flex items-center justify-between text-xs font-mono text-[#908fa0] uppercase tracking-wider font-semibold">
            <span>ALERT INCIDENTS</span>
            <span>STATUS / ACTION</span>
          </div>

          <div className="divide-y divide-[#1f1f27] overflow-y-auto">
            {filteredAlerts.length === 0 ? (
              <div className="p-8 text-center text-[#908fa0] text-xs font-mono">
                No alerts matching current filters.
              </div>
            ) : (
              filteredAlerts.map((alert) => (
                <div
                  key={alert.id}
                  onClick={() => handleInspect(alert.id)}
                  className={`p-3.5 flex items-start justify-between gap-3 cursor-pointer transition-colors hover:bg-[#1b1b23] ${
                    selectedAlert?.alert_id === alert.id ? 'bg-[#1b1b23] border-l-2 border-[#8083ff]' : ''
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`p-1.5 rounded shrink-0 mt-0.5 ${
                        alert.severity === 'critical'
                          ? 'bg-rose-950/60 text-rose-400 border border-rose-500/40'
                          : alert.severity === 'high'
                          ? 'bg-amber-950/60 text-amber-400 border border-amber-500/40'
                          : 'bg-[#8083ff]/10 text-[#c0c1ff] border border-[#8083ff]/30'
                      }`}
                    >
                      <AlertTriangle className="w-4 h-4" />
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-[#c0c1ff]">
                          {alert.alert_code}
                        </span>
                        <span
                          className={`text-[10px] font-mono font-bold uppercase px-1.5 py-0.2 rounded ${
                            alert.severity === 'critical'
                              ? 'bg-rose-950/50 text-rose-400'
                              : 'bg-amber-950/50 text-amber-400'
                          }`}
                        >
                          {alert.severity}
                        </span>
                        <span className="text-[10px] font-mono text-[#908fa0]">
                          Conf: {(alert.confidence * 100).toFixed(1)}%
                        </span>
                      </div>

                      <h4 className="text-xs font-semibold text-[#e4e1ed] mt-1">{alert.title}</h4>
                      <p className="text-[11px] text-[#908fa0] mt-0.5 line-clamp-2">
                        {alert.description}
                      </p>

                      <div className="flex items-center gap-4 mt-2 text-[10px] font-mono text-[#908fa0]">
                        <span>Camera: {alert.camera_name || 'Network'}</span>
                        {alert.canonical_plate && (
                          <span className="text-[#38bdf8] font-bold">
                            Plate: {alert.canonical_plate}
                          </span>
                        )}
                        <span>{new Date(alert.created_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  </div>

                  {/* Status Badge & Actions */}
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
                        alert.status === 'NEW'
                          ? 'bg-rose-950 text-rose-400 border border-rose-500/30 animate-pulse'
                          : alert.status === 'ACKNOWLEDGED'
                          ? 'bg-amber-950 text-amber-400 border border-amber-500/30'
                          : alert.status === 'RESOLVED'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30'
                          : 'bg-[#1f1f27] text-[#908fa0]'
                      }`}
                    >
                      {alert.status}
                    </span>

                    <div className="flex items-center gap-1">
                      {alert.status === 'NEW' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAcknowledge(alert.id);
                          }}
                          className="px-2 py-1 rounded bg-[#1f1f27] hover:bg-[#292932] text-xs font-mono text-[#c0c1ff] border border-[#34343d] transition-colors cursor-pointer"
                        >
                          Ack
                        </button>
                      )}
                      {alert.status !== 'RESOLVED' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenResolve(alert.id);
                          }}
                          className="px-2 py-1 rounded bg-emerald-950 hover:bg-emerald-900 text-xs font-mono text-emerald-400 border border-emerald-500/40 transition-colors cursor-pointer"
                        >
                          Resolve
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right 5 Cols: Forensic Explainability Dossier */}
        <div className="lg:col-span-5 bg-[#13131b] border border-[#292932] rounded p-4 flex flex-col justify-between">
          {selectedAlert ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#292932]">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[#c0c1ff]" />
                  <h3 className="font-semibold text-sm text-[#e4e1ed]">
                    Forensic Explainability Case File
                  </h3>
                </div>
                <span className="font-mono text-xs text-[#38bdf8] font-bold">
                  {selectedAlert.alert_code}
                </span>
              </div>

              {/* Title & Description */}
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-[#e4e1ed]">{selectedAlert.title}</h4>
                <p className="text-xs text-[#c7c4d7] leading-relaxed">
                  {selectedAlert.description}
                </p>
              </div>

              {/* Structured Evidence Card */}
              <div className="bg-[#1b1b23] border border-[#292932] rounded p-3 space-y-2">
                <span className="text-[10px] font-mono text-[#908fa0] uppercase tracking-wider font-semibold block">
                  STRUCTURED EVIDENCE BREAKDOWN
                </span>
                <div className="space-y-1.5 text-xs font-mono">
                  {Object.entries(selectedAlert.evidence || {}).map(([key, val]) => (
                    <div key={key} className="flex justify-between py-1 border-b border-[#292932]/50">
                      <span className="text-[#908fa0] capitalize">{key.replace(/_/g, ' ')}:</span>
                      <span className="text-[#e4e1ed] font-semibold">
                        {typeof val === 'number' ? val.toString() : String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Cameras Involved */}
              <div className="space-y-2">
                <span className="text-[10px] font-mono text-[#908fa0] uppercase tracking-wider font-semibold block">
                  CAMERAS INVOLVED IN ANOMALY
                </span>
                <div className="space-y-1.5">
                  {selectedAlert.cameras_involved.map((cam) => (
                    <div
                      key={cam.id}
                      className="bg-[#1b1b23] p-2.5 rounded border border-[#292932] flex items-center justify-between text-xs font-mono"
                    >
                      <div className="flex items-center gap-2">
                        <MapPin className="w-3.5 h-3.5 text-[#38bdf8]" />
                        <span className="text-[#e4e1ed] font-semibold">{cam.name}</span>
                      </div>
                      <span className="text-[#908fa0]">Heading: {cam.direction || 'N/A'}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Resolution Notes if Resolved */}
              {selectedAlert.resolution_notes && (
                <div className="p-3 rounded bg-emerald-950/30 border border-emerald-500/30 text-xs font-mono space-y-1">
                  <span className="text-emerald-400 font-bold block">OPERATOR RESOLUTION NOTES:</span>
                  <p className="text-[#e4e1ed]">{selectedAlert.resolution_notes}</p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-3 border-t border-[#292932]">
                {selectedAlert.status === 'NEW' && (
                  <button
                    onClick={() => handleAcknowledge(selectedAlert.alert_id)}
                    className="flex-1 py-2 rounded bg-[#8083ff] hover:bg-[#8083ff]/90 text-[#0d0096] font-bold text-xs font-mono cursor-pointer transition-colors"
                  >
                    Acknowledge Alert
                  </button>
                )}
                {selectedAlert.status !== 'RESOLVED' && (
                  <button
                    onClick={() => handleOpenResolve(selectedAlert.alert_id)}
                    className="flex-1 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs font-mono cursor-pointer transition-colors"
                  >
                    Resolve Incident
                  </button>
                )}
                {selectedAlert.status !== 'DISMISSED' && (
                  <button
                    onClick={() => handleDismiss(selectedAlert.alert_id)}
                    className="px-3 py-2 rounded bg-[#1f1f27] hover:bg-[#292932] text-[#ffb4ab] text-xs font-mono cursor-pointer transition-colors"
                  >
                    Dismiss False Positive
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-[#908fa0] text-center p-8 space-y-2">
              <ShieldAlert className="w-8 h-8 text-[#464554]" />
              <p className="text-xs font-mono">
                Select an alert incident from the left to view complete explainability evidence and involved camera trajectories.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Operator Resolution Notes Modal */}
      {resolveModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-[2000] p-4">
          <div className="bg-[#13131b] border border-[#292932] rounded w-full max-w-md p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#292932]">
              <h3 className="font-bold text-sm text-[#e4e1ed]">Resolve Incident Case</h3>
              <button
                onClick={() => setResolveModalOpen(false)}
                className="text-[#908fa0] hover:text-[#e4e1ed] cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-mono text-[#908fa0] block">
                Operator Resolution Notes (Required for Audit Trail):
              </label>
              <textarea
                rows={4}
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                placeholder="e.g., Patrol unit intercepted vehicle at Brigade Road intersection. Stolen vehicle secured..."
                className="w-full bg-[#0d0d15] border border-[#292932] rounded p-2.5 text-xs text-[#e4e1ed] placeholder-[#908fa0] focus:outline-none focus:border-[#8083ff] font-mono"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setResolveModalOpen(false)}
                className="px-3 py-1.5 rounded bg-[#1f1f27] text-xs font-mono text-[#e4e1ed] cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmResolve}
                disabled={!resolutionNotes.trim()}
                className="px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-mono font-bold cursor-pointer transition-colors"
              >
                Confirm Resolution
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
