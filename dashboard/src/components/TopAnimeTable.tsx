"use client";

import React, { useState } from "react";
import { Flame, Film, Users, Search } from "lucide-react";
import { TopAnime } from "@/lib/types";

interface TopAnimeTableProps {
  animeList: TopAnime[];
}

export default function TopAnimeTable({ animeList }: TopAnimeTableProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const filtered = animeList.filter((a) =>
    a.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="glass-panel rounded-2xl p-6 border border-border">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Flame className="w-4 h-4 text-accent-pink" />
            Top Streamed Anime Leaderboard
          </h2>
          <p className="text-xs text-slate-400">
            Most watched titles ranked by stream volume & audience reach
          </p>
        </div>

        {/* Search Filter */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Filter anime..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-surface border border-border rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-primary"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-border/80 text-slate-400 font-semibold uppercase tracking-wider">
              <th className="pb-3 pl-2 w-12">#</th>
              <th className="pb-3">Anime Title</th>
              <th className="pb-3 text-right">Streams</th>
              <th className="pb-3 text-right">Unique Watchers</th>
              <th className="pb-3 text-right pr-2">Share</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {filtered.slice(0, 15).map((anime, idx) => {
              const rankColor =
                idx === 0
                  ? "bg-amber-400/20 text-amber-300 border-amber-400/40"
                  : idx === 1
                  ? "bg-slate-300/20 text-slate-200 border-slate-300/40"
                  : idx === 2
                  ? "bg-amber-700/20 text-amber-500 border-amber-700/40"
                  : "bg-white/5 text-slate-400 border-transparent";

              return (
                <tr
                  key={idx}
                  className="hover:bg-white/[0.02] transition-colors group"
                >
                  <td className="py-3 pl-2">
                    <span
                      className={`inline-flex items-center justify-center w-6 h-6 rounded-lg text-xs font-bold border ${rankColor}`}
                    >
                      {idx + 1}
                    </span>
                  </td>
                  <td className="py-3 font-medium text-white flex items-center gap-2">
                    <Film className="w-3.5 h-3.5 text-primary shrink-0 opacity-70 group-hover:opacity-100" />
                    <span className="truncate max-w-xs md:max-w-md">{anime.title}</span>
                  </td>
                  <td className="py-3 text-right font-bold text-accent-cyan">
                    {anime.plays.toLocaleString()}
                  </td>
                  <td className="py-3 text-right text-slate-300">
                    <span className="inline-flex items-center gap-1 font-mono">
                      <Users className="w-3 h-3 text-slate-500" />
                      {anime.uniqueWatchers.toLocaleString()}
                    </span>
                  </td>
                  <td className="py-3 text-right pr-2">
                    <div className="flex items-center justify-end gap-2">
                      <span className="font-mono text-slate-400">{anime.share}%</span>
                      <div className="w-12 h-1.5 bg-surface rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-primary to-accent-cyan rounded-full"
                          style={{ width: `${Math.min(100, anime.share * 6)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
