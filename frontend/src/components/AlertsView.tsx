import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  MapPin,
  FileText,
  Filter
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
    <div className="p-4 space-y-4 overflow-y-auto h-full max-w-[1600px] mx-auto animate-slide-up">
      {/* Header & Filter Controls */}
      <div className="apple-card rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-xl">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h2 className="font-semibold text-sm text-[#f4f4f5] tracking-tight">
              Security & Anomaly Alert Center
            </h2>
            <span className="text-xs text-[#8e8e93] font-mono">
              {filteredAlerts.length} Active Events
            </span>
          </div>
        </div>

        {/* Filter Dropdowns */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 font-medium text-[#8e8e93] bg-[#18181f]/80 px-3 py-1.5 rounded-xl border border-white/[0.08]">
            <Filter className="w-3.5 h-3.5 text-emerald-400" />
            <span>Severity:</span>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="bg-transparent text-[#f4f4f5] font-semibold text-xs focus:outline-none cursor-pointer pr-1"
            >
              <option value="all" className="bg-[#121215]">All Severities</option>
              <option value="critical" className="bg-[#121215]">Critical</option>
              <option value="high" className="bg-[#121215]">High</option>
              <option value="moderate" className="bg-[#121215]">Moderate</option>
              <option value="low" className="bg-[#121215]">Low</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 font-medium text-[#8e8e93] bg-[#18181f]/80 px-3 py-1.5 rounded-xl border border-white/[0.08]">
            <span>Status:</span>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-transparent text-[#f4f4f5] font-semibold text-xs focus:outline-none cursor-pointer pr-1"
            >
              <option value="all" className="bg-[#121215]">All Statuses</option>
              <option value="NEW" className="bg-[#121215]">NEW</option>
              <option value="ACKNOWLEDGED" className="bg-[#121215]">ACKNOWLEDGED</option>
              <option value="RESOLVED" className="bg-[#121215]">RESOLVED</option>
              <option value="DISMISSED" className="bg-[#121215]">DISMISSED</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Alert Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
        {/* Left 7 Cols: Alert Table List */}
        <div className="lg:col-span-7 apple-card rounded-2xl overflow-hidden flex flex-col shadow-xl">
          <div className="p-3.5 border-b border-white/[0.08] flex items-center justify-between text-xs font-semibold text-[#8e8e93] uppercase tracking-wider">
            <span>ALERT INCIDENTS</span>
            <span>STATUS / ACTION</span>
          </div>

          <div className="divide-y divide-white/[0.06] overflow-y-auto">
            {filteredAlerts.length === 0 ? (
              <div className="p-8 text-center text-[#8e8e93] text-xs font-mono">
                No alerts matching current filters.
              </div>
            ) : (
              filteredAlerts.map((alert) => (
                <div
                  key={alert.id}
                  onClick={() => handleInspect(alert.id)}
                  className={`p-4 flex items-start justify-between gap-3 cursor-pointer transition-all duration-200 hover:bg-white/[0.04] ${
                    selectedAlert?.alert_id === alert.id ? 'bg-white/[0.06] border-l-2 border-emerald-500' : ''
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`p-2 rounded-xl shrink-0 mt-0.5 ${
                        alert.severity === 'critical'
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                          : alert.severity === 'high'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                          : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                      }`}
                    >
                      <AlertTriangle className="w-4 h-4" />
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-emerald-400">
                          {alert.alert_code}
                        </span>
                        <span
                          className={`text-[10px] font-bold uppercase px-2 py-0.2 rounded-full ${
                            alert.severity === 'critical'
                              ? 'bg-rose-500/20 text-rose-300'
                              : 'bg-amber-500/20 text-amber-300'
                          }`}
                        >
                          {alert.severity}
                        </span>
                        <span className="text-[11px] font-mono text-[#8e8e93]">
                          Conf: {(alert.confidence * 100).toFixed(1)}%
                        </span>
                      </div>

                      <h4 className="text-xs font-semibold text-[#f4f4f5] mt-1 tracking-tight">{alert.title}</h4>
                      <p className="text-xs text-[#a1a1aa] mt-0.5 line-clamp-2">
                        {alert.description}
                      </p>

                      <div className="flex items-center gap-4 mt-2 text-xs font-mono text-[#8e8e93]">
                        <span>Camera: {alert.camera_name || 'Network'}</span>
                        {alert.canonical_plate && (
                          <span className="text-cyan-400 font-bold">
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
                      className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase ${
                        alert.status === 'NEW'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30 animate-pulse'
                          : alert.status === 'ACKNOWLEDGED'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : alert.status === 'RESOLVED'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-white/[0.06] text-[#8e8e93]'
                      }`}
                    >
                      {alert.status}
                    </span>

                    <div className="flex items-center gap-1.5">
                      {alert.status === 'NEW' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAcknowledge(alert.id);
                          }}
                          className="px-2.5 py-1 rounded-lg bg-white/[0.08] hover:bg-white/[0.15] text-xs font-medium text-cyan-300 border border-white/[0.1] transition-all cursor-pointer active:scale-95"
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
                          className="px-2.5 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-xs font-medium text-emerald-300 border border-emerald-500/40 transition-all cursor-pointer active:scale-95"
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
        <div className="lg:col-span-5 apple-card rounded-2xl p-5 flex flex-col justify-between shadow-xl">
          {selectedAlert ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-emerald-400" />
                  <h3 className="font-semibold text-sm text-[#f4f4f5] tracking-tight">
                    Forensic Case File
                  </h3>
                </div>
                <span className="font-mono text-xs text-cyan-400 font-bold">
                  {selectedAlert.alert_code}
                </span>
              </div>

              {/* Title & Description */}
              <div className="space-y-1">
                <h4 className="text-sm font-semibold text-[#f4f4f5]">{selectedAlert.title}</h4>
                <p className="text-xs text-[#a1a1aa] leading-relaxed">
                  {selectedAlert.description}
                </p>
              </div>

              {/* Structured Evidence Card */}
              <div className="apple-subcard rounded-2xl p-3.5 space-y-2">
                <span className="text-[10px] font-semibold text-[#8e8e93] uppercase tracking-wider block">
                  STRUCTURED EVIDENCE BREAKDOWN
                </span>
                <div className="space-y-1.5 text-xs font-mono">
                  {Object.entries(selectedAlert.evidence || {}).map(([key, val]) => (
                    <div key={key} className="flex justify-between py-1 border-b border-white/[0.04]">
                      <span className="text-[#8e8e93] capitalize">{key.replace(/_/g, ' ')}:</span>
                      <span className="text-[#f4f4f5] font-semibold">
                        {typeof val === 'number' ? val.toString() : String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Cameras Involved */}
              <div className="space-y-2">
                <span className="text-[10px] font-semibold text-[#8e8e93] uppercase tracking-wider block">
                  CAMERAS INVOLVED IN ANOMALY
                </span>
                <div className="space-y-2">
                  {selectedAlert.cameras_involved.map((cam) => (
                    <div
                      key={cam.id}
                      className="apple-subcard p-2.5 rounded-xl flex items-center justify-between text-xs font-mono"
                    >
                      <div className="flex items-center gap-2">
                        <MapPin className="w-3.5 h-3.5 text-cyan-400" />
                        <span className="text-[#f4f4f5] font-semibold">{cam.name}</span>
                      </div>
                      <span className="text-[#8e8e93]">Heading: {cam.direction || 'N/A'}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Resolution Notes if Resolved */}
              {selectedAlert.resolution_notes && (
                <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs font-mono space-y-1">
                  <span className="text-emerald-400 font-bold block">OPERATOR RESOLUTION:</span>
                  <p className="text-[#f4f4f5]">{selectedAlert.resolution_notes}</p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-3 border-t border-white/[0.08]">
                {selectedAlert.status === 'NEW' && (
                  <button
                    onClick={() => handleAcknowledge(selectedAlert.alert_id)}
                    className="flex-1 py-2 rounded-xl apple-button-primary text-xs font-semibold cursor-pointer"
                  >
                    Acknowledge Alert
                  </button>
                )}
                {selectedAlert.status !== 'RESOLVED' && (
                  <button
                    onClick={() => handleOpenResolve(selectedAlert.alert_id)}
                    className="flex-1 py-2 rounded-xl apple-button-primary text-xs font-semibold cursor-pointer"
                  >
                    Resolve Incident
                  </button>
                )}
                {selectedAlert.status !== 'DISMISSED' && (
                  <button
                    onClick={() => handleDismiss(selectedAlert.alert_id)}
                    className="px-3.5 py-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-rose-400 border border-white/[0.08] text-xs font-semibold cursor-pointer transition-all active:scale-95"
                  >
                    Dismiss
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-[#8e8e93] text-center p-8 space-y-2">
              <ShieldAlert className="w-8 h-8 text-[#3f3f46]" />
              <p className="text-xs">
                Select an alert incident from the left to view complete explainability evidence and involved camera trajectories.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Operator Resolution Notes Modal */}
      {resolveModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[2000] p-4 animate-fade-in">
          <div className="apple-glass rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl border border-white/[0.15] animate-scale-in">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <h3 className="font-semibold text-sm text-[#f4f4f5]">Resolve Incident Case</h3>
              <button
                onClick={() => setResolveModalOpen(false)}
                className="w-6 h-6 rounded-full bg-white/[0.08] hover:bg-white/[0.15] text-[#8e8e93] hover:text-[#f4f4f5] flex items-center justify-center cursor-pointer text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2">
              <label className="text-xs text-[#8e8e93] block">
                Operator Resolution Notes (Required for Audit Trail):
              </label>
              <textarea
                rows={4}
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                placeholder="e.g., Patrol unit intercepted vehicle at Brigade Road intersection. Stolen vehicle secured..."
                className="w-full bg-[#18181f]/80 border border-white/[0.1] rounded-xl p-3 text-xs text-[#f4f4f5] placeholder-[#71717a] focus:outline-none focus:border-emerald-500 font-mono shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
              />
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setResolveModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-white/[0.08] hover:bg-white/[0.12] text-xs font-semibold text-[#f4f4f5] cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmResolve}
                disabled={!resolutionNotes.trim()}
                className="px-4 py-2 rounded-xl apple-button-primary disabled:opacity-50 text-xs font-semibold cursor-pointer"
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
