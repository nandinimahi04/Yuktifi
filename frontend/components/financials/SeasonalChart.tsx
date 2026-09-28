"use client";
import React from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from "recharts";

const fmt = (n: number) =>
  n >= 100000 ? `₹${(n / 100000).toFixed(1)}L` : `₹${Math.round(n).toLocaleString("en-IN")}`;

const fmtFull = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

export interface SeasonalEntry {
  month: string;
  revenue: number;
  index: number;
}

export default function SeasonalChart({
  data,
  maxRev,
  minRev
}: {
  data: SeasonalEntry[];
  maxRev: number;
  minRev: number;
}) {
  if (!data || data.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl border border-premium-border p-6 mb-6">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="month" tick={{ fontSize: 12, fill: "#6b7280" }} />
          <YAxis tickFormatter={(v) => fmt(v)} tick={{ fontSize: 11, fill: "#6b7280" }} />
          <Tooltip formatter={(v: any) => [fmtFull(v), "Revenue"]} />
          <Bar dataKey="revenue" radius={[6, 6, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={
                  entry.revenue === maxRev
                    ? "#16a34a"
                    : entry.revenue === minRev
                    ? "#ef4444"
                    : entry.index >= 1.0
                    ? "#6366f1"
                    : "#9ca3af"
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
