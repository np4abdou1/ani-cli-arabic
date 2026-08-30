"use client";

import React, { useState, useEffect } from "react";
import { Search, X, Flame, Radio, Activity, LayoutDashboard, User, ArrowRight } from "lucide-react";
import { TopAnime } from "@/lib/types";

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  topAnime: TopAnime[];
  onNavigateTab: (tab: string) => void;
  onSelectUser: (fingerprint: string) => void;
}

export default function SearchModal({
  isOpen,
  onClose,
  topAnime,
  onNavigateTab,
  onSelectUser,
}: SearchModalProps) {
  const [query, setQuery] = useState("");

  // Keyboard shortcut listener (Cmd+K / Ctrl+K / Escape)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        if (isOpen) onClose();
        else setQuery("");
      }
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filteredAnime = topAnime.filter((a) =>
    a.title.toLowerCase().includes(query.toLowerCase())
  );

  const isFingerprintQuery = query.length >= 8 && /^[a-f0-9]+$/i.test(query.trim());

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-background/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="glass-panel w-full max-w-xl rounded-3xl border border-border shadow-2xl overflow-hidden flex flex-col">
        {/* Search Bar Input */}
        <div className="p-4 border-b border-border/80 flex items-center gap-3">
          <Search className="w-4 h-4 text-primary shrink-0" />
          <input
            type="text"
            autoFocus
            placeholder="Search anime title, user fingerprint ID, or dashboard tab..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-transparent text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl bg-surface hover:bg-card border border-border text-slate-400 hover:text-white transition-colors text-xs"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results Body */}
        <div className="p-3 max-h-80 overflow-y-auto space-y-2 text-xs">
          {/* Direct User Fingerprint Search option */}
          {isFingerprintQuery && (
            <button
              onClick={() => {
                onSelectUser(query.trim());
                onClose();
              }}
              className="w-full flex items-center justify-between p-3 rounded-2xl bg-primary/10 hover:bg-primary/20 border border-primary/30 text-left transition-all group"
            >
              <div className="flex items-center gap-2.5">
                <User className="w-4 h-4 text-primary" />
                <div>
                  <span className="font-bold text-white block">Inspect User Profile</span>
                  <span className="text-[11px] font-mono text-slate-400 truncate max-w-xs block">
                    Fingerprint: {query.trim()}
                  </span>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-primary group-hover:translate-x-1 transition-transform" />
            </button>
          )}

          {/* Tab Shortcuts */}
          <div className="px-2 pt-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Quick Navigation
          </div>
          <div className="grid grid-cols-2 gap-2">
            {[
              { id: "overview", label: "Executive Overview", icon: LayoutDashboard },
              { id: "anime", label: "Anime Leaderboard", icon: Flame },
              { id: "events", label: "Live Telemetry Feed", icon: Activity },
              { id: "broadcast", label: "Broadcast & Popups", icon: Radio },
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    onNavigateTab(tab.id);
                    onClose();
                  }}
                  className="flex items-center gap-2.5 p-2.5 rounded-xl bg-surface hover:bg-card border border-white/5 text-slate-300 hover:text-white transition-all text-xs"
                >
                  <Icon className="w-3.5 h-3.5 text-primary" />
                  <span className="truncate">{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Anime Matches */}
          {filteredAnime.length > 0 && (
            <>
              <div className="px-2 pt-3 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Top Anime Matches ({filteredAnime.length})
              </div>
              <div className="space-y-1">
                {filteredAnime.slice(0, 8).map((anime, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      onNavigateTab("anime");
                      onClose();
                    }}
                    className="w-full flex items-center justify-between p-2.5 rounded-xl bg-surface/50 hover:bg-card border border-transparent hover:border-border text-left transition-all"
                  >
                    <span className="font-semibold text-white truncate max-w-sm">
                      {anime.title}
                    </span>
                    <span className="text-[11px] font-mono text-accent-cyan font-bold shrink-0">
                      {anime.plays.toLocaleString()} streams
                    </span>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
