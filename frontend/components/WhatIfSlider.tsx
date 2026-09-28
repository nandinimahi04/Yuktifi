"use client";
import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { formatCurrency } from "@/lib/formatters";
import { Loader2, TrendingUp, TrendingDown, DollarSign } from "lucide-react";
import { VerdictBanner } from "./VerdictBanner";

interface Props {
  sessionId: string;
}

export function WhatIfSlider({ sessionId }: Props) {
  const [revenueDelta, setRevenueDelta] = useState(0);
  const [costDelta, setCostDelta] = useState(0);
  const [tenureOverride, setTenureOverride] = useState<number | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Debounced API call
  const runSimulation = useCallback(async (rDelta: number, cDelta: number, tOverride: number | null) => {
    setLoading(true);
    try {
      const res = await api.simulate({
        session_id: sessionId,
        revenue_delta_pct: rDelta,
        cost_delta_pct: cDelta,
        // An untouched slider means "no override", which is the absence of a
        // value rather than a value of null.
        tenure_override_years: tOverride ?? undefined,
      });
      setResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    const timer = setTimeout(() => {
      runSimulation(revenueDelta, costDelta, tenureOverride);
    }, 500); // 500ms debounce
    return () => clearTimeout(timer);
  }, [revenueDelta, costDelta, tenureOverride, runSimulation]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card>
        <CardContent className="p-6 space-y-8">
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="font-semibold text-slate-700 flex items-center">
                <TrendingUp size={16} className="mr-2 text-indigo-500" />
                Revenue Change
              </label>
              <span className={`font-sans font-bold ${revenueDelta >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                {revenueDelta > 0 ? "+" : ""}{revenueDelta}%
              </span>
            </div>
            <input 
              type="range" 
              min="-50" max="50" step="5" 
              value={revenueDelta}
              onChange={(e) => setRevenueDelta(parseInt(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
            <div className="flex justify-between text-xs text-slate-400 mt-1">
              <span>-50% (Worst Case)</span>
              <span>Baseline (0%)</span>
              <span>+50% (Best Case)</span>
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="font-semibold text-slate-700 flex items-center">
                <TrendingDown size={16} className="mr-2 text-rose-500" />
                Variable Cost Change
              </label>
              <span className={`font-sans font-bold ${costDelta <= 0 ? "text-emerald-600" : "text-red-600"}`}>
                {costDelta > 0 ? "+" : ""}{costDelta}%
              </span>
            </div>
            <input 
              type="range" 
              min="-30" max="50" step="5" 
              value={costDelta}
              onChange={(e) => setCostDelta(parseInt(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-rose-600"
            />
            <div className="flex justify-between text-xs text-slate-400 mt-1">
              <span>-30% (Cheaper)</span>
              <span>Baseline (0%)</span>
              <span>+50% (Inflation)</span>
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="font-semibold text-slate-700 flex items-center">
                <DollarSign size={16} className="mr-2 text-amber-500" />
                Loan Tenure (Years)
              </label>
              <span className="font-sans font-bold text-amber-600">
                {tenureOverride || "Default"}
              </span>
            </div>
            <div className="flex space-x-2">
              {[null, 3, 5, 7].map((yr) => (
                <button
                  key={yr || "def"}
                  onClick={() => setTenureOverride(yr)}
                  className={`flex-1 py-2 text-sm rounded-md font-medium transition-colors ${
                    tenureOverride === yr 
                      ? "bg-amber-500 text-warm-text shadow-sm" 
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {yr ? `${yr} Yrs` : "Default"}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-slate-900 text-warm-text relative overflow-hidden">
        {loading && (
          <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-10">
            <Loader2 size={32} className="animate-spin text-indigo-400" />
          </div>
        )}
        
        <CardContent className="p-6 h-full flex flex-col justify-between relative z-0">
          <div>
            <h3 className="text-slate-400 text-sm font-semibold uppercase tracking-wider mb-6">Simulated Outcome</h3>
            
            <div className="grid grid-cols-2 gap-6 mb-8">
              <div>
                <p className="text-slate-400 text-sm mb-1">Monthly Net Profit</p>
                <p className={`text-3xl font-bold ${result?.net_profit < 0 ? "text-red-400" : "text-warm-text"}`}>
                  {result ? formatCurrency(result.net_profit) : "..."}
                </p>
              </div>
              <div>
                <p className="text-slate-400 text-sm mb-1">New Monthly Installment</p>
                <p className="text-3xl font-bold text-warm-text">
                  {result ? formatCurrency(result.emi) : "..."}
                </p>
              </div>
              <div>
                <p className="text-slate-400 text-sm mb-1">Loan Repayment Capacity</p>
                <p className={`text-2xl font-bold ${
                  result?.dscr == null
                    ? "text-slate-400"
                    : result.dscr >= 1.5
                      ? "text-emerald-400"
                      : result.dscr >= 1.0
                        ? "text-amber-400"
                        : "text-red-400"
                }`}>
                  {!result
                    ? "..."
                    : result.dscr == null
                      ? "N/A"
                      : `${result.dscr.toFixed(2)}x`}
                </p>
                {result?.dscr == null && (
                  <p className="text-xs text-slate-500 mt-1">
                    No debt assumed, so coverage does not apply.
                  </p>
                )}
              </div>
              <div>
                <p className="text-slate-400 text-sm mb-1">Break-Even Units</p>
                <p className="text-2xl font-bold text-warm-text">
                  {result
                    ? result.break_even_units == null
                      ? "N/A"
                      : Math.round(result.break_even_units)
                    : "..."}
                </p>
              </div>
            </div>
          </div>
          
          <div className="mt-4 border-t border-slate-700 pt-4">
            {result && <VerdictBanner verdict={result.verdict} />}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
