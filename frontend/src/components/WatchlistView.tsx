import React, { useState, useEffect } from 'react';
import {
  ListOrdered,
  Plus,
  Search
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

    try {
      await api.addToWatchlist({
        plate_number: newPlate.trim().toUpperCase(),
        plate_text: newPlate.trim().toUpperCase(),
        reason: newReason.trim(),
        priority: newPriority,
        notes: newNotes.trim() || undefined,
      });
      await loadWatchlist();
    } catch (err) {
      console.error('Failed to add entry:', err);
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
    }

    setNewPlate('');
    setNewReason('');
    setNewNotes('');
    setModalOpen(false);
  };

  const filtered = watchlist.filter((w) => {
    const plate = w.plate_number || (w as any).plate_text || '';
    const reason = w.reason || '';
    return (
      plate.toLowerCase().includes(searchFilter.toLowerCase()) ||
      reason.toLowerCase().includes(searchFilter.toLowerCase())
    );
  });

  return (
    <div className="p-4 space-y-4 overflow-y-auto h-full max-w-[1600px] mx-auto animate-slide-up">
      {/* Top Header & Search */}
      <div className="apple-card rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-xl">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ListOrdered className="w-4 h-4" />
          </div>
          <div>
            <h2 className="font-semibold text-sm text-[#f4f4f5] tracking-tight">
              Law Enforcement Vehicle Watchlist / Blacklist
            </h2>
            <span className="text-xs text-[#8e8e93] font-mono">
              {watchlist.length} Monitored Vehicles
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#71717a]" />
            <input
              type="text"
              placeholder="Filter by plate or FIR..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="bg-[#18181f]/80 border border-white/[0.08] rounded-xl pl-9 pr-3 py-1.5 text-xs text-[#f4f4f5] placeholder-[#71717a] focus:outline-none focus:border-emerald-500/60 font-mono w-64 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
            />
          </div>

          <button
            onClick={() => setModalOpen(true)}
            className="px-4 py-2 rounded-xl apple-button-primary text-xs font-semibold flex items-center gap-1.5 cursor-pointer active:scale-95 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add Vehicle</span>
          </button>
        </div>
      </div>

      {/* Watchlist Table */}
      <div className="apple-card rounded-2xl overflow-hidden shadow-xl">
        <div className="grid grid-cols-12 p-4 border-b border-white/[0.08] text-xs font-semibold text-[#8e8e93] uppercase tracking-wider">
          <div className="col-span-3">LICENSE PLATE</div>
          <div className="col-span-4">REASON & FIR DETAILS</div>
          <div className="col-span-2">PRIORITY</div>
          <div className="col-span-2">DATE ADDED</div>
          <div className="col-span-1 text-right">STATUS</div>
        </div>

        <div className="divide-y divide-white/[0.06]">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-[#8e8e93] text-xs font-mono">
              No watchlist entries found.
            </div>
          ) : (
            filtered.map((item) => (
              <div
                key={item.id}
                className="grid grid-cols-12 p-4 items-center text-xs font-mono transition-all hover:bg-white/[0.04]"
              >
                <div className="col-span-3 flex items-center gap-2">
                  <span className="px-3 py-1.5 rounded-xl bg-[#18181f] border border-emerald-500/40 text-sm font-bold text-emerald-400 tracking-wider shadow-sm">
                    {item.plate_number || (item as any).plate_text || 'UNKNOWN'}
                  </span>
                </div>

                <div className="col-span-4 font-sans">
                  <span className="text-[#f4f4f5] font-semibold block">{item.reason}</span>
                  {item.notes && (
                    <span className="text-xs text-[#8e8e93] block mt-0.5">{item.notes}</span>
                  )}
                </div>

                <div className="col-span-2">
                  <span
                    className={`text-[10px] uppercase font-bold px-2.5 py-0.5 rounded-full ${
                      item.priority === 'critical'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        : item.priority === 'high'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        : 'bg-white/[0.06] text-[#a1a1aa]'
                    }`}
                  >
                    {item.priority}
                  </span>
                </div>

                <div className="col-span-2 text-[#8e8e93]">
                  {new Date(item.created_at).toLocaleDateString()}
                </div>

                <div className="col-span-1 text-right">
                  <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/15 px-2 py-0.5 rounded-full border border-emerald-500/30">
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
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[2000] p-4 animate-fade-in">
          <form
            onSubmit={handleAddEntry}
            className="apple-glass rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl border border-white/[0.15] animate-scale-in"
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <h3 className="font-semibold text-sm text-[#f4f4f5]">Add Vehicle to Watchlist</h3>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="w-6 h-6 rounded-full bg-white/[0.08] hover:bg-white/[0.15] text-[#8e8e93] hover:text-[#f4f4f5] flex items-center justify-center cursor-pointer text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3.5">
              <div>
                <label className="text-xs text-[#8e8e93] block mb-1.5 font-medium">
                  License Plate Number:
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. KA01MJ4040"
                  value={newPlate}
                  onChange={(e) => setNewPlate(e.target.value)}
                  className="w-full bg-[#18181f]/80 border border-white/[0.1] rounded-xl p-2.5 text-xs text-[#f4f4f5] font-mono uppercase focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs text-[#8e8e93] block mb-1.5 font-medium">
                  Reason / FIR Incident:
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Stolen Vehicle (FIR #2026/842)"
                  value={newReason}
                  onChange={(e) => setNewReason(e.target.value)}
                  className="w-full bg-[#18181f]/80 border border-white/[0.1] rounded-xl p-2.5 text-xs text-[#f4f4f5] focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs text-[#8e8e93] block mb-1.5 font-medium">
                  Priority Level:
                </label>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  className="w-full bg-[#18181f] border border-white/[0.1] rounded-xl p-2.5 text-xs text-[#f4f4f5] focus:outline-none focus:border-emerald-500 cursor-pointer"
                >
                  <option value="critical" className="bg-[#121215]">Critical (Immediate Alert)</option>
                  <option value="high" className="bg-[#121215]">High</option>
                  <option value="medium" className="bg-[#121215]">Medium</option>
                  <option value="low" className="bg-[#121215]">Low</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-[#8e8e93] block mb-1.5 font-medium">
                  Vehicle Description / Notes (Optional):
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. White Toyota Fortuner, tinted glass..."
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  className="w-full bg-[#18181f]/80 border border-white/[0.1] rounded-xl p-2.5 text-xs text-[#f4f4f5] focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/[0.08]">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-white/[0.08] hover:bg-white/[0.12] text-xs font-semibold text-[#f4f4f5] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-xl apple-button-primary text-xs font-semibold cursor-pointer"
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
