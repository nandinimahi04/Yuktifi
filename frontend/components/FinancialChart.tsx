"use client";

import React from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { formatCurrency } from "@/lib/formatters";

interface FinancialChartProps {
  data: {
    year: number;
    revenue: number;
    expenses: number;
    cashflow: number;
  }[];
}

export function FinancialChart({ data }: FinancialChartProps) {
  return (
    <div className="h-[300px] w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00ffff" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#00ffff" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorCashflow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00ff00" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#00ff00" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <XAxis dataKey="year" stroke="#cccccc" fontSize={10} tickLine={false} axisLine={false} tickMargin={10} fontFamily="monospace" />
          <YAxis 
            stroke="#cccccc" 
            fontSize={10} 
            tickLine={false} 
            axisLine={false}
            tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}k`}
            tickMargin={10}
            fontFamily="monospace"
          />
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#27272a" />
          <Tooltip 
            formatter={(value: any) => [formatCurrency(Number(value) || 0), ""]}
            contentStyle={{ borderRadius: '0', border: '1px solid #3f3f46', backgroundColor: '#000000', color: '#ffffff', fontFamily: 'monospace', fontSize: '10px', textTransform: 'uppercase' }}
            itemStyle={{ fontFamily: 'monospace', fontSize: '10px' }}
          />
          <Area type="step" dataKey="revenue" name="Revenue" stroke="#00ffff" strokeWidth={2} fillOpacity={1} fill="url(#colorRevenue)" />
          <Area type="step" dataKey="cashflow" name="Net Cashflow" stroke="#00ff00" strokeWidth={2} fillOpacity={1} fill="url(#colorCashflow)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
