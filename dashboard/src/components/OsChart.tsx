"use client";

import React from "react";
import { Monitor, Smartphone, Terminal, Apple, Laptop } from "lucide-react";
import { OsStat } from "@/lib/types";

interface OsChartProps {
  osList: OsStat[];
}

export default function OsChart({ osList }: OsChartProps) {
  const getOsIcon = (name: string) => {
    const l = name.toLowerCase();
    if (l.includes("linux")) return Terminal;
    if (l.includes("windows")) return Laptop;
    if (l.includes("darwin") || l.includes("mac")) return Apple;
    if (l.includes("android")) return Smartphone;
    return Monitor;
  };

  const getOsColor = (idx: number) => {
    const colors = ["bg-accent-green", "bg-primary", "bg-accent-magenta", "bg-accent-yellow", "bg-accent-pink"];
    return colors[idx % colors.length];
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-border">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Monitor className="w-4 h-4 text-primary" />
            Operating System Share
          </h3>
          <p className="text-xs text-slate-400">Distribution of active client platforms</p>
        </div>
      </div>

      {/* Progress Bar Spectrum */}
      <div className="w-full h-3 bg-surface rounded-full overflow-hidden flex gap-0.5 mb-6 p-0.5 border border-border">
        {osList.map((o, idx) => (
          <div
            key={idx}
            className={`h-full rounded-sm ${getOsColor(idx)} transition-all`}
            style={{ width: `${o.percentage}%` }}
            title={`${o.os}: ${o.percentage}%`}
          />
        ))}
      </div>

      {/* OS Metrics Grid */}
      <div className="space-y-3">
        {osList.map((o, idx) => {
          const Icon = getOsIcon(o.os);
          return (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 rounded-xl bg-surface/50 border border-white/5 hover:border-border transition-colors text-xs"
            >
              <div className="flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full ${getOsColor(idx)}`} />
                <Icon className="w-4 h-4 text-slate-300" />
                <span className="font-medium text-white">{o.os}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-slate-400 font-mono">{o.runs.toLocaleString()} runs</span>
                <span className="font-bold text-white font-mono min-w-10 text-right">
                  {o.percentage}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
