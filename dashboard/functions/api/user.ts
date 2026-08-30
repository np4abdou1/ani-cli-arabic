interface Env {
  DB: D1Database;
}

export const onRequestGet: PagesFunction<Env> = async (context) => {
  const { env, request } = context;
  const url = new URL(request.url);
  const fingerprint = url.searchParams.get("fingerprint") || "";

  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json"
  };

  if (!fingerprint) {
    return new Response(JSON.stringify({ error: "Fingerprint required" }), { status: 400, headers: corsHeaders });
  }

  try {
    const userSummary = await env.DB.prepare(`
      SELECT 
        fingerprint,
        min(timestamp) as first_seen,
        max(timestamp) as last_seen,
        count(*) as total_events,
        sum(case when action = 'video_play' then 1 else 0 end) as total_streams,
        sum(case when action = 'app_start' then 1 else 0 end) as total_starts
      FROM monitoring_events
      WHERE fingerprint = ?
    `).bind(fingerprint).first();

    const watchHistory = await env.DB.prepare(`
      SELECT 
        json_extract(details, '$.anime') as anime,
        json_extract(details, '$.episode') as episode,
        timestamp
      FROM monitoring_events
      WHERE fingerprint = ? AND action = 'video_play'
      ORDER BY id DESC
      LIMIT 30
    `).bind(fingerprint).all();

    return new Response(JSON.stringify({
      summary: userSummary,
      history: watchHistory.results || []
    }), {
      status: 200,
      headers: corsHeaders
    });
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message }), { status: 500, headers: corsHeaders });
  }
};
