"use client";

import React, { useState, useEffect, useCallback } from "react";
import Header from "@/components/Header";
import KpiGrid from "@/components/KpiGrid";
import TrafficChart from "@/components/TrafficChart";
import TopAnimeTable from "@/components/TopAnimeTable";
import OsChart from "@/components/OsChart";
import VersionChart from "@/components/VersionChart";
import EventExplorer from "@/components/EventExplorer";
import UserModal from "@/components/UserModal";
import BroadcastManager from "@/components/BroadcastManager";
import { DashboardResponse } from "@/lib/types";
import { Activity, Flame, Radio, Zap, LayoutDashboard, Terminal, RefreshCw } from "lucide-react";

// Fallback initial data
const INITIAL_DATA: DashboardResponse = {
  kpis: {
    totalUniqueUsers: 1413,
    totalEvents: 24033,
    totalStreams: 12304,
    totalAppStarts: 11728,
    dau: 38,
    wau: 109,
    mau: 292,
    growthRate: 14.8,
    stickiness: 13.0,
  },
  growthSeries: [],
  topAnime: [],
  osBreakdown: [
    { os: "Linux", users: 1213, runs: 9012, percentage: 85.8 },
    { os: "Windows", users: 168, runs: 2238, percentage: 11.9 },
    { os: "macOS", users: 15, runs: 139, percentage: 1.1 },
    { os: "Android", users: 11, runs: 338, percentage: 0.8 },
  ],
  versionBreakdown: [
    { version: "v2.0.0", users: 20, runs: 65, percentage: 1.4 },
    { version: "v1.8.4", users: 580, runs: 4512, percentage: 38.5 },
    { version: "v1.8.2", users: 621, runs: 4007, percentage: 34.2 },
    { version: "v1.8", users: 215, runs: 1432, percentage: 12.2 },
  ],
  recentEvents: [],
  broadcast: {
    id: "",
    active: false,
    type: "banner",
    title: "",
    message: "",
    link: "",
    style: "cyan",
  },
  timeRange: "30d",
  serverTimeGmt1: new Date().toISOString(),
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardResponse>(INITIAL_DATA);
  const [loading, setLoading] = useState(false);
  const [timeRange, setTimeRange] = useState("30d");
  const [autoRefreshInterval, setAutoRefreshInterval] = useState(30);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "anime" | "events" | "broadcast">("overview");

  const fetchData = useCallback(async () => {
    if (typeof window === "undefined") return;
    setLoading(true);
    try {
      const res = await fetch(`/api/stats?range=${timeRange}`);
      if (res.ok) {
        const text = await res.text();
        if (text) {
          try {
            const json = JSON.parse(text);
            setData((prev) => ({ ...prev, ...json }));
          } catch (e) {}
        }
      }
    } catch (e) {
      console.warn("Using fallback state:", e);
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh interval
  useEffect(() => {
    if (autoRefreshInterval <= 0) return;
    const timer = setInterval(() => {
      fetchData();
    }, autoRefreshInterval * 1000);
    return () => clearInterval(timer);
  }, [autoRefreshInterval, fetchData]);

  return (
    <div className="min-h-screen bg-background text-slate-100 pb-16">
      {/* Top Header with GMT+1 clock & controls */}
      <Header
        timeRange={timeRange}
        setTimeRange={setTimeRange}
        onRefresh={fetchData}
        loading={loading}
        autoRefreshInterval={autoRefreshInterval}
        setAutoRefreshInterval={setAutoRefreshInterval}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 mb-6 border-b border-border/80 pb-3 overflow-x-auto">
          {[
            { id: "overview", label: "Executive Overview", icon: LayoutDashboard },
            { id: "anime", label: "Anime Leaderboard", icon: Flame },
            { id: "events", label: "Live Telemetry Feed", icon: Activity },
            { id: "broadcast", label: "Cloudflare Broadcast", icon: Radio },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                  isActive
                    ? "bg-primary text-slate-900 shadow-md shadow-primary/20"
                    : "text-slate-400 hover:text-white hover:bg-surface"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab 1: Executive Overview */}
        {activeTab === "overview" && (
          <div className="space-y-6 animate-in fade-in duration-300">
            {/* KPI Metric Cards */}
            <KpiGrid kpis={data.kpis} />

            {/* Main Area Chart */}
            <TrafficChart data={data.growthSeries} timeRange={timeRange} />

            {/* Secondary Row: Top 10 Anime + OS & Version Breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <TopAnimeTable animeList={data.topAnime} />
              </div>
              <div className="space-y-6">
                <OsChart osList={data.osBreakdown} />
                <VersionChart versionList={data.versionBreakdown} />
              </div>
            </div>

            {/* Recent Telemetry Stream preview */}
            <EventExplorer onSelectUser={(id) => setSelectedUser(id)} />
          </div>
        )}

        {/* Tab 2: Anime Leaderboard */}
        {activeTab === "anime" && (
          <div className="space-y-6 animate-in fade-in duration-300">
            <TopAnimeTable animeList={data.topAnime} />
          </div>
        )}

        {/* Tab 3: Full Event Explorer */}
        {activeTab === "events" && (
          <div className="space-y-6 animate-in fade-in duration-300">
            <EventExplorer onSelectUser={(id) => setSelectedUser(id)} />
          </div>
        )}

        {/* Tab 4: Broadcast Control */}
        {activeTab === "broadcast" && (
          <div className="space-y-6 animate-in fade-in duration-300 max-w-3xl mx-auto">
            <BroadcastManager
              initialBroadcast={data.broadcast}
              onUpdateSuccess={fetchData}
            />
          </div>
        )}
      </main>

      {/* User Deep-Dive Modal Drawer */}
      <UserModal
        fingerprint={selectedUser}
        onClose={() => setSelectedUser(null)}
      />
    </div>
  );
}
