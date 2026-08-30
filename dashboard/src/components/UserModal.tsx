"use client";

import React, { useEffect, useState } from "react";
import { X, User, Play, Clock, Zap, Film, Calendar, RefreshCw } from "lucide-react";
import { formatGmt1DateTime, timeAgo } from "@/lib/timezone";

interface UserModalProps {
  fingerprint: string | null;
  onClose: () => void;
}

export default function UserModal({ fingerprint, onClose }: UserModalProps) {
  const [userData, setUserData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!fingerprint) return;

    const fetchUser = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/user?fingerprint=${encodeURIComponent(fingerprint)}`);
        if (res.ok) {
          const data = (await res.json()) as any;
          setUserData(data);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [fingerprint]);

  if (!fingerprint) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="glass-panel w-full max-w-2xl rounded-3xl p-6 border border-border shadow-2xl relative overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-border mb-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 text-primary">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2 font-mono">
                {fingerprint.slice(0, 16)}...
              </h3>
              <p className="text-xs text-slate-400 font-mono text-ellipsis overflow-hidden max-w-xs sm:max-w-md">
                Fingerprint ID: {fingerprint}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-surface border border-border text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="py-16 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-3 text-primary" />
            Retrieving user profile and watch history from D1 database...
          </div>
        ) : userData ? (
          <div className="space-y-6 overflow-y-auto pr-1">
            {/* Quick Metrics */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3.5 rounded-2xl bg-surface/60 border border-white/5 text-center">
                <span className="text-[11px] text-slate-400 block mb-1">Total Streams</span>
                <span className="text-xl font-bold text-accent-cyan">
                  {userData.summary?.total_streams || 0}
                </span>
              </div>
              <div className="p-3.5 rounded-2xl bg-surface/60 border border-white/5 text-center">
                <span className="text-[11px] text-slate-400 block mb-1">App Launches</span>
                <span className="text-xl font-bold text-accent-magenta">
                  {userData.summary?.total_starts || 0}
                </span>
              </div>
              <div className="p-3.5 rounded-2xl bg-surface/60 border border-white/5 text-center">
                <span className="text-[11px] text-slate-400 block mb-1">Total Events</span>
                <span className="text-xl font-bold text-white">
                  {userData.summary?.total_events || 0}
                </span>
              </div>
            </div>

            {/* Timeline info */}
            <div className="p-4 rounded-2xl bg-surface/40 border border-white/5 text-xs space-y-2">
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-primary" /> First Seen (GMT+1):
                </span>
                <span className="font-mono">
                  {userData.summary?.first_seen ? formatGmt1DateTime(userData.summary.first_seen) : "N/A"}
                </span>
              </div>
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-accent-green" /> Last Seen (GMT+1):
                </span>
                <span className="font-mono">
                  {userData.summary?.last_seen ? formatGmt1DateTime(userData.summary.last_seen) : "N/A"}
                </span>
              </div>
            </div>

            {/* Watch History Log */}
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
                <Film className="w-3.5 h-3.5 text-primary" />
                Recent Watch History Log
              </h4>

              {userData.history?.length === 0 ? (
                <div className="p-4 text-center text-xs text-slate-500 rounded-xl bg-surface">
                  No stream history recorded yet for this client
                </div>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {userData.history.map((h: any, i: number) => (
                    <div
                      key={i}
                      className="flex items-center justify-between p-2.5 rounded-xl bg-surface/80 border border-white/5 text-xs hover:border-border transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <Play className="w-3.5 h-3.5 text-accent-cyan fill-current shrink-0" />
                        <span className="font-bold text-white max-w-xs truncate">{h.anime}</span>
                        {h.episode && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-slate-300 font-mono">
                            Ep {h.episode}
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-slate-400 font-mono">
                        {timeAgo(h.timestamp)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
