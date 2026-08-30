"use client";

import React, { useState, useEffect } from "react";
import { Clock, RefreshCw, Search, Sparkles, Activity, ShieldCheck } from "lucide-react";
import { formatGmt1DateTime } from "@/lib/timezone";

interface HeaderProps {
  activeTab: string;
  timeRange: string;
  setTimeRange: (range: string) => void;
  onRefresh: () => void;
  loading: boolean;
  autoRefreshInterval: number;
  setAutoRefreshInterval: (interval: number) => void;
  onOpenSearch: () => void;
}

export default function Header({
  activeTab,
  timeRange,
  setTimeRange,
  onRefresh,
  loading,
  autoRefreshInterval,
  setAutoRefreshInterval,
  onOpenSearch,
}: HeaderProps) {
  const [clock, setClock] = useState<string>("");

  useEffect(() => {
    const updateTime = () => setClock(formatGmt1DateTime(new Date()));
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const getBreadcrumbTitle = (tab: string) => {
    switch (tab) {
      case "anime": return "Anime Leaderboard & Rankings";
      case "events": return "Live Telemetry Event Feed";
      case "users": return "User Directory & Watch Inspector";
      case "broadcast": return "Remote Announcements & Popups";
      case "health": return "System Health & Cloudflare Edge Status";
      default: return "Executive Metrics & Growth Overview";
    }
  };

  return (
    <header className="glass-panel sticky top-0 z-40 px-6 py-3.5 border-b border-border mb-6">
      <div className="flex flex-col lg:flex-row items-center justify-between gap-4">
        {/* Left: Breadcrumbs & Quick Search */}
        <div className="flex items-center gap-4 w-full lg:w-auto justify-between lg:justify-start">
          <div>
            <div className="flex items-center gap-2 text-[11px] text-slate-400 font-medium">
              <span>Platform</span>
              <span>/</span>
              <span className="text-primary font-semibold capitalize">{activeTab}</span>
            </div>
            <h2 className="text-base font-extrabold text-white tracking-tight">
              {getBreadcrumbTitle(activeTab)}
            </h2>
          </div>

          <button
            onClick={onOpenSearch}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-surface/80 hover:bg-card border border-border text-slate-400 hover:text-white transition-all text-xs group shadow-inner"
          >
            <Search className="w-3.5 h-3.5 group-hover:text-primary transition-colors" />
            <span className="hidden sm:inline">Search anything...</span>
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono bg-background rounded border border-border/80 text-slate-500 group-hover:text-primary">
              ⌘K
            </kbd>
          </button>
        </div>

        {/* Center/Right: GMT+1 Clock + Controls */}
        <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto justify-between lg:justify-end">
          {/* GMT+1 Clock Card */}
          <div className="flex items-center gap-3 bg-surface/90 px-3.5 py-1.5 rounded-xl border border-white/5 shadow-inner">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-green opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-green"></span>
              </span>
              <span className="text-[10px] font-bold text-accent-green tracking-wider">
                EDGE GMT+1
              </span>
            </div>
            <div className="h-3 w-px bg-border"></div>
            <div className="flex items-center gap-1.5 text-xs font-mono text-slate-200">
              <Clock className="w-3.5 h-3.5 text-primary" />
              <span>{clock || "Loading..."}</span>
            </div>
          </div>

          {/* Time Range Selector */}
          <div className="flex items-center bg-surface/90 p-1 rounded-xl border border-white/5">
            {["24h", "7d", "30d", "90d", "all"].map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                className={`px-2.5 py-1 text-xs font-bold rounded-lg transition-all ${
                  timeRange === r
                    ? "bg-primary text-slate-900 shadow-md shadow-primary/20"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {r.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Auto Refresh & Action */}
          <div className="flex items-center gap-2">
            <select
              value={autoRefreshInterval}
              onChange={(e) => setAutoRefreshInterval(Number(e.target.value))}
              className="bg-surface border border-border text-xs text-slate-300 rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-primary cursor-pointer"
            >
              <option value={0}>Auto: Off</option>
              <option value={10}>Auto: 10s</option>
              <option value={30}>Auto: 30s</option>
              <option value={60}>Auto: 60s</option>
            </select>

            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-2 bg-primary hover:bg-primary-hover text-slate-900 font-bold rounded-xl shadow-md shadow-primary/20 transition-all disabled:opacity-50"
              title="Refresh Data from Cloudflare Edge"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
