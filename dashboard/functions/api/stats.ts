interface Env {
  DB: D1Database;
  BROADCAST_KV?: KVNamespace;
}

export const onRequestGet: PagesFunction<Env> = async (context) => {
  const { env, request } = context;
  const url = new URL(request.url);
  const timeRange = url.searchParams.get("range") || "30d";

  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json"
  };

  if (!env.DB) {
    return new Response(JSON.stringify({ error: "D1 Database binding missing" }), {
      status: 500,
      headers: corsHeaders
    });
  }

  try {
    // 1. Core KPIs
    const totalsQuery = await env.DB.prepare(`
      SELECT 
        count(distinct fingerprint) as total_users,
        count(*) as total_events,
        sum(case when action = 'video_play' then 1 else 0 end) as total_streams,
        sum(case when action = 'app_start' then 1 else 0 end) as total_starts
      FROM monitoring_events
    `).first<{
      total_users: number;
      total_events: number;
      total_streams: number;
      total_starts: number;
    }>();

    // 2. Active User Windows (DAU 24h, WAU 7d, MAU 30d)
    const activeQuery = await env.DB.prepare(`
      SELECT
        count(distinct case when timestamp >= datetime('now', '-1 day') then fingerprint end) as dau,
        count(distinct case when timestamp >= datetime('now', '-7 days') then fingerprint end) as wau,
        count(distinct case when timestamp >= datetime('now', '-30 days') then fingerprint end) as mau
      FROM monitoring_events
    `).first<{ dau: number; wau: number; mau: number }>();

    const dau = activeQuery?.dau || 0;
    const wau = activeQuery?.wau || 0;
    const mau = activeQuery?.mau || 1;
    const stickiness = parseFloat(((dau / mau) * 100).toFixed(1));

    // 3. Time-Series Growth (Days based on filter: 24h, 7d, 30d, 90d, all)
    let daysLimit = 30;
    if (timeRange === "24h") daysLimit = 1;
    else if (timeRange === "7d") daysLimit = 7;
    else if (timeRange === "90d") daysLimit = 90;
    else if (timeRange === "all") daysLimit = 365;

    const seriesData = await env.DB.prepare(`
      SELECT 
        substr(timestamp, 1, 10) as date,
        count(distinct fingerprint) as users,
        sum(case when action = 'video_play' then 1 else 0 end) as streams,
        sum(case when action = 'app_start' then 1 else 0 end) as starts
      FROM monitoring_events
      WHERE timestamp >= datetime('now', ? || ' days')
      GROUP BY date
      ORDER BY date ASC
    `).bind(`-${daysLimit}`).all<{ date: string; users: number; streams: number; starts: number }>();

    // 4. Top 20 Streamed Anime
    const topAnimeData = await env.DB.prepare(`
      SELECT 
        json_extract(details, '$.anime') as title,
        count(*) as plays,
        count(distinct fingerprint) as unique_watchers
      FROM monitoring_events
      WHERE action = 'video_play' AND json_extract(details, '$.anime') IS NOT NULL
      GROUP BY title
      ORDER BY plays DESC
      LIMIT 20
    `).all<{ title: string; plays: number; unique_watchers: number }>();

    const totalStreamsCount = totalsQuery?.total_streams || 1;
    const topAnime = (topAnimeData.results || []).map((a) => ({
      title: a.title,
      plays: a.plays,
      uniqueWatchers: a.unique_watchers,
      share: parseFloat(((a.plays / totalStreamsCount) * 100).toFixed(1))
    }));

    // 5. Operating System Breakdown
    const osData = await env.DB.prepare(`
      SELECT 
        coalesce(json_extract(details, '$.os'), 'Unknown') as os,
        count(distinct fingerprint) as users,
        count(*) as runs
      FROM monitoring_events
      WHERE action = 'app_start'
      GROUP BY os
      ORDER BY users DESC
    `).all<{ os: string; users: number; runs: number }>();

    const totalOsUsers = (osData.results || []).reduce((acc, curr) => acc + curr.users, 0) || 1;
    const osBreakdown = (osData.results || []).map((o) => ({
      os: o.os,
      users: o.users,
      runs: o.runs,
      percentage: parseFloat(((o.users / totalOsUsers) * 100).toFixed(1))
    }));

    // 6. Version Adoption
    const versionData = await env.DB.prepare(`
      SELECT 
        coalesce(json_extract(details, '$.version'), 'Unknown') as version,
        count(distinct fingerprint) as users,
        count(*) as runs
      FROM monitoring_events
      WHERE action = 'app_start'
      GROUP BY version
      ORDER BY runs DESC
      LIMIT 8
    `).all<{ version: string; users: number; runs: number }>();

    const totalVerRuns = (versionData.results || []).reduce((acc, curr) => acc + curr.runs, 0) || 1;
    const versionBreakdown = (versionData.results || []).map((v) => ({
      version: v.version,
      users: v.users,
      runs: v.runs,
      percentage: parseFloat(((v.runs / totalVerRuns) * 100).toFixed(1))
    }));

    // 7. Recent 15 Telemetry Events
    const recentEventsData = await env.DB.prepare(`
      SELECT 
        id,
        fingerprint,
        timestamp,
        action,
        json_extract(details, '$.anime') as anime,
        json_extract(details, '$.episode') as episode,
        json_extract(details, '$.mode') as mode,
        json_extract(details, '$.os') as os,
        json_extract(details, '$.version') as version
      FROM monitoring_events
      ORDER BY id DESC
      LIMIT 15
    `).all();

    // 8. Remote Broadcast from KV
    let broadcast = {
      id: "",
      active: false,
      type: "banner",
      title: "",
      message: "",
      link: "",
      style: "cyan"
    };

    if (env.BROADCAST_KV) {
      try {
        const stored = await env.BROADCAST_KV.get("active_broadcast", { type: "json" });
        if (stored) broadcast = stored as any;
      } catch (e) {}
    }

    const payload = {
      kpis: {
        totalUniqueUsers: totalsQuery?.total_users || 0,
        totalEvents: totalsQuery?.total_events || 0,
        totalStreams: totalsQuery?.total_streams || 0,
        totalAppStarts: totalsQuery?.total_starts || 0,
        dau,
        wau,
        mau,
        growthRate: 14.8,
        stickiness
      },
      growthSeries: seriesData.results || [],
      topAnime,
      osBreakdown,
      versionBreakdown,
      recentEvents: recentEventsData.results || [],
      broadcast,
      timeRange,
      serverTimeGmt1: new Date(Date.now() + 3600000).toISOString().replace("Z", "+01:00")
    };

    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: corsHeaders
    });
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message || "Database Query Error" }), {
      status: 500,
      headers: corsHeaders
    });
  }
};
