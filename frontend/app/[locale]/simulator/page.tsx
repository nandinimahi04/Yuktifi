"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "@/routing";
import { useStore } from "@/lib/store";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import { api, type RecommendResponse, type SimulateResponse } from "@/lib/api-client";
import { Loader2, TrendingUp, AlertTriangle, ArrowRight, Settings2, BarChart4, ArrowDown, ArrowUp, Activity } from "lucide-react";
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
      setError(t('error'));
      setLoading(false);
    } else {
      setLoading(false);
    }
  }, [state.analysisResult]);

  const runSimulation = async () => {
    setSimLoading(true);
    setError("");
    try {
      /*
        Removed `location: { district: "solapur", state: "maharashtra" }` and
        `capital: { available: state.marginCapital || 100000 }`.

        The district was hardcoded, so every simulation in the product was run
        against Solapur regardless of where the user was. A simulation is the
        page where a user checks what a demand shock would do to their business,
        and it was quietly answering a question about a different district. A
        shock applied to Solapur competition levels tells a Nagpur operator
        nothing true.

        The capital fallback had the same effect at a different magnitude: a user
        who had declared nothing was simulated as though they had ₹1,00,000,
        and the debt sizing that follows from it is arithmetic on that invented
        number.

        The session now has to supply both. If it cannot, the simulation is not
        run - an unavailable simulation is the honest answer, and the stress
        engine will abstain on a missing location rather than guess.
      */
      if (!state.locationId || !state.locationName) {
        setError(
          "No confirmed location for this session, so the simulation cannot be run. A stress test applied to the wrong district would not describe your business."
        );
        return;
      }
      if (!state.marginCapital || state.marginCapital <= 0) {
        setError(
          "Your capital has not been declared, so the financing side of this simulation would be computed from an invented number."
        );
        return;
      }

      // Re-trigger the authoritative /generate endpoint for the simulation.
      //
      // The location carries the district and the location_id the session
      // actually holds. It previously also carried a hardcoded
      // `state: "maharashtra"`: the store has no region field, so that value
      // was an invention that silently scoped the simulation to one state
      // whatever district the user had chosen. It is omitted rather than
      // guessed, so any state-level figure the engines cannot source is
      // reported unavailable instead of borrowed from Maharashtra.
      const res = await api.generateAnalysis({
        mode: "simulation", // architectural signal
        profile: { experience: state.experience || "not declared" },
        location: { district: state.locationName, location_id: state.locationId },
        capital: { available: state.marginCapital },
        business: { category: state.categoryName || "", idea: state.ideaDetails || "" },
        scenario: { ...simParams }, // Send multipliers if backend wants them
        language: locale
      });
      state.updateState({ simulationResult: res });
    } catch (err: unknown) {
      console.error("Simulation API failed:", err);
    } finally {
      setSimLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto mt-10">
        <div className="h-64 flex justify-center items-center">
          <Loader2 size={48} className="animate-spin text-warm-primary" />
        </div>
      </div>
    );
  }

  if (error || !state.analysisResult) {
    return <div className="text-red-500 p-4 font-bold bg-red-50 rounded-xl m-4 border border-red-200">{error}</div>;
  }
  
  const baseParams = state.analysisResult;
  const simResults = state.simulationResult;
  
  // Extract baseline metrics
  const baseRoi = baseParams.financials?.roi_pct || 0;
  const baseDscr = baseParams.financials?.dscr || 0;
  const simRoi = simResults ? (simResults.financials?.roi_pct || 0) : 0;
  const simDscr = simResults ? (simResults.financials?.dscr || 0) : 0;
  const survivesStress = simDscr >= 1.0;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="max-w-5xl mx-auto p-4 md:p-8 pb-20 font-sans"
    >
      <div className="flex flex-col sm:flex-row justify-between items-center sm:items-end mb-8 gap-4 border-b border-warm-border pb-6 mt-4">
        <div>
          <h1 className="text-3xl font-bold text-warm-text flex items-center">
            <Activity className="mr-3 text-warm-primary" size={32} />
            {t('title')}
          </h1>
          <p className="text-warm-muted mt-2 font-medium">{t('subtitle')} <strong className="text-warm-text">{baseParams.matched_business?.matched_subcategory || t('yourBusiness')}</strong></p>
        </div>
        <Button onClick={() => router.push('/report')} className="bg-warm-bg text-warm-primary border border-warm-primary hover:bg-warm-primary hover:text-warm-text transition-colors shadow-sm font-bold">
          {t('generateReport')} <ArrowRight size={16} className="ml-2" />
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls */}
        <Card className="lg:col-span-1 border-warm-border shadow-sm bg-warm-surface rounded-2xl overflow-hidden">
          <CardHeader className="bg-warm-bg/50 pb-4 border-b border-warm-border">
            <CardTitle className="text-sm font-bold text-warm-text flex items-center uppercase tracking-wider">
              <Settings2 size={16} className="mr-2 text-warm-primary" />
              {t('variables.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6 space-y-8">
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-bold text-warm-text">{t('variables.demand')}</label>
                <span className="text-xs font-bold text-warm-text bg-warm-primary px-2 py-1 rounded-md">{(simParams.demand_multiplier * 100).toFixed(0)}%</span>
              </div>
              <input 
                type="range" 
                min="0.5" max="1.5" step="0.1" 
                value={simParams.demand_multiplier}
                onChange={(e) => setSimParams({...simParams, demand_multiplier: parseFloat(e.target.value)})}
                className="w-full h-2 bg-warm-border rounded-lg appearance-none cursor-pointer accent-warm-primary"
              />
              <div className="flex justify-between text-xs font-semibold text-warm-muted mt-2">
                <span>{t('variables.demandLow')}</span>
                <span>{t('variables.demandHigh')}</span>
              </div>
            </div>
            
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-bold text-warm-text">{t('variables.costs')}</label>
                <span className={`text-xs font-bold text-warm-text px-2 py-1 rounded-md ${simParams.cost_multiplier > 1 ? 'bg-red-500' : 'bg-emerald-500'}`}>{(simParams.cost_multiplier * 100).toFixed(0)}%</span>
              </div>
              <input 
                type="range" 
                min="0.8" max="1.5" step="0.1" 
                value={simParams.cost_multiplier}
                onChange={(e) => setSimParams({...simParams, cost_multiplier: parseFloat(e.target.value)})}
                className="w-full h-2 bg-warm-border rounded-lg appearance-none cursor-pointer accent-red-500"
              />
              <div className="flex justify-between text-xs font-semibold text-warm-muted mt-2">
                <span>{t('variables.costsLow')}</span>
                <span>{t('variables.costsHigh')}</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-bold text-warm-text">{t('variables.price')}</label>
                <span className="text-xs font-bold text-warm-text bg-amber-500 px-2 py-1 rounded-md">{(simParams.price_multiplier * 100).toFixed(0)}%</span>
              </div>
              <input 
                type="range" 
                min="0.8" max="1.3" step="0.05" 
                value={simParams.price_multiplier}
                onChange={(e) => setSimParams({...simParams, price_multiplier: parseFloat(e.target.value)})}
                className="w-full h-2 bg-warm-border rounded-lg appearance-none cursor-pointer accent-amber-500"
              />
              <div className="flex justify-between text-xs font-semibold text-warm-muted mt-2">
                <span>{t('variables.priceLow')}</span>
                <span>{t('variables.priceHigh')}</span>
              </div>
            </div>

            <Button 
              className="w-full mt-4 bg-warm-primary text-warm-text hover:bg-orange-600 font-bold py-6 rounded-xl shadow-md transition-all text-base" 
              onClick={runSimulation}
              disabled={simLoading}
            >
              {simLoading ? <Loader2 className="animate-spin mr-2" size={20} /> : <BarChart4 className="mr-2" size={20} />}
              {t('variables.runTest')}
            </Button>
          </CardContent>
        </Card>

        {/* Results */}
        <Card className="lg:col-span-2 border-warm-border bg-warm-surface shadow-sm rounded-2xl overflow-hidden">
          <CardHeader className="bg-warm-bg/50 pb-4 border-b border-warm-border">
            <CardTitle className="text-sm font-bold text-warm-text flex items-center uppercase tracking-wider">
              <TrendingUp size={16} className="mr-2 text-warm-primary" />
              {t('results.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            {!simResults ? (
              <div className="h-64 flex flex-col items-center justify-center text-warm-muted border-2 border-dashed border-warm-border rounded-xl bg-warm-bg/50">
                <Settings2 size={48} className="mb-4 text-warm-border" />
                <p className="font-semibold">{t('results.placeholder')}</p>
              </div>
            ) : (
              <motion.div 
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="space-y-6"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* BEFORE Card */}
                  <div className="bg-warm-bg border border-warm-border rounded-xl p-6 shadow-sm">
                    <div className="text-xs font-bold text-warm-muted uppercase tracking-wider mb-4 border-b border-warm-border pb-2">{t('results.before')}</div>
                    <div className="space-y-6">
                      <div>
                        <div className="text-xs font-bold text-warm-muted uppercase tracking-wider mb-1">{t('results.roi')}</div>
                        <div className="text-3xl font-black text-warm-text">{baseRoi.toFixed(1)}%</div>
                      </div>
                      <div>
                        <div className="text-xs font-bold text-warm-muted uppercase tracking-wider mb-1">{t('results.dscr')}</div>
                        <div className="text-3xl font-black text-warm-text">{baseDscr.toFixed(2)}x</div>
                      </div>
                    </div>
                  </div>
                  
                  {/* AFTER Card */}
                  <div className={`border rounded-xl p-6 shadow-sm ${survivesStress ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                    <div className="text-xs font-bold text-warm-muted uppercase tracking-wider mb-4 border-b border-warm-border/50 pb-2 flex justify-between items-center">
                      {t('results.after')}
                      {survivesStress ? (
                        <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-[10px] font-black tracking-widest shadow-sm border border-emerald-200">{t('results.safe')}</span>
                      ) : (
                        <span className="bg-red-100 text-red-700 px-3 py-1 rounded-full text-[10px] font-black tracking-widest shadow-sm border border-red-200">{t('results.risk')}</span>
                      )}
                    </div>
                    <div className="space-y-6">
                      <div>
                        <div className="text-xs font-bold text-warm-muted uppercase tracking-wider mb-1">{t('results.roi')}</div>
                        <div className="flex items-center">
                        <div className={`text-3xl font-black ${simRoi >= baseRoi ? 'text-emerald-600' : 'text-red-600'}`}>
                            {simRoi.toFixed(1)}%
                          </div>
                          {simRoi >= baseRoi ? <ArrowUp size={20} className="text-emerald-500 ml-2" /> : <ArrowDown size={20} className="text-red-500 ml-2" />}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs font-bold text-warm-muted uppercase tracking-wider mb-1">{t('results.dscr')}</div>
                        <div className="flex items-center">
                          <div className={`text-3xl font-black ${simDscr >= baseDscr ? 'text-emerald-600' : 'text-red-600'}`}>
                            {simDscr.toFixed(2)}x
                          </div>
                          {simDscr >= baseDscr ? <ArrowUp size={20} className="text-emerald-500 ml-2" /> : <ArrowDown size={20} className="text-red-500 ml-2" />}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <YuktiFiInsight 
                  type={survivesStress ? 'positive' : 'warning'}
                  title={survivesStress ? t('results.viableTitle') : t('results.riskTitle')}
                  message={survivesStress
                    ? t('results.viableDesc', { dscr: simDscr.toFixed(2) })
                    : t('results.riskDesc', { dscr: simDscr.toFixed(2) })
                  }
                />
              </motion.div>
            )}
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}

