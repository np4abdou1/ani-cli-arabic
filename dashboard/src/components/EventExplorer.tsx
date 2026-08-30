"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  Play,
  Zap,
  Search,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  User,
  Clock
} from "lucide-react";
import { TelemetryEvent } from "@/lib/types";
import { formatGmt1DateTime, timeAgo } from "@/lib/timezone";

interface EventExplorerProps {
  onSelectUser: (fingerprint: string) => void;
}

export default function EventExplorer({ onSelectUser }: EventExplorerProps) {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalEvents, setTotalEvents] = useState(0);

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [osFilter, setOsFilter] = useState("");

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: "20",
        action: actionFilter,
        os: osFilter,
        search: searchTerm
      });
      const res = await fetch(`/api/events?${params.toString()}`);
      if (res.ok) {
        const data = (await res.json()) as any;
        setEvents(data.events || []);
        setTotalPages(data.pagination?.totalPages || 1);
        setTotalEvents(data.pagination?.total || 0);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [page, actionFilter, osFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchEvents();
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-border">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Activity className="w-4 h-4 text-accent-cyan animate-pulse" />
            Live Telemetry Event Explorer (GMT+1)
          </h2>
          <p className="text-xs text-slate-400">
            Real-time feed of CLI executions, stream triggers, and client sessions ({totalEvents.toLocaleString()} total)
          </p>
        </div>

        {/* Filter Controls */}
        <form onSubmit={handleSearchSubmit} className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <div className="relative flex-1 sm:w-48">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search anime or user ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-surface border border-border rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-primary"
            />
          </div>

          <select
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(1);
            }}
            className="bg-surface border border-border rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-primary"
          >
            <option value="">All Actions</option>
            <option value="video_play">Video Streams</option>
            <option value="app_start">App Launches</option>
          </select>

          <select
            value={osFilter}
            onChange={(e) => {
              setOsFilter(e.target.value);
              setPage(1);
            }}
            className="bg-surface border border-border rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-primary"
          >
            <option value="">All OS</option>
            <option value="Linux">Linux</option>
            <option value="Windows">Windows</option>
            <option value="Darwin">macOS</option>
            <option value="Android">Android</option>
          </select>

          <button
            type="submit"
            className="p-1.5 bg-primary text-slate-900 font-bold rounded-xl text-xs hover:bg-primary-hover transition-colors"
          >
            <Search className="w-4 h-4" />
          </button>
        </form>
      </div>

      {/* Events Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-border/80 text-slate-400 font-semibold uppercase tracking-wider">
              <th className="pb-3 pl-2">Time (GMT+1)</th>
              <th className="pb-3">Action</th>
              <th className="pb-3">Details / Anime</th>
              <th className="pb-3">OS / Client</th>
              <th className="pb-3 text-right pr-2">User Fingerprint</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 font-mono">
            {loading ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-slate-400">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-primary" />
                  Streaming events from Cloudflare Edge...
                </td>
              </tr>
            ) : events.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">
                  No telemetry events match the filter
                </td>
              </tr>
            ) : (
              events.map((ev) => {
                const isStream = ev.action === "video_play";
                return (
                  <tr key={ev.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 pl-2 text-slate-400 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span>{formatGmt1DateTime(ev.timestamp)}</span>
                        <span className="text-[10px] text-slate-600">({timeAgo(ev.timestamp)})</span>
                      </div>
                    </td>
                    <td className="py-3">
                      {isStream ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 text-[11px] font-sans font-bold">
                          <Play className="w-3 h-3 fill-current" /> Stream
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-accent-magenta/15 text-accent-magenta border border-accent-magenta/30 text-[11px] font-sans font-semibold">
                          <Zap className="w-3 h-3" /> App Start
                        </span>
                      )}
                    </td>
                    <td className="py-3 font-sans text-slate-200">
                      {isStream ? (
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white max-w-xs md:max-w-md truncate">
                            {ev.anime || "Unknown Anime"}
                          </span>
                          {ev.episode && (
                            <span className="text-[11px] px-1.5 py-0.5 rounded bg-white/5 text-slate-300 font-mono">
                              Ep {ev.episode}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-slate-400 text-xs">CLI Session Initialized</span>
                      )}
                    </td>
                    <td className="py-3 font-sans">
                      <div className="flex items-center gap-2">
                        {ev.os && (
                          <span className="text-xs px-2 py-0.5 rounded bg-surface border border-border text-slate-300">
                            {ev.os}
                          </span>
                        )}
                        {ev.version && (
                          <span className="text-xs text-slate-500 font-mono">
                            {ev.version}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 text-right pr-2">
                      <button
                        onClick={() => onSelectUser(ev.fingerprint)}
                        className="inline-flex items-center gap-1.5 text-xs text-primary hover:text-primary-hover hover:underline font-mono bg-primary/10 hover:bg-primary/20 px-2 py-1 rounded-lg border border-primary/20 transition-colors"
                        title="Inspect User Watch History"
                      >
                        <User className="w-3 h-3" />
                        <span>{ev.fingerprint.slice(0, 10)}...</span>
                        <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/5 text-xs">
        <span className="text-slate-400">
          Page {page} of {totalPages} ({totalEvents.toLocaleString()} events)
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1 || loading}
            className="p-2 rounded-xl bg-surface border border-border text-slate-300 hover:text-white disabled:opacity-30"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages || loading}
            className="p-2 rounded-xl bg-surface border border-border text-slate-300 hover:text-white disabled:opacity-30"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
