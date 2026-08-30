import React, { useState, useEffect } from 'react';
import {
  Terminal,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  RefreshCw,
  Cpu,
  Database,
  Radio,
  ExternalLink
} from 'lucide-react';
import { api } from '../services/api';

interface DiagnosticsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DiagnosticsModal: React.FC<DiagnosticsModalProps> = ({ isOpen, onClose }) => {
  const [healthData, setHealthData] = useState<any>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [actionStatus, setActionStatus] = useState<string | null>(null);

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

  useEffect(() => {
    if (isOpen) {
      checkDiagnostics();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const sampleCurl = `curl -X GET http://localhost:8000/api/v1/dashboard/overview \\
  -H "Accept: application/json"`;

  const triggerTestAlert = async () => {
    setActionStatus('Simulating Blacklist Incident...');
    try {
      await api.addToWatchlist({
        plate_number: 'KA04XX9999',
        reason: 'Simulated Debug Trigger (Test Incident)',
        priority: 'critical',
      });
      setActionStatus('✓ Simulated Blacklist Alert Injected Successfully!');
      setTimeout(() => setActionStatus(null), 3000);
    } catch (err: any) {
      setActionStatus(`Error: ${err.message}`);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[3000] p-4">
      <div className="bg-[#13131b] border border-[#292932] rounded-lg w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 border-b border-[#292932] flex items-center justify-between bg-[#101017]">
          <div className="flex items-center gap-2">
            <Terminal className="w-5 h-5 text-[#8083ff]" />
            <div>
              <h3 className="font-bold text-sm text-[#e4e1ed] flex items-center gap-2">
                <span>System Diagnostics & Developer Console</span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#8083ff]/20 text-[#c0c1ff] border border-[#8083ff]/30">
                  DEBUG MODE
                </span>
              </h3>
              <p className="text-[11px] font-mono text-[#908fa0]">
                Real-time API telemetry, latency probes & test injectors
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={checkDiagnostics}
              disabled={loading}
              className="p-1.5 rounded bg-[#1f1f27] hover:bg-[#292932] text-[#c0c1ff] border border-[#34343d] transition-colors cursor-pointer"
              title="Refresh Health Probe"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="text-[#908fa0] hover:text-[#e4e1ed] px-2 py-1 text-sm cursor-pointer"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 overflow-y-auto text-xs font-mono">
          {/* Status Bar */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#1b1b23] p-3 rounded border border-[#292932] space-y-1">
              <span className="text-[10px] text-[#908fa0] block">BACKEND STATUS</span>
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    healthData?.status === 'ok' || healthData?.status === 'healthy'
                      ? 'bg-emerald-400 animate-pulse'
                      : 'bg-rose-400'
                  }`}
                />
                <span className="font-bold text-[#e4e1ed] uppercase">
                  {healthData?.status || 'OFFLINE'}
                </span>
              </div>
            </div>

            <div className="bg-[#1b1b23] p-3 rounded border border-[#292932] space-y-1">
              <span className="text-[10px] text-[#908fa0] block">API LATENCY</span>
              <span className="font-bold text-[#38bdf8]">
                {latencyMs !== null ? `${latencyMs} ms` : 'N/A'}
              </span>
            </div>

            <div className="bg-[#1b1b23] p-3 rounded border border-[#292932] space-y-1">
              <span className="text-[10px] text-[#908fa0] block">EVENT BUS</span>
              <span className="font-bold text-emerald-400">RESILIENT ACTIVE</span>
            </div>
          </div>

          {/* Raw Health JSON Response */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-[#908fa0] font-semibold">
                Live Backend Probe (`GET /api/v1/health`):
              </span>
              <button
                onClick={() => copyToClipboard(JSON.stringify(healthData, null, 2), 'health')}
                className="text-[10px] text-[#8083ff] hover:underline flex items-center gap-1 cursor-pointer"
              >
                {copiedKey === 'health' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedKey === 'health' ? 'Copied' : 'Copy JSON'}</span>
              </button>
            </div>
            <pre className="bg-[#0d0d15] p-3 rounded border border-[#292932] text-[#c7c4d7] overflow-x-auto text-[11px] max-h-32">
              {JSON.stringify(healthData || { info: 'Connecting...' }, null, 2)}
            </pre>
          </div>

          {/* Quick Interactive Test Injectors */}
          <div className="space-y-2 pt-2 border-t border-[#292932]">
            <span className="text-[11px] text-[#908fa0] font-semibold block">
              Developer Actions & Injectors:
            </span>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={triggerTestAlert}
                className="p-2.5 rounded bg-[#1b1b23] hover:bg-[#292932] border border-[#34343d] text-left transition-colors cursor-pointer group"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#e4e1ed] text-[11px] group-hover:text-[#c0c1ff]">
                    🚨 Inject Blacklist Trigger
                  </span>
                </div>
                <span className="text-[10px] text-[#908fa0] block mt-0.5">
                  Sends plate `KA04XX9999` to watchlists
                </span>
              </button>

              <button
                onClick={() => {
                  window.open('http://localhost:8000/docs', '_blank');
                }}
                className="p-2.5 rounded bg-[#1b1b23] hover:bg-[#292932] border border-[#34343d] text-left transition-colors cursor-pointer group"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#e4e1ed] text-[11px] group-hover:text-[#38bdf8] flex items-center gap-1">
                    📖 Open Swagger Docs <ExternalLink className="w-3 h-3" />
                  </span>
                </div>
                <span className="text-[10px] text-[#908fa0] block mt-0.5">
                  Interactive API documentation at :8000/docs
                </span>
              </button>
            </div>

            {actionStatus && (
              <div className="p-2 rounded bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 text-center font-bold text-[11px]">
                {actionStatus}
              </div>
            )}
          </div>

          {/* Useful cURL Samples */}
          <div className="space-y-1.5 pt-2 border-t border-[#292932]">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-[#908fa0] font-semibold">
                Reproducible cURL Command:
              </span>
              <button
                onClick={() => copyToClipboard(sampleCurl, 'curl')}
                className="text-[10px] text-[#8083ff] hover:underline flex items-center gap-1 cursor-pointer"
              >
                {copiedKey === 'curl' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedKey === 'curl' ? 'Copied' : 'Copy cURL'}</span>
              </button>
            </div>
            <pre className="bg-[#0d0d15] p-2.5 rounded border border-[#292932] text-[#908fa0] text-[10px] overflow-x-auto">
              {sampleCurl}
            </pre>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-[#101017] border-t border-[#292932] flex items-center justify-between text-[11px] font-mono text-[#908fa0]">
          <span>Run CLI Doctor: <code className="text-[#c0c1ff]">python tools/doctor.py</code></span>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded bg-[#8083ff] text-[#0d0096] font-bold cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
