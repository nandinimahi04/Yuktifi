"use client";
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, BarChart, Activity, TrendingUp, DollarSign, Target, Map, PieChart } from 'lucide-react';
import { YuktiFiInsight } from '@/components/YuktiFiInsight';

export default function AnalyticsOverview() {
  /*
    Provenance correction.

    This page carried a green pulsing badge reading "LIVE DATA" above four metric
    cards whose values are literals in the JSX, and an insight panel stating
    "Algorithm detects a 34% surge in textile-related business plans in Nagpur.
    Recommended to allocate surplus NSFDC funds to manufacturing sector."

    Asserting a data source is a stronger claim than getting a number wrong. A
    bad number can be checked against its source; a "LIVE" badge tells an advisor
    the figure needs no checking at all, and the recommendation is one an
    officer could act on by moving real money between sectors. There is no
    analytics endpoint behind this page, so the badge was false in the strict
    sense rather than merely optimistic.

    The figures are retained as sample content - a dashboard mock with no data
    source is a legitimate thing to design against - but they are now labelled
    as sample data, and the insight is no longer attributed to the algorithm.
    The panel reads "SAMPLE" where it read "LIVE".
  */
  return (
    <div className="p-4 md:p-8 bg-warm-bg min-h-screen text-warm-text font-sans animate-in fade-in duration-500">
      <div className="mb-6 flex items-start gap-3 bg-amber-50 border-2 border-amber-300 rounded-xl p-4">
        <AlertTriangle size={18} className="text-amber-700 mt-0.5 shrink-0" />
        <div>
          <div className="text-sm font-bold text-warm-text">
            Sample data — not live analytics
          </div>
          <p className="text-xs text-warm-muted mt-1">
            No analytics endpoint is wired to this page. Every figure below is a
            placeholder for layout, not a measurement, and nothing here should
            be used to allocate funds.
          </p>
        </div>
      </div>

      <div className="flex justify-between items-end border-b border-warm-border pb-4 mb-8">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-warm-text">Analytics Overview</h1>
          <p className="text-sm text-warm-muted font-medium mt-1">Regional Macro Trends • Maharashtra Zone 3</p>
        </div>
        <div className="text-right">
          <div className="text-xs text-warm-muted font-bold uppercase tracking-wider">Data Source</div>
          <div className="text-amber-700 flex items-center text-sm font-bold mt-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 mr-2"></span> SAMPLE DATA
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 md:gap-6 mb-8">
        <Card className="bg-warm-surface border-warm-border rounded-xl shadow-sm">
          <CardContent className="p-5">
            <p className="text-xs text-warm-muted uppercase tracking-wider font-bold mb-1">Active Plans</p>
            <div className="text-3xl font-black text-warm-text">1,248</div>
            <p className="text-xs text-emerald-600 mt-2 flex items-center font-bold">
              <TrendingUp size={14} className="mr-1" /> +12% this month
            </p>
          </CardContent>
        </Card>
        
        <Card className="bg-warm-surface border-warm-border rounded-xl shadow-sm">
          <CardContent className="p-5">
            <p className="text-xs text-warm-muted uppercase tracking-wider font-bold mb-1">Total Capital Demand</p>
            <div className="text-3xl font-black text-warm-primary">₹48.2 Cr</div>
            <p className="text-xs text-warm-primary/80 mt-2 flex items-center font-bold">
              Target: ₹50 Cr Allocation
            </p>
          </CardContent>
        </Card>

        <Card className="bg-warm-surface border-warm-border rounded-xl shadow-sm">
          <CardContent className="p-5">
            <p className="text-xs text-warm-muted uppercase tracking-wider font-bold mb-1">Avg YuktiFi Score</p>
            <div className="text-3xl font-black text-warm-text">76.4</div>
            <p className="text-xs text-emerald-600 mt-2 flex items-center font-bold">
              <Activity size={14} className="mr-1" /> High Viability Region
            </p>
          </CardContent>
        </Card>

        <Card className="bg-warm-surface border-warm-border rounded-xl shadow-sm">
          <CardContent className="p-5">
            <p className="text-xs text-warm-muted uppercase tracking-wider font-bold mb-1">Loans Disbursed</p>
            <div className="text-3xl font-black text-warm-secondary">₹12.5 Cr</div>
            <p className="text-xs text-warm-muted mt-2 font-bold">
              412 Successful Applicants
            </p>
          </CardContent>
        </Card>
      </div>

      <YuktiFiInsight
        type="info"
        title="SAMPLE INSIGHT — NOT COMPUTED"
        message="Placeholder text. A previous version of this panel read &quot;Algorithm detects a 34% surge in textile-related business plans in Nagpur. Recommended to allocate surplus NSFDC funds to manufacturing sector.&quot; No such analysis runs, and an allocation recommendation attributed to an algorithm that never ran is the most dangerous kind of placeholder to ship."
        className="mb-8 shadow-sm"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-warm-surface border-warm-border rounded-xl shadow-sm min-h-[300px]">
          <CardHeader className="border-b border-warm-border pb-4 bg-warm-bg/50">
            <CardTitle className="text-sm font-bold text-warm-text uppercase tracking-wider flex items-center">
              <PieChart size={16} className="mr-2 text-warm-primary" /> Capital Demand by Sector
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="space-y-5">
              {[
                { label: 'Agriculture & Processing', val: 45, color: 'bg-warm-primary' },
                { label: 'Manufacturing & Textiles', val: 28, color: 'bg-warm-secondary' },
                { label: 'Retail & Distribution', val: 15, color: 'bg-orange-300' },
                { label: 'Services & IT', val: 12, color: 'bg-warm-muted' }
              ].map((item, i) => (
                <div key={i}>
                  <div className="flex justify-between text-xs font-bold text-warm-text mb-2">
                    <span>{item.label}</span>
                    <span>{item.val}%</span>
                  </div>
                  <div className="w-full h-2.5 bg-warm-border rounded-full overflow-hidden">
                    <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.val}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-warm-surface border-warm-border rounded-xl shadow-sm min-h-[300px]">
          <CardHeader className="border-b border-warm-border pb-4 bg-warm-bg/50">
            <CardTitle className="text-sm font-bold text-warm-text uppercase tracking-wider flex items-center">
              <Map size={16} className="mr-2 text-warm-primary" /> High-Viability Zones
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="space-y-4">
              {[
                { zone: 'Nagpur East', score: 88, trend: 'up' },
                { zone: 'Pune Outer', score: 82, trend: 'up' },
                { zone: 'Mumbai North', score: 71, trend: 'down' },
                { zone: 'Nashik Central', score: 65, trend: 'down' }
              ].map((item, i) => (
                <div key={i} className="flex justify-between items-center border-b border-warm-border pb-4 last:border-0 last:pb-0">
                  <div>
                    <div className="text-base font-bold text-warm-text">{item.zone}</div>
                    <div className="text-xs text-warm-muted font-bold mt-1">Viability Score</div>
                  </div>
                  <div className="flex items-center">
                    <div className={`text-2xl font-black mr-3 ${item.score > 80 ? 'text-emerald-600' : 'text-amber-500'}`}>
                      {item.score}
                    </div>
                    {item.trend === 'up' ? 
                      <TrendingUp size={20} className="text-emerald-500" /> : 
                      <TrendingUp size={20} className="text-amber-500 rotate-180" />
                    }
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
