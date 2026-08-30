"use client";

import React from "react";
import {
  LayoutDashboard,
  Flame,
  Activity,
  Users,
  Radio,
  Server,
  ChevronLeft,
  ChevronRight,
  Github,
  ExternalLink,
  ShieldCheck,
  Terminal
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: any) => void;
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
  totalUsers: number;
  totalEvents: number;
  isBroadcastActive: boolean;
}

export default function Sidebar({
  activeTab,
  setActiveTab,
  collapsed,
  setCollapsed,
  totalUsers,
  totalEvents,
  isBroadcastActive,
}: SidebarProps) {
  const navItems = [
    {
      id: "overview",
      label: "Overview",
      icon: LayoutDashboard,
      badge: null,
      color: "text-primary",
    },
    {
      id: "anime",
      label: "Anime Rankings",
      icon: Flame,
      badge: "Top 20",
      color: "text-accent-pink",
    },
    {
      id: "events",
      label: "Live Telemetry",
      icon: Activity,
      badge: "LIVE",
      badgeColor: "bg-accent-cyan/20 text-accent-cyan border-accent-cyan/30 animate-pulse",
      color: "text-accent-cyan",
    },
    {
      id: "users",
      label: "Users Directory",
      icon: Users,
      badge: `${(totalUsers / 1000).toFixed(1)}k`,
      color: "text-accent-green",
    },
    {
      id: "broadcast",
      label: "Broadcast & Popups",
      icon: Radio,
      badge: isBroadcastActive ? "ACTIVE" : null,
      badgeColor: "bg-accent-green/20 text-accent-green border-accent-green/30",
      color: "text-accent-yellow",
    },
    {
      id: "health",
      label: "System & Database",
      icon: Server,
      badge: "D1",
      color: "text-accent-magenta",
    },
  ];

  return (
    <aside
      className={`fixed top-0 left-0 bottom-0 z-50 glass-panel border-r border-border flex flex-col justify-between transition-all duration-300 ${
        collapsed ? "w-20" : "w-64"
      }`}
    >
      {/* Top: Branding */}
      <div>
        <div className="p-4 border-b border-border/80 flex items-center justify-between">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-primary via-indigo-600 to-accent-cyan flex items-center justify-center shadow-lg shadow-primary/25 shrink-0 group">
              <Terminal className="w-5 h-5 text-white transition-transform group-hover:scale-110" />
            </div>
            {!collapsed && (
              <div className="animate-in fade-in duration-200">
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-sm text-white tracking-tight">
                    ani-cli-ar
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold bg-primary/20 text-primary border border-primary/30">
                    v2.0
                  </span>
                </div>
                <span className="text-[11px] text-slate-400 block font-mono">
                  Command Center
                </span>
              </div>
            )}
          </div>

          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-xl bg-surface hover:bg-card border border-border text-slate-400 hover:text-white transition-colors"
            title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl text-xs font-semibold transition-all group relative ${
                  isActive
                    ? "bg-primary text-slate-900 shadow-lg shadow-primary/25 font-bold"
                    : "text-slate-400 hover:text-white hover:bg-surface/80"
                }`}
                title={collapsed ? item.label : undefined}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 transition-transform group-hover:scale-110 ${
                    isActive ? "text-slate-900" : item.color
                  }`}
                />
                {!collapsed && (
                  <span className="truncate flex-1 text-left">{item.label}</span>
                )}
                {!collapsed && item.badge && (
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                      item.badgeColor || (isActive ? "bg-slate-900/20 text-slate-900 border-slate-900/30" : "bg-white/5 text-slate-300 border-white/10")
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom: Cloudflare & GitHub Status */}
      <div className="p-3 border-t border-border/80 space-y-2">
        {!collapsed && (
          <div className="p-3 rounded-2xl bg-surface/60 border border-white/5 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-slate-400 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-accent-green" /> Cloudflare D1
              </span>
              <span className="text-[10px] font-mono text-accent-green font-bold">
                ONLINE
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>Events Ingested:</span>
              <span className="font-mono text-white font-bold">
                {totalEvents.toLocaleString()}
              </span>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between gap-1">
          <a
            href="https://github.com/np4abdou1/ani-cli-arabic"
            target="_blank"
            rel="noreferrer"
            className={`flex items-center gap-2 p-2 rounded-xl bg-surface hover:bg-card border border-border text-slate-400 hover:text-white transition-colors text-xs ${
              collapsed ? "w-full justify-center" : "flex-1"
            }`}
            title="GitHub Repository"
          >
            <Github className="w-4 h-4 shrink-0" />
            {!collapsed && <span className="truncate">GitHub Repo</span>}
            {!collapsed && <ExternalLink className="w-3 h-3 ml-auto opacity-50" />}
          </a>
        </div>
      </div>
    </aside>
  );
}
