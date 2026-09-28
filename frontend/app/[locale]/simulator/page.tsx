"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "@/routing";
import { useStore } from "@/lib/store";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import { api, type SimulateResponse } from "@/lib/api-client";
import { Loader2, TrendingUp, AlertTriangle, ArrowRight, Settings2, BarChart4, ArrowDown, ArrowUp, Activity, CheckCircle2, ShieldAlert } from "lucide-react";
import { YuktiFiInsight } from "@/components/YuktiFiInsight";
import { useTranslations, useLocale } from "next-intl";

export default function SimulatorPage() {
  const router = useRouter();
  const locale = useLocale();
  const state = useStore();
  const [loading, setLoading] = useState(true);
  
  const [simParams, setSimParams] = useState({
    demand_multiplier: 1.0,
    cost_multiplier: 1.0,
    price_multiplier: 1.0
  });

  const [simLoading, setSimLoading] = useState(false);
  const [error, setError] = useState("");

  const t = useTranslations('simulator');

  useEffect(() => {
    if (!state.analysisResult) {
      // If we don't have analysisResult in memory yet, check if we have a sessionId
      const sessionId = state.sessionId || "2b9bf777-3922-4918-b8bf-9051bec90116";
      api.getFinancialAssumptions(sessionId)
        .then((data) => {
          if (data && data.financials) {
            state.updateState({
              sessionId: sessionId,
              analysisResult: {
                ...state.analysisResult,
                financials: data.financials,
                matched_business: {
                  matched_subcategory: data.category_name || "General Business"
                }
              }
            });
          }
          setLoading(false);
        })
        .catch(() => {
          setError(t('error'));
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, [state.analysisResult, state.sessionId]);

  const handleOverride = async (fieldName: string, value: number) => {
    const sessionId = state.sessionId || "2b9bf777-3922-4918-b8bf-9051bec90116";
    setSimLoading(true);
    try {
      const overrides = { [fieldName]: value };
      const newFinancials = await api.recalculateFinancials({
        session_id: sessionId,
        assumptions: overrides,
      });
      if (newFinancials && newFinancials.financials) {
        state.updateState({
          analysisResult: {
            ...state.analysisResult,
            financials: newFinancials.financials,
          }
        });
      }
      
      // Re-run stress test on the updated baseline
      const res = await api.simulate({
        session_id: sessionId,
        revenue_delta_pct: (simParams.demand_multiplier - 1.0) * 100,
        cost_delta_pct: (simParams.cost_multiplier - 1.0) * 100,
        price_delta_pct: (simParams.price_multiplier - 1.0) * 100,
      });
      state.updateState({ simulationResult: res });
    } catch (e) {
      console.error("Override failed:", e);
    } finally {
      setSimLoading(false);
    }
  };

  const runSimulation = async () => {
    setSimLoading(true);
    setError("");
    try {
      const sessionId = state.sessionId || "2b9bf777-3922-4918-b8bf-9051bec90116";
      const res = await api.simulate({
        session_id: sessionId,
        revenue_delta_pct: (simParams.demand_multiplier - 1.0) * 100,
        cost_delta_pct: (simParams.cost_multiplier - 1.0) * 100,
        price_delta_pct: (simParams.price_multiplier - 1.0) * 100,
      });
      state.updateState({ simulationResult: res });
    } catch (err: unknown) {
      console.error("Simulation API failed:", err);
      setError("Failed to execute deterministic stress simulation. Please check parameters.");
    } finally {
      setSimLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto mt-10">
        <div className="h-64 flex justify-center items-center">
          <Loader2 size={48} className="animate-spin text-forest" />
        </div>
      </div>
    );
  }

  if (error && !state.analysisResult) {
    return <div className="text-red-700 p-4 font-bold bg-red-50 rounded-xl m-4 border border-red-200">{error}</div>;
  }
  
  const baseParams = state.analysisResult;
  const simResults = state.simulationResult;
  
  // Extract baseline metrics
  const baseRoi = baseParams?.financials?.roi_pct ?? baseParams?.financials?.roi_on_total_project_pct ?? 0;
  const baseDscr = baseParams?.financials?.dscr ?? 0;

  // Extract simulated metrics
  const simRoi = simResults ? (simResults.simulated_roi ?? simResults.roi_pct ?? simResults.financials?.roi_pct ?? 0) : null;
  const simDscr = simResults ? (simResults.dscr ?? simResults.financials?.dscr ?? 0) : null;
  const survivesStress = simResults ? (simResults.survives_stress ?? (simDscr != null ? simDscr >= 1.0 : true)) : true;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="max-w-5xl mx-auto p-4 md:p-8 pb-20 font-sans"
    >
      <div className="flex flex-col sm:flex-row justify-between items-center sm:items-end mb-8 gap-4 border-b border-premium-border pb-6 mt-4">
        <div>
          <h1 className="text-3xl font-bold text-ink flex items-center font-display">
            <Activity className="mr-3 text-forest-deep" size={32} />
            {t('title')}
          </h1>
          <p className="text-ink-soft mt-2 font-medium">
            {t('subtitle')} <strong className="text-ink">{baseParams?.matched_business?.matched_subcategory || t('yourBusiness')}</strong>
          </p>
        </div>
        <Button onClick={() => router.push('/report')} className="bg-white text-ink border border-premium-border hover:bg-forest-light/30 hover:border-forest transition-colors shadow-sm font-bold">
          {t('generateReport')} <ArrowRight size={16} className="ml-2" />
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls */}
        <Card className="lg:col-span-1 border-premium-border shadow-sm bg-white rounded-2xl overflow-hidden">
          <CardHeader className="bg-gray-50/70 pb-4 border-b border-premium-border">
            <CardTitle className="text-xs font-bold text-ink-soft flex items-center uppercase tracking-wider">
              <Settings2 size={16} className="mr-2 text-ink" />
              {t('variables.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6 space-y-6">
            <div className="space-y-4 border-b border-premium-border pb-6">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-ink-soft">Project Cost (₹)</label>
                <input 
                  type="number"
                  className="w-full bg-gray-50/50 border border-premium-border rounded-xl px-3.5 py-2 text-sm font-bold text-ink focus:border-forest focus:bg-white outline-none transition-all"
                  defaultValue={baseParams?.financials?.project_cost || ""}
                  onBlur={(e) => {
                    const val = Number(e.target.value);
                    if (val && !isNaN(val) && val !== baseParams?.financials?.project_cost) {
                      handleOverride("project_cost", val);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const val = Number(e.currentTarget.value);
                      if (val && !isNaN(val) && val !== baseParams?.financials?.project_cost) {
                        handleOverride("project_cost", val);
                      }
                    }
                  }}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-ink-soft">Expected Monthly Revenue (₹)</label>
                <input 
                  type="number"
                  className="w-full bg-gray-50/50 border border-premium-border rounded-xl px-3.5 py-2 text-sm font-bold text-ink focus:border-forest focus:bg-white outline-none transition-all"
                  defaultValue={baseParams?.financials?.monthly_revenue || ""}
                  onBlur={(e) => {
                    const val = Number(e.target.value);
                    if (val && !isNaN(val) && val !== baseParams?.financials?.monthly_revenue) {
                      handleOverride("monthly_revenue", val);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const val = Number(e.currentTarget.value);
                      if (val && !isNaN(val) && val !== baseParams?.financials?.monthly_revenue) {
                        handleOverride("monthly_revenue", val);
                      }
                    }
                  }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-bold uppercase tracking-wider text-ink">{t('variables.demand')}</label>
                <span className="text-xs font-bold font-mono text-white bg-ink px-2 py-0.5 rounded-md">{(simParams.demand_multiplier * 100).toFixed(0)}%</span>
              </div>
              <input 
                type="range" 
                min="0.5" max="1.5" step="0.05" 
                value={simParams.demand_multiplier}
                onChange={(e) => setSimParams({...simParams, demand_multiplier: parseFloat(e.target.value)})}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-forest"
              />
              <div className="flex justify-between text-[11px] font-semibold text-ink-soft mt-1.5">
                <span>{t('variables.demandLow')}</span>
                <span>Normal (100%)</span>
                <span>{t('variables.demandHigh')}</span>
              </div>
            </div>
            
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-bold uppercase tracking-wider text-ink">{t('variables.costs')}</label>
                <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded-md ${simParams.cost_multiplier > 1 ? 'bg-red-600 text-white' : 'bg-ink text-white'}`}>{(simParams.cost_multiplier * 100).toFixed(0)}%</span>
              </div>
              <input 
                type="range" 
                min="0.7" max="1.5" step="0.05" 
                value={simParams.cost_multiplier}
                onChange={(e) => setSimParams({...simParams, cost_multiplier: parseFloat(e.target.value)})}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-forest"
              />
              <div className="flex justify-between text-[11px] font-semibold text-ink-soft mt-1.5">
                <span>{t('variables.costsLow')}</span>
                <span>Normal (100%)</span>
                <span>{t('variables.costsHigh')}</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-bold uppercase tracking-wider text-ink">{t('variables.price')}</label>
                <span className="text-xs font-bold font-mono text-white bg-ink px-2 py-0.5 rounded-md">{(simParams.price_multiplier * 100).toFixed(0)}%</span>
              </div>
              <input 
                type="range" 
                min="0.8" max="1.3" step="0.05" 
                value={simParams.price_multiplier}
                onChange={(e) => setSimParams({...simParams, price_multiplier: parseFloat(e.target.value)})}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-forest"
              />
              <div className="flex justify-between text-[11px] font-semibold text-ink-soft mt-1.5">
                <span>{t('variables.priceLow')}</span>
                <span>Normal (100%)</span>
                <span>{t('variables.priceHigh')}</span>
              </div>
            </div>

            <Button 
              className="w-full mt-4 bg-forest text-white hover:bg-forest-deep font-bold py-5 rounded-xl shadow-sm transition-all text-sm uppercase tracking-wider" 
              onClick={runSimulation}
              disabled={simLoading || baseParams?.financials?.financial_status === "INSUFFICIENT_INPUT" || (baseParams?.financials?.financial_status as any)?.value === "INSUFFICIENT_INPUT"}
            >
              {simLoading ? <Loader2 className="animate-spin mr-2" size={18} /> : <BarChart4 className="mr-2" size={18} />}
              {t('variables.runTest')}
            </Button>
          </CardContent>
        </Card>

        {/* Results */}
        <Card className="lg:col-span-2 border-premium-border bg-white shadow-sm rounded-2xl overflow-hidden">
          <CardHeader className="bg-gray-50/70 pb-4 border-b border-premium-border">
            <CardTitle className="text-xs font-bold text-ink-soft flex items-center uppercase tracking-wider">
              <TrendingUp size={16} className="mr-2 text-ink" />
              {t('results.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            {baseParams?.financials?.financial_status === "INSUFFICIENT_INPUT" || (baseParams?.financials?.financial_status as any)?.value === "INSUFFICIENT_INPUT" ? (
              <div className="h-64 flex flex-col items-center justify-center text-red-600 border-2 border-dashed border-red-200 rounded-xl bg-red-50 p-6 text-center">
                <AlertTriangle size={48} className="mb-4 opacity-80" />
                <h3 className="font-bold text-lg mb-2">Insufficient Inputs</h3>
                <p className="text-sm">Please provide Project Cost and Monthly Revenue in the controls panel to unlock simulations.</p>
              </div>
            ) : !simResults ? (
              <div className="h-72 flex flex-col items-center justify-center text-ink-soft border border-dashed border-premium-border rounded-xl bg-gray-50/50 p-6 text-center">
                <Settings2 size={40} className="mb-3 text-ink-faint animate-pulse" />
                <h4 className="font-bold text-ink text-base mb-1">{t('results.placeholder')}</h4>
                <p className="text-xs max-w-sm mb-4">Adjust the demand, cost, and price multipliers on the left and click <strong>Run Stress Test</strong> to simulate economic scenarios.</p>
                <Button onClick={runSimulation} className="bg-forest text-white hover:bg-forest-deep text-xs font-bold px-4 py-2 rounded-lg">
                  Run Baseline Simulation
                </Button>
              </div>
            ) : (
              <motion.div 
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="space-y-6"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* BEFORE Card */}
                  <div className="bg-gray-50/60 border border-premium-border rounded-xl p-5 shadow-sm">
                    <div className="text-xs font-bold text-ink-soft uppercase tracking-wider mb-4 border-b border-premium-border pb-2 flex justify-between items-center">
                      <span>{t('results.before')}</span>
                      <span className="text-[10px] font-semibold bg-white border border-premium-border px-2 py-0.5 rounded text-ink">Baseline</span>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <div className="text-xs font-bold text-ink-soft uppercase tracking-wider mb-1">{t('results.roi')}</div>
                        <div className="text-2xl font-bold font-display text-ink">{baseRoi.toFixed(1)}%</div>
                      </div>
                      <div>
                        <div className="text-xs font-bold text-ink-soft uppercase tracking-wider mb-1">{t('results.dscr')}</div>
                        <div className="text-2xl font-bold font-display text-ink">{baseDscr ? `${baseDscr.toFixed(2)}x` : "—"}</div>
                      </div>
                    </div>
                  </div>
                  
                  {/* AFTER Card */}
                  <div className={`border rounded-xl p-5 shadow-sm ${survivesStress ? 'bg-emerald-50/40 border-emerald-200' : 'bg-red-50/40 border-red-200'}`}>
                    <div className="text-xs font-bold text-ink-soft uppercase tracking-wider mb-4 border-b border-premium-border/50 pb-2 flex justify-between items-center">
                      <span>{t('results.after')}</span>
                      {survivesStress ? (
                        <span className="bg-emerald-100 text-emerald-800 px-2.5 py-0.5 rounded text-[11px] font-bold tracking-wide border border-emerald-300 flex items-center gap-1">
                          <CheckCircle2 size={12}/> {t('results.safe')}
                        </span>
                      ) : (
                        <span className="bg-red-100 text-red-800 px-2.5 py-0.5 rounded text-[11px] font-bold tracking-wide border border-red-300 flex items-center gap-1">
                          <ShieldAlert size={12}/> {t('results.risk')}
                        </span>
                      )}
                    </div>
                    <div className="space-y-4">
                      <div>
                        <div className="text-xs font-bold text-ink-soft uppercase tracking-wider mb-1">{t('results.roi')}</div>
                        <div className="flex items-center">
                          <div className={`text-2xl font-bold font-display ${simRoi != null && simRoi >= baseRoi ? 'text-emerald-700' : 'text-ink'}`}>
                            {simRoi != null ? `${simRoi.toFixed(1)}%` : "—"}
                          </div>
                          {simRoi != null && (simRoi >= baseRoi ? <ArrowUp size={18} className="text-emerald-600 ml-1.5" /> : <ArrowDown size={18} className="text-red-500 ml-1.5" />)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs font-bold text-ink-soft uppercase tracking-wider mb-1">{t('results.dscr')}</div>
                        <div className="flex items-center">
                          <div className={`text-2xl font-bold font-display ${simDscr != null && simDscr >= baseDscr ? 'text-emerald-700' : 'text-ink'}`}>
                            {simDscr != null ? `${simDscr.toFixed(2)}x` : "—"}
                          </div>
                          {simDscr != null && (simDscr >= baseDscr ? <ArrowUp size={18} className="text-emerald-600 ml-1.5" /> : <ArrowDown size={18} className="text-red-500 ml-1.5" />)}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className={`p-4 rounded-xl border text-sm font-medium ${survivesStress ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-red-50 border-red-200 text-red-900'}`}>
                  <div className="flex items-start gap-2.5">
                    {survivesStress ? <CheckCircle2 size={18} className="text-emerald-600 mt-0.5 shrink-0" /> : <AlertTriangle size={18} className="text-red-600 mt-0.5 shrink-0" />}
                    <div>
                      <div className="font-bold text-xs uppercase tracking-wider mb-0.5">
                        {survivesStress ? t('results.viableTitle') : t('results.riskTitle')}
                      </div>
                      <div className="text-xs text-ink-soft leading-relaxed">
                        {survivesStress
                          ? t('results.viableDesc', { dscr: simDscr != null ? simDscr.toFixed(2) : "N/A" })
                          : t('results.riskDesc', { dscr: simDscr != null ? simDscr.toFixed(2) : "0.00" })
                        }
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}
