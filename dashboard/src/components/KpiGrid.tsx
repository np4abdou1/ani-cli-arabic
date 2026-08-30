"use client";

import React from "react";
import { Users, Play, TrendingUp, Zap, Radio, Sparkles, ArrowUpRight, Activity } from "lucide-react";
import { KpiStats } from "@/lib/types";

interface KpiGridProps {
  kpis: KpiStats;
}

export default function KpiGrid({ kpis }: KpiGridProps) {
  const cards = [
    {
      title: "Total Unique Users",
      value: kpis.totalUniqueUsers.toLocaleString(),
      change: "+233 this month",
      trend: "up",
      subtitle: "Hardware Device Fingerprints",
      icon: Users,
      color: "text-primary",
      glowColor: "from-primary/20 to-transparent",
      badgeColor: "bg-primary/10 text-primary border-primary/20",
    },
    {
      title: "Active Users (DAU / MAU)",
      value: `${kpis.dau} / ${kpis.mau}`,
      change: `${kpis.stickiness}% Stickiness`,
      trend: "up",
      subtitle: `${kpis.wau} weekly active users (WAU)`,
      icon: TrendingUp,
      color: "text-accent-green",
      glowColor: "from-accent-green/20 to-transparent",
      badgeColor: "bg-accent-green/10 text-accent-green border-accent-green/20",
    },
    {
      title: "Total Video Streams",
      value: kpis.totalStreams.toLocaleString(),
      change: "51.2% Conversion",
      trend: "up",
      subtitle: "Direct Playback & Resumes",
      icon: Play,
      color: "text-accent-cyan",
      glowColor: "from-accent-cyan/20 to-transparent",
      badgeColor: "bg-accent-cyan/10 text-accent-cyan border-accent-cyan/20",
    },
    {
      title: "Total App Launches",
      value: kpis.totalAppStarts.toLocaleString(),
      change: "24,000+ Total Events",
      trend: "up",
      subtitle: "CLI Sessions Initialized",
      icon: Zap,
      color: "text-accent-magenta",
      glowColor: "from-accent-magenta/20 to-transparent",
      badgeColor: "bg-accent-magenta/10 text-accent-magenta border-accent-magenta/20",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className="glass-panel glass-panel-hover rounded-3xl p-5 border border-white/5 relative overflow-hidden group cursor-default"
          >
            {/* Top Glow Ambient */}
            <div
              className={`absolute -top-12 -right-12 w-28 h-28 bg-gradient-to-br ${card.glowColor} rounded-full blur-2xl opacity-40 group-hover:opacity-80 transition-opacity`}
            />

            <div className="flex items-center justify-between mb-3 relative z-10">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                {card.title}
              </span>
              <div className={`p-2.5 rounded-2xl ${card.badgeColor} border`}>
                <Icon className={`w-4 h-4 ${card.color}`} />
              </div>
            </div>

            <div className="flex items-baseline gap-2 mb-1 relative z-10">
              <span className="text-3xl font-black text-white tracking-tight">
                {card.value}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs mt-3 pt-3 border-t border-white/5 relative z-10">
              <span className="text-slate-400 text-[11px] truncate">{card.subtitle}</span>
              <span className={`font-bold text-[11px] flex items-center gap-0.5 ${card.color}`}>
                <ArrowUpRight className="w-3 h-3" />
                {card.change}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
