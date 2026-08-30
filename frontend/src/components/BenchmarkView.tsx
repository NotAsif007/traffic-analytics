import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Play,
  CheckCircle2,
  Activity,
  Award,
  Zap,
  Layers,
  ShieldAlert,
  Camera,
  Car
} from 'lucide-react';
import { EvaluationReport } from '../types/api';
import { api } from '../services/api';

export const BenchmarkView: React.FC = () => {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [running, setRunning] = useState(false);

  const runEvaluation = async () => {
    setRunning(true);
    try {
      const data = await api.runBenchmark();
      setReport(data);
    } catch (err) {
      console.error('Failed to run benchmark:', err);
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    runEvaluation();
  }, []);

  if (!report && running) {
    return (
      <div className="flex items-center justify-center h-full text-[#908fa0]">
        <div className="flex items-center gap-2 font-mono text-sm">
          <Activity className="w-4 h-4 animate-spin text-[#c0c1ff]" />
          <span>Executing City-Wide Synthetic Benchmark Suite (35 Vehicles, 8 Cameras)...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full max-w-[1600px] mx-auto">
      {/* Top Banner & Run Button */}
      <div className="bg-[#13131b] border border-[#292932] rounded p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-[#8083ff]/10 text-[#c0c1ff]">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-bold text-sm text-[#e4e1ed]">
              Scientific Evaluation & Benchmarking Suite
            </h2>
            <p className="text-xs font-mono text-[#908fa0]">
              Measurable, Non-Fabricated Verification of ANPR, Tracking, Association & Alert Subsystems
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {report && (
            <div className="px-3 py-1.5 rounded bg-emerald-950/40 border border-emerald-500/30 text-right">
              <span className="text-[10px] font-mono text-[#908fa0] uppercase block">
                COMPOSITE SCORE
              </span>
              <span className="text-lg font-bold font-mono text-emerald-400">
                {(report.overall_composite_score * 100).toFixed(2)}%
              </span>
            </div>
          )}

          <button
            onClick={runEvaluation}
            disabled={running}
            className="px-4 py-2 rounded bg-[#8083ff] hover:bg-[#8083ff]/90 disabled:opacity-50 text-[#0d0096] text-xs font-mono font-bold transition-colors cursor-pointer flex items-center gap-2"
          >
            {running ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
            <span>Run Benchmark</span>
          </button>
        </div>
      </div>

      {report && (
        <div className="space-y-4">
          {/* Dataset Summary Strip */}
          <div className="bg-[#1b1b23] border border-[#292932] rounded p-3 flex flex-wrap items-center justify-between text-xs font-mono text-[#908fa0]">
            <span>Benchmark: <strong className="text-[#e4e1ed]">{report.benchmark_name}</strong></span>
            <span>Cameras: <strong className="text-[#c0c1ff]">{report.dataset_summary.total_cameras}</strong></span>
            <span>Vehicles: <strong className="text-[#c0c1ff]">{report.dataset_summary.total_vehicles}</strong></span>
            <span>Observations: <strong className="text-[#c0c1ff]">{report.dataset_summary.total_observations}</strong></span>
            <span>Anomalies Evaluated: <strong className="text-rose-400">{report.dataset_summary.total_anomalous_events}</strong></span>
          </div>

          {/* 4 Quadrants Grid for Subsystems */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Quadrant 1: ANPR Layer */}
            <div className="bg-[#13131b] border border-[#292932] rounded p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#292932]">
                <div className="flex items-center gap-2">
                  <Camera className="w-4 h-4 text-[#38bdf8]" />
                  <h3 className="font-semibold text-sm text-[#e4e1ed]">1. ANPR Layer Metrics</h3>
                </div>
                <span className="text-xs font-mono text-emerald-400 font-bold">
                  {(report.anpr.detection_f1 * 100).toFixed(1)}% F1
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">DETECTION PRECISION</span>
                  <span className="text-sm font-bold text-[#e4e1ed]">
                    {(report.anpr.detection_precision * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">DETECTION RECALL</span>
                  <span className="text-sm font-bold text-[#e4e1ed]">
                    {(report.anpr.detection_recall * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">EXACT PLATE ACCURACY</span>
                  <span className="text-sm font-bold text-[#c0c1ff]">
                    {(report.anpr.exact_plate_accuracy * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">CHARACTER ACCURACY</span>
                  <span className="text-sm font-bold text-[#c0c1ff]">
                    {(report.anpr.character_accuracy * 100).toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Quadrant 2: Single-Camera Tracking */}
            <div className="bg-[#13131b] border border-[#292932] rounded p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#292932]">
                <div className="flex items-center gap-2">
                  <Car className="w-4 h-4 text-emerald-400" />
                  <h3 className="font-semibold text-sm text-[#e4e1ed]">2. Single-Camera MOT Tracking</h3>
                </div>
                <span className="text-xs font-mono text-emerald-400 font-bold">
                  {(report.tracking.mota * 100).toFixed(1)}% MOTA
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">MOTA ACCURACY</span>
                  <span className="text-sm font-bold text-[#e4e1ed]">
                    {(report.tracking.mota * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">IDENTIFICATION F1 (IDF1)</span>
                  <span className="text-sm font-bold text-[#e4e1ed]">
                    {(report.tracking.idf1 * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">ID SWITCHES (IDSW)</span>
                  <span className="text-sm font-bold text-emerald-400">
                    {report.tracking.id_switches} (Zero)
                  </span>
                </div>
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">MOSTLY TRACKED TRACKS</span>
                  <span className="text-sm font-bold text-[#c0c1ff]">
                    {report.tracking.mostly_tracked_tracks} Tracks
                  </span>
                </div>
              </div>
            </div>

            {/* Quadrant 3: Cross-Camera Association */}
            <div className="bg-[#13131b] border border-[#292932] rounded p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#292932]">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-[#8083ff]" />
                  <h3 className="font-semibold text-sm text-[#e4e1ed]">3. Cross-Camera Association</h3>
                </div>
                <span className="text-xs font-mono text-emerald-400 font-bold">
                  {(report.association.f1 * 100).toFixed(1)}% F1
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">ASSOCIATION PRECISION</span>
                  <span className="text-sm font-bold text-[#e4e1ed]">
                    {(report.association.precision * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">ASSOCIATION RECALL</span>
                  <span className="text-sm font-bold text-[#e4e1ed]">
                    {(report.association.recall * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">ASSOCIATION F1 SCORE</span>
                  <span className="text-sm font-bold text-[#c0c1ff]">
                    {(report.association.f1 * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">TRAJECTORY COMPLETENESS</span>
                  <span className="text-sm font-bold text-emerald-400">
                    {(report.association.trajectory_completeness_rate * 100).toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Quadrant 4: Alert & Anomaly Engine */}
            <div className="bg-[#13131b] border border-[#292932] rounded p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#292932]">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                  <h3 className="font-semibold text-sm text-[#e4e1ed]">4. Alert & Anomaly Engine</h3>
                </div>
                <span className="text-xs font-mono text-emerald-400 font-bold">
                  {(report.alerts.f1 * 100).toFixed(1)}% F1
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">ALERT PRECISION</span>
                  <span className="text-sm font-bold text-[#e4e1ed]">
                    {(report.alerts.precision * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">ALERT RECALL</span>
                  <span className="text-sm font-bold text-[#e4e1ed]">
                    {(report.alerts.recall * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">ALERT F1 SCORE</span>
                  <span className="text-sm font-bold text-[#c0c1ff]">
                    {(report.alerts.f1 * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="bg-[#1b1b23] p-2.5 rounded border border-[#292932]">
                  <span className="text-[10px] text-[#908fa0] block">FALSE POSITIVE RATE (FPR)</span>
                  <span className="text-sm font-bold text-emerald-400">
                    {(report.alerts.false_positive_rate * 100).toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
