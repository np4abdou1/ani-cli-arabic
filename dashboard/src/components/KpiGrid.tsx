"use client";

import React from "react";
import { Users, Play, Radio, TrendingUp, Zap, Sparkles, MonitorSmartphone } from "lucide-react";
import { KpiStats } from "@/lib/types";

interface KpiGridProps {
  kpis: KpiStats;
}

export default function KpiGrid({ kpis }: KpiGridProps) {
  const cards = [
    {
      title: "Total Unique Users",
      value: kpis.totalUniqueUsers.toLocaleString(),
      change: "+233 this mo",
      subtitle: "Unique Hardware Fingerprints",
      icon: Users,
      color: "text-primary",
      bg: "bg-primary/10",
      border: "border-primary/20",
    },
    {
      title: "Active Users (DAU / MAU)",
      value: `${kpis.dau} / ${kpis.mau}`,
      change: `${kpis.stickiness}% Stickiness`,
      subtitle: `${kpis.wau} active past 7 days`,
      icon: TrendingUp,
      color: "text-accent-green",
      bg: "bg-accent-green/10",
      border: "border-accent-green/20",
    },
    {
      title: "Total Video Streams",
      value: kpis.totalStreams.toLocaleString(),
      change: "51.2% Conversion",
      subtitle: "Direct Anime Streams & Resumes",
      icon: Play,
      color: "text-accent-cyan",
      bg: "bg-accent-cyan/10",
      border: "border-accent-cyan/20",
    },
    {
      title: "Total App Executions",
      value: kpis.totalAppStarts.toLocaleString(),
      change: "24,000+ Total Events",
      subtitle: "CLI Sessions Launched",
      icon: Zap,
      color: "text-accent-magenta",
      bg: "bg-accent-magenta/10",
      border: "border-accent-magenta/20",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`glass-panel glass-panel-hover rounded-2xl p-5 border ${card.border} transition-all duration-300 relative overflow-hidden group`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                {card.title}
              </span>
              <div className={`p-2.5 rounded-xl ${card.bg} ${card.color}`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>

            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                {card.value}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs mt-3 pt-3 border-t border-white/5">
              <span className="text-slate-400 truncate">{card.subtitle}</span>
              <span className={`font-semibold ${card.color} shrink-0`}>
                {card.change}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
