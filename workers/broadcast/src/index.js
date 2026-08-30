/**
 * Cloudflare Worker for ani-cli-arabic Remote Broadcast & Announcements
 */

const DEFAULT_BROADCAST = {
  id: "",
  active: false,
  type: "popup", // "banner" or "popup"
  title: "",
  message: "",
  link: "",
  min_version: "",
  max_version: "",
  dismissable: false,
  closable: true,
  style: "cyan"
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, HEAD, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, User-Agent",
      "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0"
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    // Handle GET
    if (request.method === "GET" && (url.pathname === "/broadcast.json" || url.pathname === "/" || url.pathname === "/api/broadcast")) {
      let broadcastData = DEFAULT_BROADCAST;

      if (env.BROADCAST_KV) {
        try {
          const stored = await env.BROADCAST_KV.get("active_broadcast", { type: "json" });
          if (stored) {
            broadcastData = stored;
          }
        } catch (e) {
          // fallback to default
        }
      }

      return new Response(JSON.stringify(broadcastData, null, 2), {
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          ...corsHeaders
        }
      });
    }

    // Handle POST
    if (request.method === "POST" && (url.pathname === "/api/broadcast" || url.pathname === "/broadcast.json" || url.pathname === "/")) {
      if (!env.BROADCAST_KV) {
        return new Response(JSON.stringify({ error: "BROADCAST_KV binding missing" }), { status: 500, headers: corsHeaders });
      }

      try {
        const body = await request.json();
        body.updated_at = new Date().toISOString();
        await env.BROADCAST_KV.put("active_broadcast", JSON.stringify(body));
        return new Response(JSON.stringify({ success: true, broadcast: body }), {
          headers: { "Content-Type": "application/json", ...corsHeaders }
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), { status: 400, headers: corsHeaders });
      }
    }

    if (url.pathname === "/health") {
      return new Response(JSON.stringify({ status: "ok", version: "2.0.0" }), {
        headers: {
          "Content-Type": "application/json",
          ...corsHeaders
        }
      });
    }

    return new Response("Not Found", { status: 404, headers: corsHeaders });
  }
};
