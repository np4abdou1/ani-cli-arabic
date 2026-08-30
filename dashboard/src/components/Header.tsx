"use client";

import React, { useState, useEffect } from "react";
import { Activity, Clock, RefreshCw, Radio, Sparkles } from "lucide-react";
import { formatGmt1DateTime, formatGmt1TimeOnly } from "@/lib/timezone";

interface HeaderProps {
  timeRange: string;
  setTimeRange: (range: string) => void;
  onRefresh: () => void;
  loading: boolean;
  autoRefreshInterval: number;
  setAutoRefreshInterval: (interval: number) => void;
}

export default function Header({
  timeRange,
  setTimeRange,
  onRefresh,
  loading,
  autoRefreshInterval,
  setAutoRefreshInterval,
}: HeaderProps) {
  const [clock, setClock] = useState<string>("");

  useEffect(() => {
    const updateTime = () => setClock(formatGmt1DateTime(new Date()));
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="glass-panel sticky top-0 z-40 px-6 py-4 border-b border-border mb-8">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Left: Brand / Title */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary via-indigo-600 to-accent-cyan flex items-center justify-center shadow-lg shadow-primary/20">
            <Activity className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                ani-cli-arabic
                <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-primary/20 text-primary border border-primary/30">
                  Command Center v2.0
                </span>
              </h1>
            </div>
            <p className="text-xs text-slate-400">
              Live Edge Telemetry & Analytics Platform
            </p>
          </div>
        </div>

        {/* Center: Live GMT+1 Clock & Status */}
        <div className="flex items-center gap-4 bg-background/60 px-4 py-2 rounded-xl border border-border/80">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-green opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-accent-green"></span>
            </span>
            <span className="text-xs font-semibold text-accent-green tracking-wide">
              SYSTEM ONLINE
            </span>
          </div>
          <div className="h-4 w-px bg-border"></div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
            <Clock className="w-3.5 h-3.5 text-primary" />
            <span>{clock || "Loading GMT+1..."}</span>
          </div>
        </div>

        {/* Right: Controls & Range Selector */}
        <div className="flex items-center gap-2">
          {/* Time Range Pills */}
          <div className="flex items-center bg-background/60 p-1 rounded-xl border border-border/80">
            {["24h", "7d", "30d", "90d", "all"].map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                className={`px-3 py-1 text-xs font-medium rounded-lg transition-all ${
                  timeRange === r
                    ? "bg-primary text-slate-900 font-bold shadow-md shadow-primary/30"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {r.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Auto-Refresh Select */}
          <select
            value={autoRefreshInterval}
            onChange={(e) => setAutoRefreshInterval(Number(e.target.value))}
            className="bg-card border border-border text-xs text-slate-300 rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-primary cursor-pointer"
          >
            <option value={0}>Auto: Off</option>
            <option value={10}>Auto: 10s</option>
            <option value={30}>Auto: 30s</option>
            <option value={60}>Auto: 60s</option>
          </select>

          {/* Manual Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 bg-card hover:bg-surface border border-border rounded-xl text-slate-300 hover:text-white transition-all disabled:opacity-50"
            title="Refresh Data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-primary" : ""}`} />
          </button>
        </div>
      </div>
    </header>
  );
}
