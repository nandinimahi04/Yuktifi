"use client";
import React from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, ReferenceLine, Cell
} from "recharts";

const fmt = (n: number) =>
  n >= 100000 ? `₹${(n / 100000).toFixed(1)}L` : `₹${Math.round(n).toLocaleString("en-IN")}`;

const fmtFull = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

export interface CashflowEntry {
  month: string;
  month_num: number;
  revenue: number;
  expenses: number;
  net_cash: number;
  cumulative: number;
}

export default function CashFlowChart({ data }: { data: CashflowEntry[] }) {
  if (!data || data.length === 0) return null;

  return (
    <>
      <div className="bg-white rounded-2xl border border-premium-border p-6 mb-6">
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#16a34a" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#16a34a" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ea580c" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#ea580c" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 12, fill: "#6b7280" }} />
            <YAxis tickFormatter={(v) => fmt(v)} tick={{ fontSize: 11, fill: "#6b7280" }} />
            <Tooltip
              formatter={(val: any, name: any) => [fmtFull(val), name]}
              labelFormatter={(label: any) => `Month: ${label}`}
            />
            <Area type="monotone" dataKey="revenue" name="Revenue" stroke="#16a34a" strokeWidth={2} fill="url(#revGrad)" />
            <Area type="monotone" dataKey="expenses" name="Expenses" stroke="#ea580c" strokeWidth={2} fill="url(#expGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-2xl border border-premium-border p-6">
        <h3 className="font-bold text-forest-deep mb-4">Cumulative Net Cash Flow</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 12, fill: "#6b7280" }} />
            <YAxis tickFormatter={(v) => fmt(v)} tick={{ fontSize: 11, fill: "#6b7280" }} />
            <Tooltip formatter={(val: any) => [fmtFull(val), "Net Cash"]} />
            <ReferenceLine y={0} stroke="#374151" strokeDasharray="4 2" />
            <Bar dataKey="net_cash" radius={[4, 4, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={index} fill={entry.net_cash >= 0 ? "#16a34a" : "#ef4444"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
