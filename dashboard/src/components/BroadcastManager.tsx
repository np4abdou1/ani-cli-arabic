"use client";

import React, { useState } from "react";
import { Radio, Send, CheckCircle2, AlertTriangle, Eye, Sparkles, MessageSquare, Layout, ExternalLink } from "lucide-react";
import { BroadcastData } from "@/lib/types";

interface BroadcastManagerProps {
  initialBroadcast: BroadcastData;
  onUpdateSuccess: () => void;
}

export default function BroadcastManager({
  initialBroadcast,
  onUpdateSuccess
}: BroadcastManagerProps) {
  const [broadcast, setBroadcast] = useState<BroadcastData>({
    id: initialBroadcast.id || "announcement-v2",
    active: initialBroadcast.active ?? true,
    type: initialBroadcast.type || "popup",
    title: initialBroadcast.title || "🚀 Welcome to ani-cli-arabic v2.0",
    message: initialBroadcast.message || "Welcome to the brand new **v2.0 Multi-Provider Update**!\n\n◆ 4 Streaming engines: Anime3rb, Anime Slayer, Animeify, and AniDB\n◆ Real-Time MPV playback resumption\n◆ Instant auto-updater and zero-latency search\n\nJoin our Discord or star the repo on GitHub!",
    link: initialBroadcast.link || "https://github.com/np4abdou1/ani-cli-arabic",
    style: initialBroadcast.style || "cyan"
  });

  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setStatusMsg(null);

    try {
      const res = await fetch("/api/broadcast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(broadcast)
      });

      if (res.ok) {
        setStatusMsg({ type: "success", text: "Broadcast updated successfully across Cloudflare Edge!" });
        onUpdateSuccess();
      } else {
        const err = (await res.json()) as any;
        setStatusMsg({ type: "error", text: err?.error || "Failed to update broadcast" });
      }
    } catch (e: any) {
      setStatusMsg({ type: "error", text: e.message || "Network Error" });
    } finally {
      setSaving(false);
    }
  };

  const getStyleColor = (style: string) => {
    switch (style) {
      case "green": return { text: "text-accent-green", border: "border-accent-green", bg: "bg-accent-green/10" };
      case "yellow": return { text: "text-accent-yellow", border: "border-accent-yellow", bg: "bg-accent-yellow/10" };
      case "magenta": return { text: "text-accent-magenta", border: "border-accent-magenta", bg: "bg-accent-magenta/10" };
      case "red": return { text: "text-accent-pink", border: "border-accent-pink", bg: "bg-accent-pink/10" };
      default: return { text: "text-accent-cyan", border: "border-accent-cyan", bg: "bg-accent-cyan/10" };
    }
  };

  const styleColors = getStyleColor(broadcast.style);

  return (
    <div className="glass-panel rounded-2xl p-6 border border-border">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Radio className="w-4 h-4 text-primary animate-pulse" />
            Cloudflare Remote Broadcast & Modal Popup Hub
          </h2>
          <p className="text-xs text-slate-400">
            Publish instant announcements, startup modal popups, and maintenance banners to all active CLI users
          </p>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-5">
        {/* Active Toggle & Type Select */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Active Toggle */}
          <div className="flex items-center justify-between p-4 rounded-xl bg-surface border border-white/5">
            <div>
              <span className="text-xs font-bold text-white block">Broadcast Active Status</span>
              <span className="text-[11px] text-slate-400">
                Show live announcement to CLI users on launch
              </span>
            </div>
            <button
              type="button"
              onClick={() => setBroadcast((b) => ({ ...b, active: !b.active }))}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                broadcast.active ? "bg-accent-green" : "bg-slate-700"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  broadcast.active ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>

          {/* Type Selector (Banner vs Popup Modal) */}
          <div className="p-4 rounded-xl bg-surface border border-white/5 flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-white block">Display Format</span>
              <span className="text-[11px] text-slate-400">
                Banner vs Scrollable Startup Modal
              </span>
            </div>
            <div className="flex items-center bg-background p-1 rounded-xl border border-border">
              <button
                type="button"
                onClick={() => setBroadcast((b) => ({ ...b, type: "popup" }))}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-bold rounded-lg transition-all ${
                  broadcast.type === "popup"
                    ? "bg-primary text-slate-900 shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Modal Popup</span>
              </button>
              <button
                type="button"
                onClick={() => setBroadcast((b) => ({ ...b, type: "banner" }))}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-bold rounded-lg transition-all ${
                  broadcast.type === "banner"
                    ? "bg-primary text-slate-900 shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Layout className="w-3.5 h-3.5" />
                <span>Top Banner</span>
              </button>
            </div>
          </div>
        </div>

        {/* Title Input (If popup) */}
        {broadcast.type === "popup" && (
          <div>
            <label className="block text-xs font-bold text-slate-300 mb-1">
              Popup Modal Title
            </label>
            <input
              type="text"
              value={broadcast.title}
              onChange={(e) => setBroadcast((b) => ({ ...b, title: e.target.value }))}
              placeholder="e.g. 🚀 Welcome to ani-cli-arabic v2.0"
              className="w-full bg-surface border border-border rounded-xl px-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary"
            />
          </div>
        )}

        {/* Message Body Input */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs font-bold text-slate-300">
              Message Content (Markdown Supported)
            </label>
            <span className="text-[11px] text-slate-500 font-mono">
              Use **bold** for highlights, ◆ for bullet points
            </span>
          </div>
          <textarea
            rows={5}
            value={broadcast.message}
            onChange={(e) => setBroadcast((b) => ({ ...b, message: e.target.value }))}
            placeholder="Type your markdown message here..."
            className="w-full bg-surface border border-border rounded-xl px-4 py-2.5 text-xs text-white font-mono placeholder-slate-500 focus:outline-none focus:border-primary leading-relaxed"
          />
        </div>

        {/* Style Color & Link Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-300 mb-1">
              Accent Color / Theme
            </label>
            <select
              value={broadcast.style || "cyan"}
              onChange={(e) => setBroadcast((b) => ({ ...b, style: e.target.value }))}
              className="w-full bg-surface border border-border rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary"
            >
              <option value="cyan">Cyan (Community / General)</option>
              <option value="green">Emerald Green (New Feature / Release)</option>
              <option value="yellow">Amber Yellow (Maintenance / Notice)</option>
              <option value="magenta">Purple Magenta (Special Event)</option>
              <option value="red">Rose Red (Urgent / Breaking Alert)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-300 mb-1">
              Call-to-Action Link URL (Optional)
            </label>
            <input
              type="text"
              value={broadcast.link}
              onChange={(e) => setBroadcast((b) => ({ ...b, link: e.target.value }))}
              placeholder="https://discord.gg/ani-cli-arabic"
              className="w-full bg-surface border border-border rounded-xl px-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        {/* Live Interactive Terminal Preview */}
        <div className="mt-6 p-5 rounded-2xl bg-background border border-border/80 relative overflow-hidden">
          <div className="flex items-center justify-between mb-3 text-[11px] text-slate-400 font-semibold uppercase tracking-wider">
            <span className="flex items-center gap-2">
              <Eye className="w-3.5 h-3.5 text-primary" /> Live CLI Terminal Preview ({broadcast.type.toUpperCase()})
            </span>
            <span className="font-mono text-[10px] text-slate-500">
              {broadcast.active ? "Status: ACTIVE" : "Status: DISABLED"}
            </span>
          </div>

          {broadcast.active && broadcast.message.trim() ? (
            broadcast.type === "popup" ? (
              /* Modal Box Preview */
              <div className="p-4 rounded-xl border border-border bg-card/80 max-w-xl mx-auto space-y-3 font-mono text-xs shadow-2xl">
                <div className={`text-center font-bold pb-2 border-b border-border/60 ${styleColors.text}`}>
                  {broadcast.title || "🚨 Remote Broadcast Announcement"}
                </div>

                <div className="py-2 text-slate-200 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto pr-2">
                  {broadcast.message}
                </div>

                {/* Keycaps */}
                <div className="pt-3 border-t border-border/60 flex items-center justify-center gap-3 text-[11px] text-slate-400">
                  <span className="bg-surface px-2 py-0.5 rounded border border-border text-white font-bold">
                    [ ↵ / Esc Close ]
                  </span>
                  {broadcast.link && (
                    <span className="bg-surface px-2 py-0.5 rounded border border-border text-primary font-bold">
                      [ o Open Link ]
                    </span>
                  )}
                  <span className="bg-surface px-2 py-0.5 rounded border border-border text-slate-300">
                    [ ↑↓ Scroll ]
                  </span>
                </div>
              </div>
            ) : (
              /* Banner Preview */
              <div className="text-center py-4">
                <span className={`font-bold text-xs ${styleColors.text}`}>
                  ⚡ {broadcast.message}
                </span>
                {broadcast.link && (
                  <span className="text-[11px] text-slate-400 block mt-1 underline">
                    {broadcast.link}
                  </span>
                )}
              </div>
            )
          ) : (
            <div className="text-center py-6 text-xs text-slate-600 italic">
              Broadcast is currently inactive (No message or popup displayed on client startup)
            </div>
          )}
        </div>

        {/* Status Alert */}
        {statusMsg && (
          <div
            className={`p-3.5 rounded-xl text-xs flex items-center gap-2 ${
              statusMsg.type === "success"
                ? "bg-accent-green/10 text-accent-green border border-accent-green/20"
                : "bg-accent-pink/10 text-accent-pink border border-accent-pink/20"
            }`}
          >
            {statusMsg.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0" />
            )}
            <span>{statusMsg.text}</span>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={saving}
          className="w-full py-3 bg-primary hover:bg-primary-hover text-slate-900 font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow-lg shadow-primary/20 transition-all disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
          <span>{saving ? "Deploying to Cloudflare Edge..." : "Publish Live Broadcast to Cloudflare Edge"}</span>
        </button>
      </form>
    </div>
  );
}
