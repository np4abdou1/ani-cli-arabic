"use client";

import React, { useState, useEffect, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import KpiGrid from "@/components/KpiGrid";
import TrafficChart from "@/components/TrafficChart";
import TopAnimeTable from "@/components/TopAnimeTable";
import OsChart from "@/components/OsChart";
import VersionChart from "@/components/VersionChart";
import EventExplorer from "@/components/EventExplorer";
import UserModal from "@/components/UserModal";
import BroadcastManager from "@/components/BroadcastManager";
import SystemHealth from "@/components/SystemHealth";
import SearchModal from "@/components/SearchModal";
import { DashboardResponse } from "@/lib/types";

const INITIAL_DATA: DashboardResponse = {
  kpis: {
    totalUniqueUsers: 1413,
    totalEvents: 24037,
    totalStreams: 12308,
    totalAppStarts: 11729,
    dau: 45,
    wau: 109,
    mau: 297,
    growthRate: 14.8,
    stickiness: 15.2,
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
    id: "sample-popup-1",
    active: true,
    type: "popup",
    title: "🚀 Welcome to ani-cli-arabic v2.0",
    message: "Welcome to the brand new **v2.0 Multi-Provider Update**!\n\n◆ 4 Streaming engines: Anime3rb, Anime Slayer, Animeify, and AniDB\n◆ Real-Time MPV playback resumption\n◆ Instant auto-updater and zero-latency search",
    link: "https://github.com/np4abdou1/ani-cli-arabic",
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
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

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
      console.warn("Using offline fallback:", e);
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh timer
  useEffect(() => {
    if (autoRefreshInterval <= 0) return;
    const timer = setInterval(() => {
      fetchData();
    }, autoRefreshInterval * 1000);
    return () => clearInterval(timer);
  }, [autoRefreshInterval, fetchData]);

  return (
    <div className="min-h-screen bg-background text-slate-100 flex">
      {/* Collapsible Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
        totalUsers={data.kpis.totalUniqueUsers}
        totalEvents={data.kpis.totalEvents}
        isBroadcastActive={Boolean(data.broadcast?.active)}
      />

      {/* Main App Content Area */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${
          sidebarCollapsed ? "pl-20" : "pl-64"
        }`}
      >
        {/* Top Header */}
        <Header
          activeTab={activeTab}
          timeRange={timeRange}
          setTimeRange={setTimeRange}
          onRefresh={fetchData}
          loading={loading}
          autoRefreshInterval={autoRefreshInterval}
          setAutoRefreshInterval={setAutoRefreshInterval}
          onOpenSearch={() => setIsSearchOpen(true)}
        />

        {/* Dynamic Page Views */}
        <main className="flex-1 px-6 pb-16 max-w-[1600px] w-full mx-auto">
          {/* Tab 1: Executive Overview */}
          {activeTab === "overview" && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <KpiGrid kpis={data.kpis} />
              <TrafficChart data={data.growthSeries} timeRange={timeRange} />
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <TopAnimeTable animeList={data.topAnime} />
                </div>
                <div className="space-y-6">
                  <OsChart osList={data.osBreakdown} />
                  <VersionChart versionList={data.versionBreakdown} />
                </div>
              </div>
              <EventExplorer onSelectUser={(id) => setSelectedUser(id)} />
            </div>
          )}

          {/* Tab 2: Anime Rankings */}
          {activeTab === "anime" && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <TopAnimeTable animeList={data.topAnime} />
            </div>
          )}

          {/* Tab 3: Live Telemetry Feed */}
          {activeTab === "events" && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <EventExplorer onSelectUser={(id) => setSelectedUser(id)} />
            </div>
          )}

          {/* Tab 4: Users Directory */}
          {activeTab === "users" && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <EventExplorer onSelectUser={(id) => setSelectedUser(id)} />
            </div>
          )}

          {/* Tab 5: Broadcast Studio */}
          {activeTab === "broadcast" && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <BroadcastManager
                initialBroadcast={data.broadcast}
                onUpdateSuccess={fetchData}
              />
            </div>
          )}

          {/* Tab 6: System & Database Health */}
          {activeTab === "health" && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <SystemHealth kpis={data.kpis} serverTimeGmt1={data.serverTimeGmt1} />
            </div>
          )}
        </main>
      </div>

      {/* Global Cmd+K Search Modal */}
      <SearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        topAnime={data.topAnime}
        onNavigateTab={(tab) => setActiveTab(tab)}
        onSelectUser={(fp) => setSelectedUser(fp)}
      />

      {/* User Watch History Deep-Dive Modal */}
      <UserModal
        fingerprint={selectedUser}
        onClose={() => setSelectedUser(null)}
      />
    </div>
  );
}
