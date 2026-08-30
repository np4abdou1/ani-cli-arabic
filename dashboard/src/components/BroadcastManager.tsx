"use client";

import React, { useState } from "react";
import { Radio, Send, CheckCircle2, AlertTriangle, Eye, Sparkles } from "lucide-react";
import { BroadcastData } from "@/lib/types";

interface BroadcastManagerProps {
  initialBroadcast: BroadcastData;
  onUpdateSuccess: () => void;
}

export default function BroadcastManager({
  initialBroadcast,
  onUpdateSuccess
}: BroadcastManagerProps) {
  const [broadcast, setBroadcast] = useState<BroadcastData>(initialBroadcast);
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
        setStatusMsg({ type: "success", text: "Broadcast updated successfully in Cloudflare KV!" });
        onUpdateSuccess();
      } else {
        const err = (await res.json()) as any;
        setStatusMsg({ type: "error", text: err.error || "Failed to update broadcast" });
      }
    } catch (e: any) {
      setStatusMsg({ type: "error", text: e.message || "Network Error" });
    } finally {
      setSaving(false);
    }
  };

  const getStyleColor = (style: string) => {
    switch (style) {
      case "green": return "text-accent-green";
      case "yellow": return "text-accent-yellow";
      case "magenta": return "text-accent-magenta";
      case "red": return "text-accent-pink";
      default: return "text-accent-cyan";
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-border">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Radio className="w-4 h-4 text-primary animate-pulse" />
            Cloudflare Remote Broadcast & Banner Manager
          </h2>
          <p className="text-xs text-slate-400">
            Publish instant announcements, maintenance notices, and alerts to all active CLI users
          </p>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-4">
        {/* Active Toggle */}
        <div className="flex items-center justify-between p-4 rounded-xl bg-surface border border-white/5">
          <div>
            <span className="text-xs font-bold text-white block">Broadcast Status</span>
            <span className="text-[11px] text-slate-400">
              When active, the message will render globally across all CLI clients on launch
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

        {/* Message Input */}
        <div>
          <label className="block text-xs font-bold text-slate-300 mb-1">
            Announcement Message
          </label>
          <input
            type="text"
            value={broadcast.message}
            onChange={(e) => setBroadcast((b) => ({ ...b, message: e.target.value }))}
            placeholder="e.g. Server maintenance scheduled tonight at 02:00 GMT+1..."
            className="w-full bg-surface border border-border rounded-xl px-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary"
          />
        </div>

        {/* Style Color Selector */}
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
              <option value="cyan">Cyan (Information / Update)</option>
              <option value="green">Green (Success / Resolved)</option>
              <option value="yellow">Yellow (Warning / Notice)</option>
              <option value="magenta">Magenta (Feature Announcement)</option>
              <option value="red">Red (Critical Alert)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-300 mb-1">
              Optional Link URL
            </label>
            <input
              type="text"
              value={broadcast.link}
              onChange={(e) => setBroadcast((b) => ({ ...b, link: e.target.value }))}
              placeholder="https://github.com/np4abdou1/ani-cli-arabic"
              className="w-full bg-surface border border-border rounded-xl px-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        {/* Live Terminal Preview */}
        <div className="mt-4 p-4 rounded-xl bg-background border border-border/80">
          <div className="flex items-center gap-2 mb-2 text-[11px] text-slate-400 font-semibold uppercase tracking-wider">
            <Eye className="w-3.5 h-3.5 text-primary" /> Live CLI Terminal Preview
          </div>
          {broadcast.active && broadcast.message.trim() ? (
            <div className="text-center py-2">
              <span className={`font-bold text-xs ${getStyleColor(broadcast.style)}`}>
                ⚡ {broadcast.message}
              </span>
            </div>
          ) : (
            <div className="text-center py-2 text-xs text-slate-600 italic">
              Broadcast is currently inactive (No message displayed on terminal)
            </div>
          )}
        </div>

        {/* Status Alert */}
        {statusMsg && (
          <div
            className={`p-3 rounded-xl text-xs flex items-center gap-2 ${
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
          className="w-full py-2.5 bg-primary hover:bg-primary-hover text-slate-900 font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow-lg shadow-primary/20 transition-all disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
          <span>{saving ? "Deploying to Cloudflare KV..." : "Publish Live Broadcast to Cloudflare Edge"}</span>
        </button>
      </form>
    </div>
  );
}
