interface Env {
  DB: D1Database;
}

export const onRequestGet: PagesFunction<Env> = async (context) => {
  const { env, request } = context;
  const url = new URL(request.url);

  const page = parseInt(url.searchParams.get("page") || "1", 10);
  const limit = Math.min(100, Math.max(10, parseInt(url.searchParams.get("limit") || "25", 10)));
  const offset = (page - 1) * limit;

  const action = url.searchParams.get("action") || "";
  const query = url.searchParams.get("search") || "";
  const os = url.searchParams.get("os") || "";

  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json"
  };

  if (!env.DB) {
    return new Response(JSON.stringify({ error: "DB binding missing" }), { status: 500, headers: corsHeaders });
  }

  try {
    let sql = `
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
      WHERE 1=1
    `;
    const params: any[] = [];

    if (action) {
      sql += ` AND action = ?`;
      params.push(action);
    }
    if (os) {
      sql += ` AND json_extract(details, '$.os') = ?`;
      params.push(os);
    }
    if (query) {
      sql += ` AND (json_extract(details, '$.anime') LIKE ? OR fingerprint LIKE ?)`;
      params.push(`%${query}%`, `%${query}%`);
    }

    // Get count
    const countSql = `SELECT count(*) as total FROM (${sql})`;
    const countStmt = env.DB.prepare(countSql);
    const countResult = await (params.length ? countStmt.bind(...params) : countStmt).first<{ total: number }>();
    const total = countResult?.total || 0;

    sql += ` ORDER BY id DESC LIMIT ? OFFSET ?`;
    params.push(limit, offset);

    const stmt = env.DB.prepare(sql);
    const result = await (params.length ? stmt.bind(...params) : stmt).all();

    return new Response(JSON.stringify({
      events: result.results || [],
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit)
      }
    }), {
      status: 200,
      headers: corsHeaders
    });
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message }), { status: 500, headers: corsHeaders });
  }
};
