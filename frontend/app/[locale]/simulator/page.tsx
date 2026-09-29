"use client";

import React, { useEffect, useState, useMemo } from "react";
import { useRouter } from "@/routing";
import { useStore } from "@/lib/store";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import { api, type SimulateResponse } from "@/lib/api-client";
<<<<<<< HEAD
import { Loader2, TrendingUp, AlertTriangle, ArrowRight, Settings2, BarChart4, ArrowDown, ArrowUp, Activity, CheckCircle2, ShieldAlert } from "lucide-react";
import { YuktiFiInsight } from "@/components/YuktiFiInsight";
=======
import {
  Loader2,
  TrendingUp,
  AlertTriangle,
  ArrowRight,
  Settings2,
  BarChart4,
  ArrowDown,
  ArrowUp,
  Activity,
  CheckCircle2,
  ShieldCheck,
  RotateCcw
} from "lucide-react";
>>>>>>> cleanup-final
import { useTranslations, useLocale } from "next-intl";
import Link from "next/link";

export default function SimulatorPage() {
  const router = useRouter();
  const locale = useLocale();
  const state = useStore();
  const [loading, setLoading] = useState(true);

  const [simParams, setSimParams] = useState({
    demand_multiplier: 1.0,
    cost_multiplier: 1.0,
    price_multiplier: 1.0,
  });

  const [customProjectCost, setCustomProjectCost] = useState<number | null>(null);
  const [customMonthlyRevenue, setCustomMonthlyRevenue] = useState<number | null>(null);

  const [simLoading, setSimLoading] = useState(false);
  const [error, setError] = useState("");

  const t = useTranslations("simulator");

  useEffect(() => {
    if (!state.analysisResult) {
<<<<<<< HEAD
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
=======
      setError(t("error") || "Please complete financial planning first to run simulations.");
      setLoading(false);
>>>>>>> cleanup-final
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

<<<<<<< HEAD
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
=======
  const baseParams = state.analysisResult;

  // Resolve authentic business name
  const businessName = useMemo(() => {
    if (state.categoryName && state.categoryName !== "your enterprise") return state.categoryName;
    if (baseParams?.business?.area_of_interest) return baseParams.business.area_of_interest;
    if (baseParams?.business?.matched_subcategory) return baseParams.business.matched_subcategory;
    if (baseParams?.business?.matched_category_id) {
      return baseParams.business.matched_category_id.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());
>>>>>>> cleanup-final
    }
    if (baseParams?.matched_business?.matched_subcategory) return baseParams.matched_business.matched_subcategory;
    return "Food & Beverage";
  }, [state.categoryName, baseParams]);

  // Extract Baseline Parameters
  const baseMonthlyRevenue = useMemo(() => {
    return Number(baseParams?.financials?.monthly_revenue || 72000);
  }, [baseParams]);

  const baseProjectCost = useMemo(() => {
    return Number(baseParams?.financials?.project_cost || baseParams?.financials?.total_project_cost || 200000);
  }, [baseParams]);

  const baseMonthlyOpex = useMemo(() => {
    return Number(baseParams?.financials?.monthly_opex || baseParams?.financials?.monthly_expenses || 25000);
  }, [baseParams]);

  const baseMonthlyCogs = useMemo(() => {
    return Number(baseParams?.financials?.monthly_cogs || (baseMonthlyRevenue * 0.45));
  }, [baseParams, baseMonthlyRevenue]);

  const baseMonthlyEmi = useMemo(() => {
    return Number(baseParams?.financials?.monthly_emi || baseParams?.financials?.emi || (baseProjectCost * 0.75 * 0.02) || 3000);
  }, [baseParams, baseProjectCost]);

  const baseNetProfit = useMemo(() => {
    return Number(baseParams?.financials?.net_profit || (baseMonthlyRevenue - baseMonthlyCogs - baseMonthlyOpex - baseMonthlyEmi));
  }, [baseParams, baseMonthlyRevenue, baseMonthlyCogs, baseMonthlyOpex, baseMonthlyEmi]);

  const baseRoi = useMemo(() => {
    if (baseParams?.financials?.roi_pct != null) return Number(baseParams.financials.roi_pct);
    return baseProjectCost > 0 ? (baseNetProfit * 12 / baseProjectCost) * 100 : 45.0;
  }, [baseParams, baseNetProfit, baseProjectCost]);

  const baseDscr = useMemo(() => {
    if (baseParams?.financials?.dscr != null) return Number(baseParams.financials.dscr);
    return baseMonthlyEmi > 0 ? (baseNetProfit + baseMonthlyEmi) / baseMonthlyEmi : 4.43;
  }, [baseParams, baseNetProfit, baseMonthlyEmi]);

  // Active working baseline
  const activeProjectCost = customProjectCost ?? baseProjectCost;
  const activeMonthlyRevenue = customMonthlyRevenue ?? baseMonthlyRevenue;

  // Real-Time Stress Test Simulation Math
  const simulation = useMemo(() => {
    const rev = activeMonthlyRevenue * simParams.demand_multiplier * simParams.price_multiplier;
    const cogs = baseMonthlyCogs * simParams.demand_multiplier * simParams.cost_multiplier;
    const opex = baseMonthlyOpex * simParams.cost_multiplier;
    const grossProfit = rev - cogs;
    const ebitda = grossProfit - opex;
    const emi = baseMonthlyEmi;
    const netProfit = ebitda - emi;

    const roi = activeProjectCost > 0
      ? Math.max(-100, Math.round(((netProfit * 12) / activeProjectCost) * 1000) / 10)
      : 0;

    const dscr = emi > 0
      ? Math.max(0, Math.round(((netProfit + emi) / emi) * 100) / 100)
      : 10.0;

    const breakEvenRevenue = (cogs + opex + emi);
    const breakEvenUnits = activeMonthlyRevenue > 0
      ? Math.round((breakEvenRevenue / (activeMonthlyRevenue / 1000)))
      : 0;

    const survives = dscr >= 1.0 && netProfit > 0;

    return {
      revenue: Math.round(rev),
      netProfit: Math.round(netProfit),
      roi,
      dscr,
      breakEvenRevenue: Math.round(breakEvenRevenue),
      breakEvenUnits,
      survives,
    };
  }, [
    activeMonthlyRevenue,
    activeProjectCost,
    baseMonthlyCogs,
    baseMonthlyOpex,
    baseMonthlyEmi,
    simParams,
  ]);

  const handleReset = () => {
    setSimParams({
      demand_multiplier: 1.0,
      cost_multiplier: 1.0,
      price_multiplier: 1.0,
    });
    setCustomProjectCost(null);
    setCustomMonthlyRevenue(null);
  };

  const handleRunTest = async () => {
    setSimLoading(true);
    // Simulate brief processing for visual feedback
    await new Promise((resolve) => setTimeout(resolve, 300));
    setSimLoading(false);
  };

  if (loading) {
    return (
<<<<<<< HEAD
      <div className="max-w-4xl mx-auto mt-10">
        <div className="h-64 flex justify-center items-center">
          <Loader2 size={48} className="animate-spin text-forest" />
        </div>
=======
      <div className="max-w-4xl mx-auto mt-10 min-h-[50vh] flex flex-col items-center justify-center space-y-4">
        <Loader2 size={48} className="animate-spin text-forest" />
        <p className="text-forest-deep font-medium animate-pulse">
          Loading What-If Simulator...
        </p>
>>>>>>> cleanup-final
      </div>
    );
  }

<<<<<<< HEAD
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
=======
  if (error || !state.analysisResult) {
    return (
      <div className="max-w-4xl mx-auto mt-10 p-6">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-8 text-center">
            <AlertTriangle className="mx-auto text-red-500 mb-4" size={48} />
            <h2 className="text-xl font-bold text-red-700 mb-2">Simulator Unavailable</h2>
            <p className="text-red-600 mb-6">{error}</p>
            <Link
              href="/"
              className="inline-flex items-center bg-forest text-white px-6 py-3 rounded-xl font-bold hover:bg-forest-deep transition-colors"
            >
              Start Financial Planning <ArrowRight size={16} className="ml-2" />
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }
>>>>>>> cleanup-final

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="max-w-6xl mx-auto p-4 md:p-8 pb-24 font-sans text-forest-deep"
    >
<<<<<<< HEAD
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
=======
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-8 gap-4 border-b border-premium-border pb-6 mt-2">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold uppercase tracking-wider mb-2">
            <Activity size={14} className="text-forest" />
            Deterministic Sensitivity Engine
          </div>
          <h1 className="text-3xl font-black tracking-tight text-forest-deep">
            What-If Simulator & Stress Testing
          </h1>
          <p className="text-ink-soft mt-1 text-sm font-medium">
            Stress test your business model for:{" "}
            <strong className="text-forest-deep font-bold">{businessName}</strong>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleReset}
            className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-premium-border text-ink-soft hover:bg-black/5 font-bold text-xs transition-colors"
          >
            <RotateCcw size={14} />
            Reset Defaults
          </button>
          <Link href="/report">
            <button className="inline-flex items-center gap-2 px-5 py-2.5 bg-forest hover:bg-forest-deep text-white font-semibold rounded-xl shadow-sm transition-colors text-xs shrink-0">
              Generate Report <ArrowRight size={14} />
            </button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Controls Column */}
        <Card className="lg:col-span-5 border-premium-border shadow-card bg-white rounded-3xl overflow-hidden">
          <CardHeader className="bg-emerald-50/40 pb-4 border-b border-premium-border/60">
            <CardTitle className="text-xs font-bold text-forest-deep uppercase tracking-wider flex items-center">
              <Settings2 size={16} className="mr-2 text-forest" />
              Adjust Stress Parameters
            </CardTitle>
          </CardHeader>

          <CardContent className="pt-6 space-y-6">
            {/* Direct Inputs */}
            <div className="space-y-4 pb-4 border-b border-premium-border/60">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-forest-deep uppercase tracking-wider">
                  Total Project Cost (₹)
                </label>
                <input
                  type="number"
                  className="w-full bg-cream/50 border border-premium-border rounded-xl px-3.5 py-2.5 text-sm font-bold text-forest-deep focus:border-forest outline-none transition-colors"
                  value={activeProjectCost}
                  onChange={(e) => setCustomProjectCost(Number(e.target.value) || 0)}
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-forest-deep uppercase tracking-wider">
                  Expected Monthly Revenue (₹)
                </label>
                <input
                  type="number"
                  className="w-full bg-cream/50 border border-premium-border rounded-xl px-3.5 py-2.5 text-sm font-bold text-forest-deep focus:border-forest outline-none transition-colors"
                  value={activeMonthlyRevenue}
                  onChange={(e) => setCustomMonthlyRevenue(Number(e.target.value) || 0)}
                />
              </div>
            </div>

            {/* Demand Slider */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-bold text-forest-deep uppercase tracking-wider">
                  Demand Shock
                </label>
                <span className="text-xs font-bold text-white bg-forest px-2.5 py-1 rounded-lg">
                  {(simParams.demand_multiplier * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                min="0.5"
                max="1.5"
                step="0.05"
                value={simParams.demand_multiplier}
                onChange={(e) =>
                  setSimParams({ ...simParams, demand_multiplier: parseFloat(e.target.value) })
                }
                className="w-full h-2 bg-cream rounded-lg appearance-none cursor-pointer accent-forest"
              />
              <div className="flex justify-between text-[11px] font-semibold text-ink-soft mt-1.5">
                <span>-50% (Slump)</span>
                <span>Baseline (100%)</span>
                <span>+50% (Surge)</span>
>>>>>>> cleanup-final
              </div>
            </div>

            {/* Cost Inflation Slider */}
            <div>
              <div className="flex justify-between items-center mb-2">
<<<<<<< HEAD
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
=======
                <label className="text-xs font-bold text-forest-deep uppercase tracking-wider">
                  Cost Inflation
                </label>
                <span
                  className={`text-xs font-bold px-2.5 py-1 rounded-lg text-white ${
                    simParams.cost_multiplier > 1.0 ? "bg-red-500" : "bg-emerald-600"
                  }`}
                >
                  {(simParams.cost_multiplier * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                min="0.8"
                max="1.5"
                step="0.05"
                value={simParams.cost_multiplier}
                onChange={(e) =>
                  setSimParams({ ...simParams, cost_multiplier: parseFloat(e.target.value) })
                }
                className="w-full h-2 bg-cream rounded-lg appearance-none cursor-pointer accent-red-500"
              />
              <div className="flex justify-between text-[11px] font-semibold text-ink-soft mt-1.5">
                <span>-20% (Savings)</span>
                <span>Normal (100%)</span>
                <span>+50% (Inflation)</span>
>>>>>>> cleanup-final
              </div>
            </div>

            {/* Pricing Power Slider */}
            <div>
              <div className="flex justify-between items-center mb-2">
<<<<<<< HEAD
                <label className="text-xs font-bold uppercase tracking-wider text-ink">{t('variables.price')}</label>
                <span className="text-xs font-bold font-mono text-white bg-ink px-2 py-0.5 rounded-md">{(simParams.price_multiplier * 100).toFixed(0)}%</span>
=======
                <label className="text-xs font-bold text-forest-deep uppercase tracking-wider">
                  Pricing Realization
                </label>
                <span className="text-xs font-bold text-white bg-amber-600 px-2.5 py-1 rounded-lg">
                  {(simParams.price_multiplier * 100).toFixed(0)}%
                </span>
>>>>>>> cleanup-final
              </div>
              <input
                type="range"
                min="0.8"
                max="1.3"
                step="0.05"
                value={simParams.price_multiplier}
<<<<<<< HEAD
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
=======
                onChange={(e) =>
                  setSimParams({ ...simParams, price_multiplier: parseFloat(e.target.value) })
                }
                className="w-full h-2 bg-cream rounded-lg appearance-none cursor-pointer accent-amber-600"
              />
              <div className="flex justify-between text-[11px] font-semibold text-ink-soft mt-1.5">
                <span>-20% (Discount)</span>
                <span>List Price</span>
                <span>+30% (Premium)</span>
              </div>
            </div>

            <Button
              onClick={handleRunTest}
              className="w-full bg-forest hover:bg-forest-deep text-white font-bold py-3.5 rounded-xl shadow-sm transition-all text-sm mt-4"
              disabled={simLoading}
            >
              {simLoading ? (
                <Loader2 className="animate-spin mr-2" size={16} />
              ) : (
                <BarChart4 className="mr-2" size={16} />
              )}
              Run Stress Test Simulation
>>>>>>> cleanup-final
            </Button>
          </CardContent>
        </Card>

<<<<<<< HEAD
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
=======
        {/* Results Column */}
        <div className="lg:col-span-7 space-y-6">
          {/* Top Status Banner */}
          <div
            className={`p-5 rounded-3xl border shadow-card flex items-start gap-4 transition-all ${
              simulation.survives
                ? "bg-emerald-50/90 border-emerald-200"
                : "bg-rose-50/90 border-rose-200"
            }`}
          >
            {simulation.survives ? (
              <ShieldCheck className="text-emerald-600 mt-0.5 shrink-0" size={28} />
            ) : (
              <AlertTriangle className="text-red-500 mt-0.5 shrink-0" size={28} />
            )}
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-base text-forest-deep">
                  {simulation.survives
                    ? "Resilient Under Tested Stress Scenario"
                    : "High Risk of Cash Flow Shortfall"}
                </h3>
                <span
                  className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                    simulation.survives
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : "bg-rose-100 text-rose-800 border border-rose-300"
                  }`}
                >
                  {simulation.survives ? "Viable" : "Action Required"}
                </span>
              </div>
              <p className="text-xs text-ink-soft mt-1 leading-relaxed">
                {simulation.survives
                  ? `With DSCR at ${simulation.dscr.toFixed(2)}x and net monthly profit of ₹${simulation.netProfit.toLocaleString(
                      "en-IN"
                    )}, the project comfortably covers all operating costs and debt obligations.`
                  : `Projected monthly net cash flow drops to ₹${simulation.netProfit.toLocaleString(
                      "en-IN"
                    )} with DSCR at ${simulation.dscr.toFixed(
                      2
                    )}x. Consider restructuring fixed expenses or increasing equity equity buffer.`}
              </p>
            </div>
          </div>

          {/* Before & After Comparison Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Baseline Card */}
            <Card className="border-premium-border shadow-card bg-white rounded-3xl overflow-hidden">
              <CardHeader className="bg-cream/60 pb-3 border-b border-premium-border/60">
                <CardTitle className="text-xs font-bold text-ink-soft uppercase tracking-wider">
                  Baseline Outlook (Normal)
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-5 space-y-4">
                <div>
                  <span className="text-[11px] font-bold text-ink-soft uppercase tracking-wider">
                    Annual Return (ROI)
                  </span>
                  <div className="text-2xl font-black text-forest-deep mt-0.5">
                    {baseRoi.toFixed(1)}%
                  </div>
                </div>
                <div>
                  <span className="text-[11px] font-bold text-ink-soft uppercase tracking-wider">
                    Debt Coverage (DSCR)
                  </span>
                  <div className="text-2xl font-black text-forest-deep mt-0.5">
                    {baseDscr.toFixed(2)}x
                  </div>
                </div>
                <div className="pt-2 border-t border-premium-border/60 flex justify-between text-xs">
                  <span className="text-ink-soft font-medium">Monthly Net Profit</span>
                  <span className="font-bold text-forest-deep">
                    ₹{Math.round(baseNetProfit).toLocaleString("en-IN")}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Simulated Stress Card */}
            <Card
              className={`border shadow-card rounded-3xl overflow-hidden ${
                simulation.survives ? "bg-white border-emerald-200" : "bg-white border-rose-200"
              }`}
            >
              <CardHeader
                className={`pb-3 border-b ${
                  simulation.survives
                    ? "bg-emerald-50/50 border-emerald-200"
                    : "bg-rose-50/50 border-rose-200"
                }`}
              >
                <div className="flex justify-between items-center">
                  <CardTitle className="text-xs font-bold text-forest-deep uppercase tracking-wider">
                    Simulated Stress Output
                  </CardTitle>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      simulation.survives
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-rose-100 text-rose-800"
                    }`}
                  >
                    Live Mode
                  </span>
                </div>
              </CardHeader>
              <CardContent className="pt-5 space-y-4">
                <div>
                  <span className="text-[11px] font-bold text-ink-soft uppercase tracking-wider">
                    Simulated ROI
                  </span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <div
                      className={`text-2xl font-black ${
                        simulation.roi >= baseRoi ? "text-emerald-700" : "text-rose-600"
                      }`}
                    >
                      {simulation.roi.toFixed(1)}%
>>>>>>> cleanup-final
                    </div>
                    {simulation.roi >= baseRoi ? (
                      <ArrowUp size={18} className="text-emerald-600" />
                    ) : (
                      <ArrowDown size={18} className="text-rose-500" />
                    )}
                  </div>
                </div>

<<<<<<< HEAD
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
=======
                <div>
                  <span className="text-[11px] font-bold text-ink-soft uppercase tracking-wider">
                    Simulated DSCR
                  </span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <div
                      className={`text-2xl font-black ${
                        simulation.dscr >= 1.25
                          ? "text-emerald-700"
                          : simulation.dscr >= 1.0
                          ? "text-amber-600"
                          : "text-rose-600"
                      }`}
                    >
                      {simulation.dscr.toFixed(2)}x
                    </div>
                    {simulation.dscr >= baseDscr ? (
                      <ArrowUp size={18} className="text-emerald-600" />
                    ) : (
                      <ArrowDown size={18} className="text-rose-500" />
                    )}
                  </div>
                </div>

                <div className="pt-2 border-t border-premium-border/60 flex justify-between text-xs">
                  <span className="text-ink-soft font-medium">Simulated Monthly Net</span>
                  <span
                    className={`font-bold ${
                      simulation.netProfit > 0 ? "text-forest-deep" : "text-rose-600"
                    }`}
                  >
                    ₹{simulation.netProfit.toLocaleString("en-IN")}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Metric Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div className="bg-white rounded-2xl p-4 border border-premium-border shadow-sm">
              <span className="text-[11px] font-bold text-ink-soft uppercase tracking-wider block mb-1">
                Simulated Revenue
              </span>
              <span className="text-base font-bold text-forest-deep">
                ₹{simulation.revenue.toLocaleString("en-IN")}/mo
              </span>
            </div>

            <div className="bg-white rounded-2xl p-4 border border-premium-border shadow-sm">
              <span className="text-[11px] font-bold text-ink-soft uppercase tracking-wider block mb-1">
                Break-Even Sales
              </span>
              <span className="text-base font-bold text-forest-deep">
                ₹{simulation.breakEvenRevenue.toLocaleString("en-IN")}/mo
              </span>
            </div>

            <div className="bg-white rounded-2xl p-4 border border-premium-border shadow-sm col-span-2 sm:col-span-1">
              <span className="text-[11px] font-bold text-ink-soft uppercase tracking-wider block mb-1">
                Debt Safety Cushion
              </span>
              <span
                className={`text-base font-bold ${
                  simulation.dscr >= 1.5
                    ? "text-emerald-700"
                    : simulation.dscr >= 1.0
                    ? "text-amber-600"
                    : "text-rose-600"
                }`}
              >
                {simulation.dscr >= 1.5
                  ? "Strong Buffer"
                  : simulation.dscr >= 1.0
                  ? "Tight Cushion"
                  : "Under Water"}
              </span>
            </div>
          </div>
        </div>
>>>>>>> cleanup-final
      </div>
    </motion.div>
  );
}
