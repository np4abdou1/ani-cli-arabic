interface Env {
  BROADCAST_KV?: KVNamespace;
}

export const onRequest: PagesFunction<Env> = async (context) => {
  const { env, request } = context;

  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json"
  };

  if (request.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (!env.BROADCAST_KV) {
    return new Response(JSON.stringify({ error: "BROADCAST_KV binding missing" }), { status: 500, headers: corsHeaders });
  }

  if (request.method === "GET") {
    try {
      const data = await env.BROADCAST_KV.get("active_broadcast", { type: "json" });
      return new Response(JSON.stringify(data || {
        id: "",
        active: false,
        type: "banner",
        title: "",
        message: "",
        link: "",
        style: "cyan"
      }), { status: 200, headers: corsHeaders });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e.message }), { status: 500, headers: corsHeaders });
    }
  }

  if (request.method === "POST") {
    try {
      const body = await request.json();
      await env.BROADCAST_KV.put("active_broadcast", JSON.stringify(body));
      return new Response(JSON.stringify({ success: true, broadcast: body }), { status: 200, headers: corsHeaders });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e.message }), { status: 500, headers: corsHeaders });
    }
  }

  return new Response("Method Not Allowed", { status: 405, headers: corsHeaders });
};
