"use client";

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from "recharts";
import { TrendingUp, Calendar } from "lucide-react";
import { GrowthPoint } from "@/lib/types";

interface TrafficChartProps {
  data: GrowthPoint[];
  timeRange: string;
}

export default function TrafficChart({ data, timeRange }: TrafficChartProps) {
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="glass-panel p-3 rounded-xl border border-border shadow-xl text-xs space-y-1">
          <p className="font-bold text-white mb-1 flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-primary" />
            {label} (GMT+1)
          </p>
          <p className="text-accent-cyan flex justify-between gap-4">
            <span>Video Streams:</span>
            <span className="font-bold">{payload[0]?.value?.toLocaleString()}</span>
          </p>
          <p className="text-primary flex justify-between gap-4">
            <span>Active Users:</span>
            <span className="font-bold">{payload[1]?.value?.toLocaleString()}</span>
          </p>
          <p className="text-accent-magenta flex justify-between gap-4">
            <span>App Starts:</span>
            <span className="font-bold">{payload[2]?.value?.toLocaleString()}</span>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-border">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-6">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-primary" />
            Traffic & Activity Overview (GMT+1)
          </h2>
          <p className="text-xs text-slate-400">
            Daily stream volume and active user engagement over time
          </p>
        </div>
        <span className="text-xs px-3 py-1 bg-white/5 rounded-lg border border-white/10 text-slate-300 font-mono">
          Showing: {timeRange.toUpperCase()}
        </span>
      </div>

      <div className="h-72 w-full">
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-slate-500">
            No telemetry data recorded for this range
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="streamGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7dcfff" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#7dcfff" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="userGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7aa2f7" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#7aa2f7" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="startGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#bb9af7" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#bb9af7" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#202538" vertical={false} />
              <XAxis
                dataKey="date"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                verticalAlign="top"
                align="right"
                iconType="circle"
                wrapperStyle={{ fontSize: "11px", paddingBottom: "12px" }}
              />
              <Area
                type="monotone"
                name="Streams"
                dataKey="streams"
                stroke="#7dcfff"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#streamGrad)"
              />
              <Area
                type="monotone"
                name="Active Users"
                dataKey="users"
                stroke="#7aa2f7"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#userGrad)"
              />
              <Area
                type="monotone"
                name="App Starts"
                dataKey="starts"
                stroke="#bb9af7"
                strokeWidth={1.5}
                fillOpacity={1}
                fill="url(#startGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
