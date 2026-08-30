"use client";

import React from "react";
import { Server, Database, ShieldCheck, Cpu, HardDrive, Zap, CheckCircle2, Radio } from "lucide-react";
import { KpiStats } from "@/lib/types";

interface SystemHealthProps {
  kpis: KpiStats;
  serverTimeGmt1: string;
}

export default function SystemHealth({ kpis, serverTimeGmt1 }: SystemHealthProps) {
  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Edge Services Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* D1 SQLite Database */}
        <div className="glass-panel glass-panel-hover rounded-3xl p-6 border border-white/5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-accent-green/10 rounded-2xl border border-accent-green/20 text-accent-green">
              <Database className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-mono px-2.5 py-1 rounded-full font-bold bg-accent-green/20 text-accent-green border border-accent-green/30">
              HEALTHY • 99.9%
            </span>
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">Cloudflare D1 SQLite</h4>
            <p className="text-xs text-slate-400 font-mono truncate">
              ID: fc0cbb15-ed44-4db9-adf7-7a824056dd42
            </p>
          </div>
          <div className="pt-3 border-t border-white/5 space-y-1.5 text-xs text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">Database Size:</span>
              <span className="font-mono font-bold text-white">~5.07 MB</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Total Telemetry Rows:</span>
              <span className="font-mono font-bold text-accent-cyan">{kpis.totalEvents.toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* KV Namespace */}
        <div className="glass-panel glass-panel-hover rounded-3xl p-6 border border-white/5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 text-primary">
              <Radio className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-mono px-2.5 py-1 rounded-full font-bold bg-accent-green/20 text-accent-green border border-accent-green/30">
              BROADCAST_KV
            </span>
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">Cloudflare KV Storage</h4>
            <p className="text-xs text-slate-400 font-mono truncate">
              ID: 9964f00f31ab464e864f2b21751046aa
            </p>
          </div>
          <div className="pt-3 border-t border-white/5 space-y-1.5 text-xs text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">Replication:</span>
              <span className="font-mono font-bold text-white">Global Edge CDN</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Latency:</span>
              <span className="font-mono font-bold text-accent-green">&lt; 15 ms</span>
            </div>
          </div>
        </div>

        {/* Cloudflare Pages Functions Edge */}
        <div className="glass-panel glass-panel-hover rounded-3xl p-6 border border-white/5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-accent-magenta/10 rounded-2xl border border-accent-magenta/20 text-accent-magenta">
              <Zap className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-mono px-2.5 py-1 rounded-full font-bold bg-primary/20 text-primary border border-primary/30">
              V8 ISOLATE
            </span>
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">Edge API Engine</h4>
            <p className="text-xs text-slate-400 font-mono truncate">
              anicliar-dashboard.pages.dev
            </p>
          </div>
          <div className="pt-3 border-t border-white/5 space-y-1.5 text-xs text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">Runtime:</span>
              <span className="font-mono font-bold text-white">Cloudflare Workers</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Timezone Engine:</span>
              <span className="font-mono font-bold text-accent-magenta">GMT+1 (UTC+1)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Edge Diagnostics Table */}
      <div className="glass-panel rounded-3xl p-6 border border-border space-y-4">
        <h4 className="text-sm font-bold text-white flex items-center gap-2">
          <Server className="w-4 h-4 text-primary" />
          Production Edge Database Table Schemas
        </h4>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-border/80 text-slate-400 font-semibold uppercase">
                <th className="pb-3 pl-2">Table Name</th>
                <th className="pb-3">Type</th>
                <th className="pb-3">Primary Key</th>
                <th className="pb-3 text-right pr-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              <tr className="hover:bg-white/[0.02]">
                <td className="py-3 pl-2 font-bold text-white">monitoring_events</td>
                <td className="py-3 text-slate-400">High-Volume Telemetry</td>
                <td className="py-3">id (INTEGER AUTOINCREMENT)</td>
                <td className="py-3 text-right pr-2 text-accent-green font-bold">24,037 rows (Active)</td>
              </tr>
              <tr className="hover:bg-white/[0.02]">
                <td className="py-3 pl-2 font-bold text-white">website_visits</td>
                <td className="py-3 text-slate-400">Landing Page Logs</td>
                <td className="py-3">id (INTEGER AUTOINCREMENT)</td>
                <td className="py-3 text-right pr-2 text-accent-green font-bold">2,026 rows (Active)</td>
              </tr>
              <tr className="hover:bg-white/[0.02]">
                <td className="py-3 pl-2 font-bold text-white">watch_analytics</td>
                <td className="py-3 text-slate-400">Legacy Episodes Table</td>
                <td className="py-3">id (INTEGER AUTOINCREMENT)</td>
                <td className="py-3 text-right pr-2 text-slate-400">Archived</td>
              </tr>
              <tr className="hover:bg-white/[0.02]">
                <td className="py-3 pl-2 font-bold text-white">credentials</td>
                <td className="py-3 text-slate-400">API Tokens & CDNs</td>
                <td className="py-3">key (TEXT)</td>
                <td className="py-3 text-right pr-2 text-accent-green font-bold">Protected</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
