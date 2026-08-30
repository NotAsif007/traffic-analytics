import React, { useState, useEffect } from 'react';
import {
  ListOrdered,
  Plus,
  ShieldAlert,
  Search,
  CheckCircle,
  AlertTriangle,
  Clock,
  Trash2
} from 'lucide-react';
import { BlacklistEntry } from '../types/api';
import { api } from '../services/api';

export const WatchlistView: React.FC = () => {
  const [watchlist, setWatchlist] = useState<BlacklistEntry[]>([]);
  const [searchFilter, setSearchFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [newPlate, setNewPlate] = useState('');
  const [newReason, setNewReason] = useState('');
  const [newPriority, setNewPriority] = useState('critical');
  const [newNotes, setNewNotes] = useState('');

  const loadWatchlist = async () => {
    try {
      const data = await api.listWatchlist();
      setWatchlist(data);
    } catch (err) {
      console.error('Failed to load watchlist:', err);
    }
  };

  useEffect(() => {
    loadWatchlist();
  }, []);

  const handleAddEntry = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlate.trim() || !newReason.trim()) return;

    await api.addToWatchlist({
      plate_number: newPlate.trim().toUpperCase(),
      reason: newReason.trim(),
      priority: newPriority,
      notes: newNotes.trim() || undefined,
    });

    setWatchlist((prev) => [
      {
        id: `w-${Date.now()}`,
        plate_number: newPlate.trim().toUpperCase(),
        reason: newReason.trim(),
        priority: newPriority as any,
        is_active: true,
        created_at: new Date().toISOString(),
        notes: newNotes.trim(),
      },
      ...prev,
    ]);

    setNewPlate('');
    setNewReason('');
    setNewNotes('');
    setModalOpen(false);
  };

  const filtered = watchlist.filter(
    (w) =>
      w.plate_number.toLowerCase().includes(searchFilter.toLowerCase()) ||
      w.reason.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full max-w-[1600px] mx-auto">
      {/* Top Header & Search */}
      <div className="bg-[#13131b] border border-[#292932] rounded p-3.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ListOrdered className="w-5 h-5 text-[#8083ff]" />
          <h2 className="font-bold text-sm text-[#e4e1ed]">
            Law Enforcement Vehicle Watchlist / Blacklist
          </h2>
          <span className="px-2 py-0.5 rounded bg-[#1f1f27] border border-[#34343d] text-xs font-mono text-[#908fa0]">
            {watchlist.length} Monitored Vehicles
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#908fa0]" />
            <input
              type="text"
              placeholder="Filter by plate or reason..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="bg-[#0d0d15] border border-[#292932] rounded pl-8 pr-2.5 py-1 text-xs font-mono text-[#e4e1ed] placeholder-[#908fa0] focus:outline-none focus:border-[#8083ff] w-64"
            />
          </div>

          <button
            onClick={() => setModalOpen(true)}
            className="px-3 py-1.5 rounded bg-[#8083ff] hover:bg-[#8083ff]/90 text-[#0d0096] text-xs font-mono font-bold transition-colors cursor-pointer flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add to Watchlist</span>
          </button>
        </div>
      </div>

      {/* Watchlist Table */}
      <div className="bg-[#13131b] border border-[#292932] rounded overflow-hidden">
        <div className="grid grid-cols-12 p-3 border-b border-[#292932] text-xs font-mono text-[#908fa0] uppercase tracking-wider font-semibold">
          <div className="col-span-3">LICENSE PLATE</div>
          <div className="col-span-4">REASON & FIR DETAILS</div>
          <div className="col-span-2">PRIORITY</div>
          <div className="col-span-2">DATE ADDED</div>
          <div className="col-span-1 text-right">STATUS</div>
        </div>

        <div className="divide-y divide-[#1f1f27]">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-[#908fa0] text-xs font-mono">
              No watchlist entries found.
            </div>
          ) : (
            filtered.map((item) => (
              <div
                key={item.id}
                className="grid grid-cols-12 p-3.5 items-center text-xs font-mono transition-colors hover:bg-[#1b1b23]"
              >
                <div className="col-span-3 flex items-center gap-2">
                  <span className="px-2.5 py-1 rounded bg-[#0d0d15] border border-[#8083ff]/60 text-sm font-bold text-[#c0c1ff] tracking-wider">
                    {item.plate_number}
                  </span>
                </div>

                <div className="col-span-4">
                  <span className="text-[#e4e1ed] font-semibold block">{item.reason}</span>
                  {item.notes && (
                    <span className="text-[11px] text-[#908fa0] block mt-0.5">{item.notes}</span>
                  )}
                </div>

                <div className="col-span-2">
                  <span
                    className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                      item.priority === 'critical'
                        ? 'bg-rose-950 text-rose-400 border border-rose-500/30'
                        : item.priority === 'high'
                        ? 'bg-amber-950 text-amber-400 border border-amber-500/30'
                        : 'bg-[#1f1f27] text-[#c7c4d7]'
                    }`}
                  >
                    {item.priority}
                  </span>
                </div>

                <div className="col-span-2 text-[#908fa0]">
                  {new Date(item.created_at).toLocaleDateString()}
                </div>

                <div className="col-span-1 text-right">
                  <span className="text-[10px] font-bold text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-500/30">
                    ACTIVE
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Add To Watchlist Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-[2000] p-4">
          <form
            onSubmit={handleAddEntry}
            className="bg-[#13131b] border border-[#292932] rounded w-full max-w-md p-5 space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between pb-3 border-b border-[#292932]">
              <h3 className="font-bold text-sm text-[#e4e1ed]">Add Vehicle to Watchlist</h3>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="text-[#908fa0] hover:text-[#e4e1ed] cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-mono text-[#908fa0] block mb-1">
                  License Plate Number:
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. KA01MJ4040"
                  value={newPlate}
                  onChange={(e) => setNewPlate(e.target.value)}
                  className="w-full bg-[#0d0d15] border border-[#292932] rounded p-2 text-xs text-[#e4e1ed] font-mono uppercase focus:outline-none focus:border-[#8083ff]"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-[#908fa0] block mb-1">
                  Reason / FIR Incident:
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Stolen Vehicle (FIR #2026/842)"
                  value={newReason}
                  onChange={(e) => setNewReason(e.target.value)}
                  className="w-full bg-[#0d0d15] border border-[#292932] rounded p-2 text-xs text-[#e4e1ed] font-mono focus:outline-none focus:border-[#8083ff]"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-[#908fa0] block mb-1">
                  Priority Level:
                </label>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  className="w-full bg-[#0d0d15] border border-[#292932] rounded p-2 text-xs text-[#e4e1ed] font-mono focus:outline-none focus:border-[#8083ff]"
                >
                  <option value="critical">Critical (Immediate Alert)</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-mono text-[#908fa0] block mb-1">
                  Vehicle Description / Notes (Optional):
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. White Toyota Fortuner, tinted glass..."
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  className="w-full bg-[#0d0d15] border border-[#292932] rounded p-2 text-xs text-[#e4e1ed] font-mono focus:outline-none focus:border-[#8083ff]"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#292932]">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="px-3 py-1.5 rounded bg-[#1f1f27] text-xs font-mono text-[#e4e1ed] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded bg-[#8083ff] hover:bg-[#8083ff]/90 text-[#0d0096] text-xs font-mono font-bold cursor-pointer transition-colors"
              >
                Save to Watchlist
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
