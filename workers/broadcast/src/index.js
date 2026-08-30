/**
 * Cloudflare Worker for ani-cli-arabic Remote Broadcast & Announcements
 */

const DEFAULT_BROADCAST = {
  id: "",
  active: false,
  type: "banner",
  title: "",
  message: "",
  link: "",
  min_version: "",
  max_version: "",
  dismissable: true,
  style: "cyan"
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, User-Agent",
      "Cache-Control": "public, max-age=300, s-maxage=300"
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    if (url.pathname === "/broadcast.json" || url.pathname === "/" || url.pathname === "/api/broadcast") {
      let broadcastData = DEFAULT_BROADCAST;

      // If KV storage is bound as env.BROADCAST_KV
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
