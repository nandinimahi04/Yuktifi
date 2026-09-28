"use client";

import React, { useState, useEffect } from "react";
import { useStore } from "@/lib/store";
import { api } from "@/lib/api-client";
import {
  Calculator,
  Save,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  TrendingUp,
  Wallet,
  CreditCard,
  CalendarDays,
  IndianRupee,
  Layers,
  Sparkles,
  Loader2,
  ChevronDown,
  ChevronUp
} from "lucide-react";

interface FinancialAssumptionsPanelProps {
  onRecalculated?: (newFinancials: any, newScores?: any) => void;
  defaultOpen?: boolean;
}


export default function FinancialAssumptionsPanel({
  onRecalculated,
  defaultOpen = false,
}: FinancialAssumptionsPanelProps) {
  const { sessionId: rawSessionId, categoryId, analysisResult, updateState } = useStore();
  const sessionId = rawSessionId || analysisResult?.session_id || "default_session";
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<any[]>([]);

  // Form states
  const [version, setVersion] = useState<number>(1);
  const [projectCost, setProjectCost] = useState<number>(750000);
  const [ownCapital, setOwnCapital] = useState<number>(150000);
  const [loanAmount, setLoanAmount] = useState<number>(600000);
  
  const [isDirectRevenueMode, setIsDirectRevenueMode] = useState<boolean>(false);
  const [monthlyRevenue, setMonthlyRevenue] = useState<number>(180000);
  const [sellingPrice, setSellingPrice] = useState<number>(20);
  const [unitsPerDay, setUnitsPerDay] = useState<number>(300);
  const [operatingDays, setOperatingDays] = useState<number>(30);
  
  const [variableCostPerUnit, setVariableCostPerUnit] = useState<number>(8);
  const [monthlyExpenses, setMonthlyExpenses] = useState<number>(35000);
  
  const [interestRate, setInterestRate] = useState<number>(9.0);
  const [loanTenureMonths, setLoanTenureMonths] = useState<number>(60);
  const [moratoriumMonths, setMoratoriumMonths] = useState<number>(0);
  const [taxRatePct, setTaxRatePct] = useState<number | undefined>(undefined);
  const [lastUpdatedIst, setLastUpdatedIst] = useState<string | null>(null);

  // Initial load from backend API
  useEffect(() => {
    if (!sessionId) return;
    
    const fetchAssumptions = async () => {
      setIsLoading(true);
      try {
        const res = await api.getFinancialAssumptions(sessionId);
        if (res && res.assumptions) {
          const a = res.assumptions;
          setVersion(a.version || 1);
          setProjectCost(a.project_cost || 0);
          setOwnCapital(a.own_capital || 0);
          setLoanAmount(a.loan_amount || 0);
          setIsDirectRevenueMode(Boolean(a.is_direct_revenue_mode));
          setMonthlyRevenue(a.monthly_revenue || 0);
          setSellingPrice(a.selling_price || 0);
          setUnitsPerDay(a.units_per_day || 0);
          setOperatingDays(a.operating_days || 30);
          setVariableCostPerUnit(a.variable_cost_per_unit || 0);
          setMonthlyExpenses(a.monthly_expenses || 0);
          setInterestRate(a.interest_rate_annual_pct || 9.0);
          setLoanTenureMonths(a.loan_tenure_months || 60);
          setMoratoriumMonths(a.moratorium_months || 0);
          setTaxRatePct(a.tax_rate_pct);
          setLastUpdatedIst(res.last_updated_ist || null);
          setWarnings(res.validation_warnings || []);
        }
      } catch (err: any) {
        console.warn("Could not fetch persisted assumptions, using session defaults:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAssumptions();
  }, [sessionId]);

  // Synchronize loan amount when project cost or own capital changes
  const handleProjectCostChange = (val: number) => {
    setProjectCost(val);
    setLoanAmount(Math.max(0, val - ownCapital));
  };

  const handleOwnCapitalChange = (val: number) => {
    setOwnCapital(val);
    setLoanAmount(Math.max(0, projectCost - val));
  };

  // Derived calculations for live real-time feedback
  const derivedMonthlyRevenue = isDirectRevenueMode
    ? monthlyRevenue
    : Math.round(sellingPrice * unitsPerDay * operatingDays);

  const effectiveUnitsPerMonth = isDirectRevenueMode
    ? (sellingPrice > 0 ? derivedMonthlyRevenue / sellingPrice : 1)
    : unitsPerDay * operatingDays;

  const estimatedCogs = Math.round(effectiveUnitsPerMonth * variableCostPerUnit);
  const estimatedGrossProfit = derivedMonthlyRevenue - estimatedCogs;
  const grossMarginPct = derivedMonthlyRevenue > 0 ? Math.round((estimatedGrossProfit / derivedMonthlyRevenue) * 1000) / 10 : 0;
  const contributionPerUnit = Math.round((sellingPrice - variableCostPerUnit) * 100) / 100;
  const isNegativeContribution = sellingPrice > 0 && variableCostPerUnit >= sellingPrice;
  const estimatedMonthlyEbitda = estimatedGrossProfit - monthlyExpenses;

  // Estimated Working Capital
  const annualCogsEst = estimatedCogs * 12;
  const annualRevEst = derivedMonthlyRevenue * 12;
  const invReqEst = Math.round((annualCogsEst / 365) * 10);
  const recReqEst = Math.round((annualRevEst / 365) * 7);
  const payReqEst = Math.round((annualCogsEst / 365) * 14);
  const netWcEst = Math.max(0, invReqEst + recReqEst - payReqEst);

  const handleAutoBalanceCogs = (targetCogsPct = 60) => {
    if (sellingPrice > 0) {
      const balancedVarCost = Math.round(sellingPrice * (targetCogsPct / 100) * 10) / 10;
      setVariableCostPerUnit(balancedVarCost);
    }
  };

  const handleSaveAndRecalculate = async () => {
    if (!sessionId) {
      setError("Session not found. Please refresh the page.");
      return;
    }

    if (ownCapital > projectCost) {
      setError(`Own Contribution (₹${ownCapital.toLocaleString("en-IN")}) cannot exceed Total Project Cost (₹${projectCost.toLocaleString("en-IN")}).`);
      return;
    }

    setIsSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const payload = {
        session_id: sessionId,
        category_id: categoryId || analysisResult?.business?.matched_category_id || analysisResult?.matched_business?.matched_category_id || "retail_kirana",
        assumptions: {
          project_cost: Number(projectCost),
          own_capital: Number(ownCapital),
          loan_amount: Number(loanAmount),
          is_direct_revenue_mode: isDirectRevenueMode,
          monthly_revenue: Number(derivedMonthlyRevenue),
          selling_price: Number(sellingPrice),
          units_per_day: Number(unitsPerDay),
          operating_days: Number(operatingDays),
          variable_cost_per_unit: Number(variableCostPerUnit),
          monthly_expenses: Number(monthlyExpenses),
          interest_rate_annual_pct: Number(interestRate),
          loan_tenure_months: Number(loanTenureMonths),
          moratorium_months: Number(moratoriumMonths),
          tax_rate_pct: taxRatePct ? Number(taxRatePct) : null,
          version: version,
        },
        changed_by: "user",
      };

      const res = await api.recalculateFinancials(payload);

      if (res && res.financials) {
        setVersion(res.assumptions_version);
        setLastUpdatedIst(res.last_updated_ist);
        setWarnings(res.validation_warnings || []);
        setSuccessMessage(`✓ Assumptions saved (v${res.assumptions_version}) & Financial Model recalculated successfully.`);

        // Update unified state in Zustand
        if (analysisResult) {
          useStore.setState({
            analysisResult: {
              ...analysisResult,
              financials: res.financials,
              scores: res.scores ? {
                ...analysisResult.scores,
                overall: res.scores.yukti_score,
                dimensions: res.scores,
                verdict: res.scores.verdict,
                score_available: res.scores.yukti_score !== null,
              } : analysisResult.scores,
            },
          });
        }

        if (onRecalculated) {
          onRecalculated(res.financials, res.scores);
        }

        // Auto clear success message after 5 seconds
        setTimeout(() => setSuccessMessage(null), 5000);

      }
    } catch (err: any) {
      console.error("Recalculation failed:", err);
      if (err.status === 409) {
        setError("Concurrent modification detected. Another update was made. Please refresh to load latest values.");
      } else {
        setError(err.message || "Failed to recalculate financial model. Please check inputs.");
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="bg-white border-2 border-emerald-600/30 rounded-2xl shadow-md overflow-hidden mb-8 transition-all">
      {/* Top Banner & Quick Toggle */}
      <div className="bg-gradient-to-r from-emerald-900 via-forest-deep to-emerald-950 px-6 py-4 text-white flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-400/30 flex items-center justify-center text-emerald-400">
            <Calculator size={22} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-lg text-white">Financial Assumptions & Canonical Recalculator</h3>
              <span className="bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 text-xs px-2.5 py-0.5 rounded-full font-mono font-bold">
                v{version}
              </span>
            </div>
            <p className="text-xs text-emerald-200/80 mt-0.5">
              Deterministic Python financial engine. Modifying inputs here updates all dependent calculations across the platform.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {lastUpdatedIst && (
            <span className="text-xs text-emerald-300/80 hidden md:inline-block font-mono">
              Last saved: {lastUpdatedIst}
            </span>
          )}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl transition-all shadow-sm active:scale-95"
          >
            {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            {isOpen ? "Collapse Assumptions" : "Edit Assumptions & Recalculate"}
          </button>
        </div>
      </div>

      {/* Notifications & Warning Alerts */}
      {successMessage && (
        <div className="bg-emerald-50 border-b border-emerald-200 px-6 py-3 text-emerald-800 text-sm font-semibold flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 size={18} className="text-emerald-600 shrink-0" />
          <span>{successMessage}</span>
          {lastUpdatedIst && <span className="text-xs text-emerald-600 font-mono ml-auto">{lastUpdatedIst}</span>}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-3 text-red-800 text-sm font-semibold flex items-center gap-2 animate-in fade-in">
          <AlertTriangle size={18} className="text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="bg-amber-50 border-b border-amber-200 px-6 py-3 space-y-1.5 text-xs text-amber-900 font-medium">
          {warnings.map((w, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <AlertTriangle size={14} className="text-amber-600 mt-0.5 shrink-0" />
              <span>
                <strong>{w.field.replace(/_/g, " ")}:</strong> {w.message}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Editable Body */}
      {isOpen && (
        <div className="p-6 md:p-8 bg-warm-bg/20 space-y-8 animate-in fade-in duration-300">
          {isLoading ? (
            <div className="flex items-center justify-center py-12 gap-3 text-forest-deep">
              <Loader2 size={24} className="animate-spin text-emerald-600" />
              <span className="font-semibold text-sm">Loading verified financial assumptions...</span>
            </div>
          ) : (
            <>
              {/* 1. Capital & Financing Stack */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Wallet size={18} className="text-emerald-600" />
                  <h4 className="text-sm font-bold uppercase tracking-wider text-forest-deep">
                    1. Capital & Financing Stack
                  </h4>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Total Project Cost */}
                  <div className="bg-white p-4 rounded-xl border border-premium-border shadow-sm">
                    <label className="block text-xs font-bold text-ink-soft uppercase mb-1">
                      Total Project Cost (₹)
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        min="0"
                        step="5000"
                        value={projectCost}
                        onChange={(e) => handleProjectCostChange(Number(e.target.value))}
                        className="w-full font-display font-bold text-lg text-ink border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                      />
                    </div>
                    <p className="text-[11px] text-ink-soft mt-1">Total CapEx + initial working capital</p>
                  </div>

                  {/* Own Capital Contribution */}
                  <div className="bg-white p-4 rounded-xl border border-premium-border shadow-sm">
                    <label className="block text-xs font-bold text-ink-soft uppercase mb-1">
                      Your Margin Contribution (₹)
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="5000"
                      value={ownCapital}
                      onChange={(e) => handleOwnCapitalChange(Number(e.target.value))}
                      className="w-full font-display font-bold text-lg text-emerald-700 border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                    />
                    <p className="text-[11px] text-ink-soft mt-1">
                      {projectCost > 0
                        ? `${Math.round((ownCapital / projectCost) * 100)}% promoter equity share`
                        : "Promoter's cash"}
                    </p>
                  </div>

                  {/* Loan Requirement (Derived or editable) */}
                  <div className="bg-white p-4 rounded-xl border border-premium-border shadow-sm">
                    <label className="block text-xs font-bold text-ink-soft uppercase mb-1">
                      Loan Amount / Debt (₹)
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="5000"
                      value={loanAmount}
                      onChange={(e) => setLoanAmount(Number(e.target.value))}
                      className="w-full font-display font-bold text-lg text-blue-700 border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                    />
                    <p className="text-[11px] text-blue-600 font-medium mt-1">
                      {projectCost - ownCapital === loanAmount
                        ? "✓ Balanced: Project Cost − Own Capital"
                        : `Gap: ₹${(projectCost - ownCapital - loanAmount).toLocaleString("en-IN")}`}
                    </p>
                  </div>
                </div>
              </div>

              {/* 2. Revenue & Unit Economics */}
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
                  <div className="flex items-center gap-2">
                    <TrendingUp size={18} className="text-emerald-600" />
                    <h4 className="text-sm font-bold uppercase tracking-wider text-forest-deep">
                      2. Revenue Model & Unit Economics
                    </h4>
                  </div>
                  {/* Revenue Mode Toggle */}
                  <div className="flex items-center gap-3 bg-white px-3 py-1.5 rounded-xl border border-premium-border text-xs">
                    <span className={`font-semibold ${!isDirectRevenueMode ? "text-emerald-700" : "text-ink-soft"}`}>
                      Price × Volume Mode
                    </span>
                    <button
                      type="button"
                      onClick={() => setIsDirectRevenueMode(!isDirectRevenueMode)}
                      className={`w-10 h-5 rounded-full transition-colors relative ${
                        isDirectRevenueMode ? "bg-emerald-600" : "bg-gray-300"
                      }`}
                    >
                      <div
                        className={`w-4 h-4 rounded-full bg-white transition-transform absolute top-0.5 ${
                          isDirectRevenueMode ? "left-5" : "left-0.5"
                        }`}
                      />
                    </button>
                    <span className={`font-semibold ${isDirectRevenueMode ? "text-emerald-700" : "text-ink-soft"}`}>
                      Direct Revenue Override
                    </span>
                  </div>
                </div>

                {!isDirectRevenueMode ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Selling Price */}
                    <div className="bg-white p-4 rounded-xl border border-premium-border shadow-sm">
                      <label className="block text-xs font-bold text-ink-soft uppercase mb-1">
                        Selling Price / Unit (₹)
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="0.5"
                        value={sellingPrice}
                        onChange={(e) => setSellingPrice(Number(e.target.value))}
                        className="w-full font-display font-bold text-lg text-ink border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                      />
                      <p className="text-[11px] text-ink-soft mt-1">Per plate, unit, or service bill</p>
                    </div>

                    {/* Units / Day */}
                    <div className="bg-white p-4 rounded-xl border border-premium-border shadow-sm">
                      <label className="block text-xs font-bold text-ink-soft uppercase mb-1">
                        Units / Customers / Day
                      </label>
                      <input
                        type="number"
                        min="1"
                        step="5"
                        value={unitsPerDay}
                        onChange={(e) => setUnitsPerDay(Number(e.target.value))}
                        className="w-full font-display font-bold text-lg text-ink border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                      />
                      <p className="text-[11px] text-ink-soft mt-1">Daily expected footfall/sales</p>
                    </div>

                    {/* Operating Days / Month */}
                    <div className="bg-white p-4 rounded-xl border border-premium-border shadow-sm">
                      <label className="block text-xs font-bold text-ink-soft uppercase mb-1">
                        Operating Days / Month
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="31"
                        value={operatingDays}
                        onChange={(e) => setOperatingDays(Math.max(1, Math.min(31, Number(e.target.value))))}
                        className="w-full font-display font-bold text-lg text-ink border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                      />
                      <p className="text-[11px] text-ink-soft mt-1">Working days (typically 26–30)</p>
                    </div>

                    {/* Derived Monthly Revenue */}
                    <div className="bg-emerald-50/60 p-4 rounded-xl border border-emerald-200 shadow-sm flex flex-col justify-between">
                      <div>
                        <span className="block text-xs font-bold text-emerald-800 uppercase mb-1">
                          Calculated Monthly Revenue
                        </span>
                        <div className="text-2xl font-black font-display text-emerald-700">
                          ₹{derivedMonthlyRevenue.toLocaleString("en-IN")}
                        </div>
                      </div>
                      <p className="text-[11px] text-emerald-700/80 font-medium">
                        {sellingPrice} × {unitsPerDay} × {operatingDays} days
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-white p-4 rounded-xl border-2 border-emerald-500 shadow-sm">
                      <label className="block text-xs font-bold text-emerald-800 uppercase mb-1">
                        Direct Monthly Revenue Override (₹)
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="1000"
                        value={monthlyRevenue}
                        onChange={(e) => setMonthlyRevenue(Number(e.target.value))}
                        className="w-full font-display font-bold text-2xl text-emerald-800 border border-emerald-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                      />
                      <p className="text-xs text-ink-soft mt-1">Manual top-level revenue target</p>
                    </div>
                    <div className="bg-white p-4 rounded-xl border border-premium-border shadow-sm flex items-center">
                      <p className="text-xs text-ink-soft leading-relaxed">
                        In <strong>Direct Override Mode</strong>, the model calculates fixed break-even in rupees. Unit metrics (volume, price) remain informational.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* 3. Cost Breakdown & Loan Parameters */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <CreditCard size={18} className="text-emerald-600" />
                  <h4 className="text-sm font-bold uppercase tracking-wider text-forest-deep">
                    3. Operating Costs & Borrowing Terms
                  </h4>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Variable Cost / Unit */}
                  <div className="bg-white p-4 rounded-xl border border-premium-border shadow-sm">
                    <label className="block text-xs font-bold text-ink-soft uppercase mb-1">
                      Variable Cost / Unit (₹)
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="0.5"
                      value={variableCostPerUnit}
                      onChange={(e) => setVariableCostPerUnit(Number(e.target.value))}
                      className="w-full font-display font-bold text-lg text-ink border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                    />
                    <p className={`text-[11px] font-medium mt-1 ${contributionPerUnit > 0 ? "text-emerald-600" : "text-red-500 font-bold"}`}>
                      Contribution: ₹{contributionPerUnit}/unit
                    </p>
                  </div>

                  {/* Fixed Monthly Expenses */}
                  <div className="bg-white p-4 rounded-xl border border-premium-border shadow-sm">
                    <label className="block text-xs font-bold text-ink-soft uppercase mb-1">
                      Fixed Expenses / Month (₹)
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="500"
                      value={monthlyExpenses}
                      onChange={(e) => setMonthlyExpenses(Number(e.target.value))}
                      className="w-full font-display font-bold text-lg text-red-600 border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                    />
                    <p className="text-[11px] text-ink-soft mt-1">Rent, helper salary, power, basic opex</p>
                  </div>

                  {/* Interest Rate */}
                  <div className="bg-white p-4 rounded-xl border border-premium-border shadow-sm">
                    <label className="block text-xs font-bold text-ink-soft uppercase mb-1">
                      Interest Rate (% p.a.)
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.25"
                      value={interestRate}
                      onChange={(e) => setInterestRate(Number(e.target.value))}
                      className="w-full font-display font-bold text-lg text-ink border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                    />
                    <p className="text-[11px] text-ink-soft mt-1">Reducing balance annual rate</p>
                  </div>

                  {/* Loan Tenure */}
                  <div className="bg-white p-4 rounded-xl border border-premium-border shadow-sm">
                    <label className="block text-xs font-bold text-ink-soft uppercase mb-1">
                      Loan Tenure (Months)
                    </label>
                    <input
                      type="number"
                      min="6"
                      max="360"
                      step="6"
                      value={loanTenureMonths}
                      onChange={(e) => setLoanTenureMonths(Number(e.target.value))}
                      className="w-full font-display font-bold text-lg text-ink border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                    />
                    <p className="text-[11px] text-ink-soft mt-1">{Math.round(loanTenureMonths / 12)} years repayment term</p>
                  </div>
                </div>

                {/* Negative Contribution Alert */}
                {isNegativeContribution && (
                  <div className="bg-red-50 border-2 border-red-300 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-red-900 mt-4 animate-in fade-in">
                    <div className="flex items-start gap-3">
                      <AlertTriangle size={20} className="text-red-600 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-bold text-sm">Negative Contribution Margin Warning</p>
                        <p className="text-xs text-red-700 mt-0.5">
                          Variable cost (₹{variableCostPerUnit}/unit) is greater than Selling price (₹{sellingPrice}/unit). Each unit loses ₹{Math.abs(contributionPerUnit)}, causing negative Gross Profit, negative Net Profit, and negative Return on Project.
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleAutoBalanceCogs(60)}
                      className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-lg shrink-0 shadow-sm transition-colors"
                    >
                      Auto-set COGS to 60% (₹{Math.round(sellingPrice * 0.6)})
                    </button>
                  </div>
                )}

                {/* Live Economic Metrics Preview */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                  <div>
                    <span className="text-[11px] font-bold text-ink-soft uppercase block">Projected Revenue</span>
                    <span className="text-base font-bold text-emerald-700">₹{derivedMonthlyRevenue.toLocaleString("en-IN")}/mo</span>
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-ink-soft uppercase block">Projected COGS</span>
                    <span className={`text-base font-bold ${isNegativeContribution ? "text-red-600" : "text-ink"}`}>
                      ₹{estimatedCogs.toLocaleString("en-IN")}/mo ({derivedMonthlyRevenue > 0 ? Math.round((estimatedCogs / derivedMonthlyRevenue) * 100) : 0}%)
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-ink-soft uppercase block">Gross Margin</span>
                    <span className={`text-base font-bold ${grossMarginPct >= 20 ? "text-emerald-700" : grossMarginPct > 0 ? "text-amber-600" : "text-red-600 font-black"}`}>
                      {grossMarginPct}%
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-ink-soft uppercase block">Estimated Net WC</span>
                    <span className="text-base font-bold text-blue-700">₹{netWcEst.toLocaleString("en-IN")}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-premium-border">
                <div className="flex items-center gap-2 text-xs text-ink-soft">
                  <Sparkles size={14} className="text-emerald-600" />
                  <span>Submitting triggers complete re-run of P&L, DSCR, Payback, Break-even & Forecasts.</span>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setIsOpen(false)}
                    disabled={isSaving}
                    className="px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-ink font-bold text-xs rounded-xl transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveAndRecalculate}
                    disabled={isSaving}
                    className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-bold text-sm rounded-xl transition-all shadow-md disabled:opacity-50"
                  >
                    {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                    {isSaving ? "Recalculating..." : "Save & Recalculate Model"}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
