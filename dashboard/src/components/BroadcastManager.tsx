"use client";

import React, { useState, useEffect } from "react";
import {
  Radio,
  Send,
  CheckCircle2,
  AlertTriangle,
  Eye,
  Sparkles,
  MessageSquare,
  Layout,
  ExternalLink,
  Bold,
  Italic,
  List,
  Link as LinkIcon,
  Smile,
  RefreshCw,
  Terminal
} from "lucide-react";
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
    id: initialBroadcast?.id || "broadcast-" + Date.now(),
    active: initialBroadcast?.active ?? true,
    type: initialBroadcast?.type || "popup",
    title: initialBroadcast?.title ?? "🚀 Welcome to ani-cli-arabic v2.0",
    message: initialBroadcast?.message ?? "Welcome to **ani-cli-arabic v2.0**!\n\n◆ 4 Streaming engines: Anime3rb, Anime Slayer, Animeify, AniDB\n◆ Real-Time MPV playback resumption\n◆ Instant auto-updater and zero-latency search",
    link: initialBroadcast?.link ?? "https://github.com/np4abdou1/ani-cli-arabic",
    style: initialBroadcast?.style || "cyan"
  });

  // Sync state if initialBroadcast changes from server
  useEffect(() => {
    if (initialBroadcast) {
      setBroadcast({
        id: initialBroadcast.id || "broadcast-" + Date.now(),
        active: initialBroadcast.active ?? false,
        type: initialBroadcast.type || "popup",
        title: initialBroadcast.title !== undefined ? initialBroadcast.title : "🚨 Community Announcement",
        message: initialBroadcast.message !== undefined ? initialBroadcast.message : "",
        link: initialBroadcast.link || "",
        style: initialBroadcast.style || "cyan"
      });
    }
  }, [initialBroadcast]);

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
        setStatusMsg({
          type: "success",
          text: `Broadcast published successfully! Active: ${broadcast.active ? "YES" : "NO"} (${broadcast.type.toUpperCase()})`
        });
        onUpdateSuccess();
      } else {
        const err = (await res.json()) as any;
        setStatusMsg({ type: "error", text: err?.error || "Failed to deploy broadcast to Cloudflare Edge" });
      }
    } catch (e: any) {
      setStatusMsg({ type: "error", text: e.message || "Network Communication Error" });
    } finally {
      setSaving(false);
    }
  };

  const insertMarkdown = (prefix: string, suffix: string = "") => {
    setBroadcast((prev) => ({
      ...prev,
      message: `${prev.message}\n${prefix}Text${suffix}`
    }));
  };

  const insertEmoji = (emoji: string, target: "title" | "message") => {
    if (target === "title") {
      setBroadcast((prev) => ({ ...prev, title: `${prev.title} ${emoji}`.trim() }));
    } else {
      setBroadcast((prev) => ({ ...prev, message: `${prev.message} ${emoji}` }));
    }
  };

  const themeStyles: Record<string, { text: string; border: string; bg: string; name: string }> = {
    cyan: { text: "text-accent-cyan", border: "border-accent-cyan", bg: "bg-accent-cyan/10", name: "Cyber Cyan" },
    green: { text: "text-accent-green", border: "border-accent-green", bg: "bg-accent-green/10", name: "Emerald Green" },
    yellow: { text: "text-accent-yellow", border: "border-accent-yellow", bg: "bg-accent-yellow/10", name: "Amber Gold" },
    magenta: { text: "text-accent-magenta", border: "border-accent-magenta", bg: "bg-accent-magenta/10", name: "Violet Purple" },
    red: { text: "text-accent-pink", border: "border-accent-pink", bg: "bg-accent-pink/10", name: "Crimson Red" }
  };

  const activeTheme = themeStyles[broadcast.style] || themeStyles.cyan;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 animate-in fade-in duration-300">
      {/* Left Column: Form Editor (7 cols) */}
      <div className="xl:col-span-7 glass-panel rounded-3xl p-6 border border-border shadow-xl space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-border/80">
          <div>
            <h3 className="text-base font-extrabold text-white flex items-center gap-2">
              <Radio className="w-4 h-4 text-primary animate-pulse" />
              Remote Broadcast & Modal Studio
            </h3>
            <p className="text-xs text-slate-400">
              Configure and publish real-time global messages to all active CLI users
            </p>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full font-bold bg-primary/10 text-primary border border-primary/20">
            Cloudflare KV Edge
          </span>
        </div>

        <form onSubmit={handleSave} className="space-y-5">
          {/* Top Row: Active Toggle & Display Format */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Active Toggle Card */}
            <div className="p-4 rounded-2xl bg-surface/80 border border-white/5 flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-white block">Broadcast State</span>
                <span className="text-[11px] text-slate-400">
                  {broadcast.active ? "Visible to all users" : "Disabled on edge"}
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

            {/* Display Format Toggle */}
            <div className="p-4 rounded-2xl bg-surface/80 border border-white/5 flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-white block">Display Mode</span>
                <span className="text-[11px] text-slate-400">
                  {broadcast.type === "popup" ? "Startup Modal Box" : "Single-Line Banner"}
                </span>
              </div>
              <div className="flex items-center bg-background p-1 rounded-xl border border-border">
                <button
                  type="button"
                  onClick={() => setBroadcast((b) => ({ ...b, type: "popup" }))}
                  className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-bold rounded-lg transition-all ${
                    broadcast.type === "popup"
                      ? "bg-primary text-slate-900 shadow-md"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Modal</span>
                </button>
                <button
                  type="button"
                  onClick={() => setBroadcast((b) => ({ ...b, type: "banner" }))}
                  className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-bold rounded-lg transition-all ${
                    broadcast.type === "banner"
                      ? "bg-primary text-slate-900 shadow-md"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Layout className="w-3.5 h-3.5" />
                  <span>Banner</span>
                </button>
              </div>
            </div>
          </div>

          {/* Editable Title Input */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold text-slate-200">
                Announcement Title
              </label>
              <div className="flex items-center gap-1">
                {["🚀", "🎉", "📢", "🚨", "⚡", "✨", "🔥"].map((emoji) => (
                  <button
                    key={emoji}
                    type="button"
                    onClick={() => insertEmoji(emoji, "title")}
                    className="p-1 text-xs hover:bg-white/10 rounded transition-colors"
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            </div>
            <input
              type="text"
              value={broadcast.title}
              onChange={(e) => setBroadcast((b) => ({ ...b, title: e.target.value }))}
              placeholder="e.g. 🚀 Important Server Maintenance Notice"
              className="w-full bg-surface border border-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary shadow-inner"
            />
          </div>

          {/* Message Body Input + Markdown Toolbar */}
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
              <label className="text-xs font-bold text-slate-200">
                Message Content (Markdown & Emojis Supported)
              </label>
              {/* Markdown Helpers */}
              <div className="flex items-center gap-1 bg-surface p-1 rounded-lg border border-border text-xs">
                <button
                  type="button"
                  onClick={() => insertMarkdown("**", "**")}
                  className="px-2 py-0.5 rounded hover:bg-white/10 text-slate-300 hover:text-white font-bold"
                  title="Bold"
                >
                  <Bold className="w-3 h-3 inline mr-1" /> B
                </button>
                <button
                  type="button"
                  onClick={() => insertMarkdown("*", "*")}
                  className="px-2 py-0.5 rounded hover:bg-white/10 text-slate-300 hover:text-white italic"
                  title="Italic"
                >
                  <Italic className="w-3 h-3 inline mr-1" /> I
                </button>
                <button
                  type="button"
                  onClick={() => insertMarkdown("◆ ")}
                  className="px-2 py-0.5 rounded hover:bg-white/10 text-slate-300 hover:text-white"
                  title="Bullet point"
                >
                  <List className="w-3 h-3 inline mr-1" /> Bullet
                </button>
                <button
                  type="button"
                  onClick={() => insertMarkdown("[Link Title](", ")")}
                  className="px-2 py-0.5 rounded hover:bg-white/10 text-slate-300 hover:text-white"
                  title="Link"
                >
                  <LinkIcon className="w-3 h-3 inline mr-1" /> Link
                </button>
              </div>
            </div>
            <textarea
              rows={6}
              value={broadcast.message}
              onChange={(e) => setBroadcast((b) => ({ ...b, message: e.target.value }))}
              placeholder="Write your markdown announcement message here..."
              className="w-full bg-surface border border-border rounded-xl px-4 py-3 text-xs text-white font-mono placeholder-slate-500 focus:outline-none focus:border-primary leading-relaxed shadow-inner"
            />
          </div>

          {/* Theme Selector & Link Input */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Style Selector */}
            <div>
              <label className="block text-xs font-bold text-slate-200 mb-1.5">
                Accent Theme Color
              </label>
              <div className="grid grid-cols-5 gap-2">
                {Object.entries(themeStyles).map(([key, info]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setBroadcast((b) => ({ ...b, style: key }))}
                    className={`p-2 rounded-xl border flex flex-col items-center gap-1 transition-all ${
                      broadcast.style === key
                        ? `${info.border} bg-white/10 shadow-md`
                        : "border-border bg-surface hover:border-slate-500"
                    }`}
                  >
                    <div className={`w-3.5 h-3.5 rounded-full ${info.bg} ${info.border} border-2`} />
                    <span className="text-[10px] text-slate-400 capitalize">{key}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Link Input */}
            <div>
              <label className="block text-xs font-bold text-slate-200 mb-1.5">
                Call-to-Action Link URL (Optional)
              </label>
              <div className="relative">
                <ExternalLink className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={broadcast.link}
                  onChange={(e) => setBroadcast((b) => ({ ...b, link: e.target.value }))}
                  placeholder="https://discord.gg/ani-cli-arabic"
                  className="w-full bg-surface border border-border rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary shadow-inner"
                />
              </div>
            </div>
          </div>

          {/* Status Message Alert */}
          {statusMsg && (
            <div
              className={`p-4 rounded-2xl text-xs flex items-center gap-3 animate-in fade-in duration-200 ${
                statusMsg.type === "success"
                  ? "bg-accent-green/10 text-accent-green border border-accent-green/25"
                  : "bg-accent-pink/10 text-accent-pink border border-accent-pink/25"
              }`}
            >
              {statusMsg.type === "success" ? (
                <CheckCircle2 className="w-5 h-5 shrink-0" />
              ) : (
                <AlertTriangle className="w-5 h-5 shrink-0" />
              )}
              <span className="font-semibold">{statusMsg.text}</span>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={saving}
            className="w-full py-3.5 bg-primary hover:bg-primary-hover text-slate-900 font-extrabold rounded-2xl text-xs flex items-center justify-center gap-2.5 shadow-xl shadow-primary/25 transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
            <span>{saving ? "Deploying to Cloudflare KV Edge..." : "Publish Live Broadcast to Cloudflare Edge"}</span>
          </button>
        </form>
      </div>

      {/* Right Column: Live Terminal Simulation (5 cols) */}
      <div className="xl:col-span-5 space-y-4">
        <div className="glass-panel rounded-3xl p-6 border border-border shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border/80">
            <span className="text-xs font-bold text-white flex items-center gap-2">
              <Eye className="w-4 h-4 text-accent-cyan" />
              Live Terminal Preview
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-slate-300">
              {broadcast.active ? "STATUS: ACTIVE" : "STATUS: DISABLED"}
            </span>
          </div>

          {/* Mac/Linux Terminal Window Frame */}
          <div className="rounded-2xl border border-border bg-[#0b0d14] overflow-hidden shadow-2xl">
            {/* Terminal Window Titlebar */}
            <div className="px-4 py-2.5 bg-[#121622] border-b border-border/60 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block" />
                <span className="w-3 h-3 rounded-full bg-yellow-500/80 inline-block" />
                <span className="w-3 h-3 rounded-full bg-green-500/80 inline-block" />
              </div>
              <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
                <Terminal className="w-3 h-3 text-primary" /> bash - ani-cli-arabic
              </span>
              <span className="w-10" />
            </div>

            {/* Terminal Body */}
            <div className="p-6 font-mono text-xs min-h-[280px] flex flex-col justify-center">
              {broadcast.active && broadcast.message.trim() ? (
                broadcast.type === "popup" ? (
                  /* Interactive Modal Box */
                  <div className="rounded-xl border border-border bg-card/90 p-4 space-y-3 shadow-xl relative overflow-hidden">
                    {/* Modal Title */}
                    <div className={`text-center font-bold pb-2 border-b border-border/80 ${activeTheme.text}`}>
                      {broadcast.title || "🚨 Remote Announcement"}
                    </div>

                    {/* Modal Body with Fake Scrollbar */}
                    <div className="flex gap-2">
                      <div className="flex-1 whitespace-pre-wrap text-slate-200 leading-relaxed text-[11px] max-h-40 overflow-y-auto pr-1">
                        {broadcast.message}
                      </div>
                      <div className="w-2 bg-surface rounded flex flex-col justify-start">
                        <div className="h-6 w-full bg-primary/60 rounded" />
                      </div>
                    </div>

                    {/* Modal Bottom Dock Keycaps */}
                    <div className="pt-3 border-t border-border/80 flex flex-wrap items-center justify-center gap-2 text-[10px]">
                      <span className="bg-surface px-2 py-0.5 rounded border border-border text-white font-bold">
                        [ ↵ / Esc Close ]
                      </span>
                      {broadcast.link && (
                        <span className={`bg-surface px-2 py-0.5 rounded border border-border font-bold ${activeTheme.text}`}>
                          [ o Open Link ]
                        </span>
                      )}
                      <span className="bg-surface px-2 py-0.5 rounded border border-border text-slate-400">
                        [ ↑↓ Scroll ]
                      </span>
                    </div>
                  </div>
                ) : (
                  /* Single Line Banner */
                  <div className="text-center py-6 space-y-2">
                    <div className={`font-bold text-xs ${activeTheme.text}`}>
                      ⚡ {broadcast.message}
                    </div>
                    {broadcast.link && (
                      <div className="text-[10px] text-slate-400 underline truncate max-w-xs mx-auto">
                        {broadcast.link}
                      </div>
                    )}
                  </div>
                )
              ) : (
                <div className="text-center py-12 text-slate-600 italic text-xs">
                  Broadcast is currently inactive. Launching CLI straight to main menu...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
