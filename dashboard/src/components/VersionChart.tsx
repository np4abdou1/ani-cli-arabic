"use client";

import React from "react";
import { GitBranch, CheckCircle2, AlertCircle } from "lucide-react";
import { VersionStat } from "@/lib/types";

interface VersionChartProps {
  versionList: VersionStat[];
}

export default function VersionChart({ versionList }: VersionChartProps) {
  return (
    <div className="glass-panel rounded-2xl p-6 border border-border">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-accent-magenta" />
            Client Version Adoption
          </h3>
          <p className="text-xs text-slate-400">Migration progress across installed releases</p>
        </div>
      </div>

      <div className="space-y-3">
        {versionList.map((v, idx) => {
          const isV2 = v.version.startsWith("v2") || v.version.startsWith("2");
          return (
            <div
              key={idx}
              className="p-3 rounded-xl bg-surface/50 border border-white/5 space-y-1.5"
            >
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white font-mono">{v.version}</span>
                  {isV2 ? (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent-green/20 text-accent-green border border-accent-green/30 font-semibold">
                      v2.0 Architecture
                    </span>
                  ) : (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-500/20 text-slate-400 border border-slate-500/30">
                      Legacy
                    </span>
                  )}
                </div>
                <span className="font-mono text-slate-300 font-bold">{v.percentage}%</span>
              </div>

              <div className="w-full h-1.5 bg-background rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    isV2
                      ? "bg-gradient-to-r from-accent-green to-emerald-400"
                      : "bg-gradient-to-r from-primary to-accent-magenta"
                  }`}
                  style={{ width: `${v.percentage}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>{v.users.toLocaleString()} users</span>
                <span>{v.runs.toLocaleString()} launches</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
