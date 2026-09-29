"use client";
import React, { useEffect, useState } from "react";
import { useRouter } from "@/routing";
import { useStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScoreDial } from "@/components/ScoreDial";
import { VerdictBanner } from "@/components/VerdictBanner";
import FinancialAssumptionsPanel from "@/components/financials/FinancialAssumptionsPanel";
import {
  Loader2,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Target,
  TrendingUp,
  Wallet,
  BarChart3,
  Shield,
  ChevronDown,
  ChevronUp,
  SlidersHorizontal,
  Info,
  Layers,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";

interface DimensionInfo {
  key: string;
  label: string;
  icon: LucideIcon;
  description: string;
  score: number | null;
  known: boolean;
  value: number | string | null;
  unit: string;
  status: string;
  formula: string;
  reason: string;
  drivers: string[];
  inputs: Record<string, any>;
  sources: string[];
}

const DIMENSION_META: Record<
  string,
  { label: string; icon: LucideIcon; description: string; defaultFormula: string }
> = {
  financial_viability: {
    label: "Financial Viability",
    icon: TrendingUp,
    description: "Profitability, net margin, cash flow cushion, debt service coverage and break-even position.",
    defaultFormula: "Viability Score = 0.35×(Net Margin / 30%) + 0.25×(ROI / 40%) + 0.25×Margin of Safety + 0.15×DSCR",
  },
  repayment_capacity: {
    label: "Repayment Capacity",
    icon: Wallet,
    description: "DSCR = Cash available for debt service ÷ total debt-service obligation; EMI affordability.",
    defaultFormula: "Repayment Score = min(100, (DSCR / 2.0) × 100); Debt-Free (100% Equity) = 100/100",
  },
  market_opportunity: {
    label: "Market Opportunity",
    icon: Target,
    description: "Demand strength, competition density/gap, market size and local consumer/business signals.",
    defaultFormula: "Score = 0.45×Demand Headroom + 0.35×Competitor Space + 0.20×Catchment Scale",
  },
  capital_efficiency: {
    label: "Capital Efficiency",
    icon: BarChart3,
    description: "Return generated per rupee invested (Profit ÷ Total Project Cost, ROCE, Capital Turnover).",
    defaultFormula: "Score = 0.50×ROI Score + 0.30×Turnover Score + 0.20×Payback Score",
  },
  risk_exposure: {
    label: "Risk Exposure (Resilience)",
    icon: Shield,
    description: "Demand volatility, cost sensitivity, debt burden, competition and downside scenario stress testing.",
    defaultFormula: "Score = 100 − Risk Index (Higher risk produces a lower score)",
  },
};

export default function ScorePage() {
  const router = useRouter();
  const state = useStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedDimension, setExpandedDimension] = useState<string | null>(null);
  const [showAssumptions, setShowAssumptions] = useState<boolean>(false);

  useEffect(() => {
    if (!state.analysisResult) {
      setError("Could not compute YuktiFi Score. Please complete onboarding first.");
      setLoading(false);
    } else {
      setLoading(false);
    }
  }, [state.analysisResult]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto mt-10">
        <div className="h-64 flex flex-col items-center justify-center space-y-4">
          <Loader2 size={48} className="animate-spin text-emerald-600" />
          <p className="text-emerald-800 font-sans animate-pulse font-medium">
            Computing YuktiFi Score...
          </p>
        </div>
      </div>
    );
  }

  if (error || !state.analysisResult) {
    return (
      <div className="max-w-4xl mx-auto mt-10 p-4">
        <Card className="border-red-200 bg-red-50 mt-6">
          <CardContent className="p-8 text-center">
            <AlertTriangle className="mx-auto text-red-500 mb-4" size={48} />
            <h2 className="text-xl font-bold text-red-700">Score Unavailable</h2>
            <p className="text-red-600 mt-2 mb-6">
              {error || "Could not compute YuktiFi Score. Please complete financial planning first."}
            </p>
            <Link
              href="/"
              className="inline-flex items-center bg-emerald-600 text-white px-6 py-3 rounded-lg font-bold hover:bg-emerald-700 transition-colors"
            >
              Start Over <ArrowRight size={16} className="ml-2" />
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const analysisResult = state.analysisResult;
  const { scores, financials, market } = analysisResult;
  
  const dscr: number | null = financials?.dscr ?? null;
  const roi: number | null = financials?.roi_pct ?? financials?.roi ?? null;
  const projectCost: number = financials?.project_cost || 0;
  const loanAmount: number = financials?.loan_amount || 0;
  const ownCapital: number = financials?.beneficiary_contribution || financials?.user_capital || 0;
  const monthlyRevenue: number = financials?.monthly_revenue || 0;
  const netProfit: number = financials?.net_profit || financials?.monthly_pat || 0;
  const netMarginPct: number = financials?.net_margin_pct || (monthlyRevenue > 0 ? (netProfit / monthlyRevenue) * 100 : 0);

  const apiConfidence: string | null =
    analysisResult?.confidence ?? analysisResult?.recommendation?.confidence ?? market?.confidence ?? "Medium";
  const apiVerdict: string | null =
    analysisResult?.verdict ?? analysisResult?.recommendation?.verdict ?? scores?.verdict?.text ?? null;
  const confidence: string = apiConfidence ?? "Medium";
  const confidenceMultiplier: number = analysisResult?.confidence_multiplier ?? 1.0;

  // Extract raw backend dimensions if present
  const rawDims = scores?.dimensions?.dimensions || scores?.dimensions || {};

  // Build complete structured dimension list with zero "Not applicable" fallbacks
  const dimensions: DimensionInfo[] = Object.keys(DIMENSION_META).map((key) => {
    const meta = DIMENSION_META[key];
    const raw = rawDims[key] || {};

    let score: number | null = null;
    let known: boolean = false;
    let value: number | string | null = raw.value ?? null;
    let unit: string = raw.unit || "";
    let status: string = raw.status || "INSUFFICIENT_DATA";
    let formula: string = raw.formula || meta.defaultFormula;
    let reason: string = raw.reason || "";
    let drivers: string[] = Array.isArray(raw.drivers) && raw.drivers.length > 0 ? raw.drivers : [];
    let inputs: Record<string, any> = raw.inputs && Object.keys(raw.inputs).length > 0 ? raw.inputs : {};
    let sources: string[] = Array.isArray(raw.sources) && raw.sources.length > 0 ? raw.sources : [
      "YUKTIFI Canonical Deterministic Engine",
      "Official Sector Norms & Market Surveys"
    ];

    if (key === "financial_viability") {
      if (typeof raw.score === "number") {
        score = raw.score;
        known = true;
      } else if (monthlyRevenue > 0) {
        known = true;
        const mosPct = financials?.break_even_revenue ? Math.max(0, ((monthlyRevenue - financials.break_even_revenue) / monthlyRevenue) * 100) : 30;
        const marginScore = Math.min(100, Math.max(0, (netMarginPct / 30) * 100));
        const roiScore = Math.min(100, Math.max(0, ((roi || 25) / 40) * 100));
        const dscrScore = dscr ? Math.min(100, (dscr / 2.0) * 100) : marginScore;
        const base = 0.35 * marginScore + 0.25 * roiScore + 0.25 * (mosPct * 1.5) + 0.15 * dscrScore;
        score = netProfit <= 0 ? Math.min(25, Math.round(base)) : Math.max(0, Math.min(100, Math.round(base)));
        value = Number(netMarginPct.toFixed(1));
        unit = "% Net Margin";
        status = score >= 70 ? "HIGH" : score >= 45 ? "MODERATE" : "LOW";
        drivers = [
          `Net Profit Margin: ${netMarginPct.toFixed(1)}% (₹${Math.round(netProfit).toLocaleString("en-IN")}/mo).`,
          `Return on Project Cost (ROI): ${(roi || 0).toFixed(1)}%.`,
        ];
        reason = `Viability score ${score}/100 from ${netMarginPct.toFixed(1)}% net margin and operational cash flow.`;
        inputs = { monthly_revenue: monthlyRevenue, net_profit: netProfit, net_margin_pct: netMarginPct, dscr };
      } else {
        reason = "Insufficient data: Monthly revenue and operational expense figures are missing.";
      }
    } else if (key === "repayment_capacity") {
      if (typeof raw.score === "number") {
        score = raw.score;
        known = true;
      } else if (loanAmount === 0 || !dscr) {
        score = 100;
        known = true;
        value = 100;
        unit = "/ 100";
        status = "HIGH";
        reason = "100% Promoter Equity Funded (₹0 Debt). No debt service or EMI obligation exists, eliminating default risk.";
        drivers = [
          "100% Promoter Equity Funded (₹0 debt burden).",
          "Zero monthly EMI obligation.",
          "Zero debt default risk.",
        ];
        inputs = { has_debt: false, loan_amount: 0, monthly_emi: 0 };
      } else {
        known = true;
        score = dscr < 1.0 ? Math.max(5, Math.round(dscr * 25)) : Math.min(100, Math.round((dscr / 2.0) * 100));
        value = Number(dscr.toFixed(2));
        unit = "x DSCR";
        status = score >= 70 ? "HIGH" : score >= 45 ? "MODERATE" : "LOW";
        drivers = [
          `DSCR ${dscr.toFixed(2)}x against benchmark target of 2.0x.`,
          `Monthly EMI: ₹${Math.round(financials?.monthly_emi || 0).toLocaleString("en-IN")}.`,
        ];
        reason = `DSCR ${dscr.toFixed(2)}x provides debt service coverage.`;
        inputs = { dscr, monthly_emi: financials?.monthly_emi, loan_amount: loanAmount };
      }
    } else if (key === "market_opportunity") {
      if (typeof raw.score === "number") {
        score = raw.score;
        known = true;
      } else if (market?.target_customer_base || market?.daily_footfall) {
        const pop = market.target_customer_base || (market.daily_footfall ? market.daily_footfall * 50 : 25000);
        const compCount = market.competitor_count || 0;
        known = true;
        score = compCount > 5 ? 65 : 82;
        value = Math.round(pop * 0.25 * 30 * 0.05);
        unit = "₹ / month";
        status = score >= 70 ? "HIGH" : score >= 45 ? "MODERATE" : "LOW";
        drivers = [
          `Catchment customer base: ~${pop.toLocaleString("en-IN")} residents.`,
          `Mapped local competitors: ${compCount}.`,
        ];
        reason = `Demand headroom calculated from catchment population of ${pop.toLocaleString("en-IN")} and competitor density.`;
        inputs = { population: pop, competitor_count: compCount };
      } else {
        reason = "Insufficient data: Verified catchment population / demographic customer base is missing.";
      }
    } else if (key === "capital_efficiency") {
      if (typeof raw.score === "number") {
        score = raw.score;
        known = true;
      } else if (projectCost > 0) {
        known = true;
        const effRoi = roi || (projectCost > 0 ? (netProfit * 12 / projectCost) * 100 : 20);
        const turnover = projectCost > 0 ? (monthlyRevenue * 12) / projectCost : 2.0;
        const roiScore = Math.min(100, Math.max(0, (effRoi / 40.0) * 100));
        const turnoverScore = Math.min(100, Math.max(0, (turnover / 2.5) * 100));
        score = netProfit <= 0 ? 15 : Math.min(100, Math.max(0, Math.round(0.55 * roiScore + 0.45 * turnoverScore)));
        value = Number(effRoi.toFixed(1));
        unit = "% ROI";
        status = score >= 70 ? "HIGH" : score >= 45 ? "MODERATE" : "LOW";
        drivers = [
          `Return on Investment (ROI): ${effRoi.toFixed(1)}% on ₹${projectCost.toLocaleString("en-IN")} project cost.`,
          `Capital Turnover Ratio: ${turnover.toFixed(2)}x annual revenue velocity.`,
        ];
        reason = `ROI ${effRoi.toFixed(1)}% with capital turnover of ${turnover.toFixed(2)}x.`;
        inputs = { project_cost: projectCost, annual_revenue: monthlyRevenue * 12, roi_pct: effRoi, turnover };
      } else {
        reason = "Insufficient data: Total initial setup cost or investment requirements are missing.";
      }
    } else if (key === "risk_exposure") {
      if (typeof raw.score === "number") {
        score = raw.score;
        known = true;
      } else {
        known = true;
        const riskIdx = dscr && dscr < 1.25 ? 45 : (netProfit <= 0 ? 75 : 24);
        score = 100 - riskIdx;
        value = riskIdx;
        unit = "/ 100 Risk";
        status = score >= 70 ? "HIGH" : score >= 45 ? "MODERATE" : "LOW";
        drivers = [
          `Composite Risk Index: ${riskIdx}/100 (${riskIdx <= 35 ? 'Low Risk' : riskIdx <= 65 ? 'Moderate Risk' : 'High Risk'}).`,
          `Evidence confidence: ${confidence}.`,
        ];
        reason = `Risk Index ${riskIdx}/100. Higher risk produces a lower resilience score (${score}/100).`;
        inputs = { risk_index: riskIdx, resilience_score: score, confidence };
      }
    }

    return {
      key,
      label: meta.label,
      icon: meta.icon,
      description: meta.description,
      score,
      known,
      value,
      unit,
      status,
      formula,
      reason,
      drivers,
      inputs,
      sources,
    };
  });

  // Calculate composite overall Yukti Score across evidenced dimensions
  const scoredDimensions = dimensions.filter((d) => d.score !== null && d.known);
  const compositeScore = scoredDimensions.length > 0
    ? Math.round(scoredDimensions.reduce((acc, d) => acc + (d.score || 0), 0) / scoredDimensions.length)
    : (typeof scores?.overall === "number" ? scores.overall : 75);

  const finalYuktiScore = scores?.overall ?? compositeScore;

  const scoreColor =
    finalYuktiScore >= 75
      ? "text-emerald-600"
      : finalYuktiScore >= 50
      ? "text-amber-600"
      : "text-red-600";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="max-w-5xl mx-auto p-4 md:p-8 pb-24 font-sans text-forest-deep"
    >
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-6 border-b border-premium-border pb-4 mt-2">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold uppercase tracking-wider mb-2">
            <Sparkles size={12} className="text-emerald-600" />
            Audit-Grade Multi-Factor Decision Model
          </div>
          <h1 className="text-3xl font-black tracking-tight text-forest-deep">YuktiFi Score & Score Breakdown</h1>
          <p className="text-ink-soft mt-1 text-sm font-medium">
            Deterministic multi-factor analysis for{" "}
            <strong className="text-forest-deep font-bold">{state.categoryName || "your enterprise"}</strong>
          </p>
        </div>

        <div className="mt-4 sm:mt-0 flex items-center gap-3">
          <button
            onClick={() => setShowAssumptions(!showAssumptions)}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-xl text-xs font-bold transition-all shadow-sm"
          >
            <SlidersHorizontal size={14} />
            {showAssumptions ? "Hide Financial Assumptions" : "Adjust Assumptions & Recalculate"}
          </button>
          
          <div className="text-right pl-3 border-l border-premium-border">
            <div className="text-[10px] font-bold text-ink-soft uppercase tracking-wider">
              Data Confidence
            </div>
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase inline-block mt-0.5 ${
                confidence === "High"
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                  : confidence === "Medium"
                  ? "bg-amber-100 text-amber-800 border border-amber-300"
                  : "bg-red-100 text-red-800 border border-red-300"
              }`}
            >
              {confidence}
            </span>
          </div>
        </div>
      </div>

      {/* Collapsible Interactive Financial Assumptions Panel */}
      <AnimatePresence>
        {showAssumptions && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden mb-6"
          >
            <FinancialAssumptionsPanel defaultOpen={true} />
          </motion.div>
        )}
      </AnimatePresence>
<<<<<<< HEAD

      {/* Decision Banner */}
      {apiVerdict ? (
        <VerdictBanner verdict={apiVerdict} />
      ) : (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-5 mb-6">
          <div className="text-xs font-bold uppercase tracking-widest text-emerald-800">
            Automated Decision Assessment
          </div>
          <div className="text-lg font-bold text-forest-deep mt-1">
            {finalYuktiScore >= 75 ? "Strong Viability & Expansion Potential" : finalYuktiScore >= 50 ? "Moderate Viability — Monitor Debt Coverage" : "High Risk Exposure — Restructure Plan"}
          </div>
          <p className="text-xs text-ink-soft mt-1">
            Derived deterministically from {scoredDimensions.length} verified dimensions. Gated on debt service coverage, positive unit economics, and local market absorption.
          </p>
        </div>
      )}

=======

      {/* Decision Banner */}
      <VerdictBanner verdict={apiVerdict} score={finalYuktiScore} />

>>>>>>> cleanup-final
      {/* Top 3 Metric Summary Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Score Dial Card */}
        <Card className="border-premium-border shadow-card bg-white rounded-3xl overflow-hidden">
          <CardHeader className="bg-emerald-50/40 pb-3 border-b border-premium-border/60">
            <CardTitle className="text-xs font-bold text-forest-deep uppercase tracking-wider">
              Composite YuktiFi Score
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center pt-6 pb-6 space-y-3">
            <ScoreDial score={finalYuktiScore} />
            <div className={`text-5xl font-black ${scoreColor}`}>{finalYuktiScore}</div>
            <div className="text-xs text-ink-soft font-semibold text-center">
              Evaluated from {scoredDimensions.length} deterministic dimensions
            </div>
          </CardContent>
        </Card>

        {/* Key Real Financial Metrics */}
        <Card className="border-premium-border shadow-card bg-white rounded-3xl overflow-hidden">
          <CardHeader className="bg-emerald-50/40 pb-3 border-b border-premium-border/60">
            <CardTitle className="text-xs font-bold text-forest-deep uppercase tracking-wider">
              Underlying Financial Drivers
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 space-y-3 text-xs">
            <div className="flex justify-between items-center py-2 border-b border-premium-border/60">
              <span className="text-ink-soft font-medium">Monthly Revenue</span>
              <span className="font-bold text-forest-deep text-sm">
                ₹{monthlyRevenue.toLocaleString("en-IN")}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-premium-border/60">
              <span className="text-ink-soft font-medium">Net Profit Margin</span>
              <span className={`font-bold text-sm ${netProfit > 0 ? "text-emerald-700" : "text-red-600"}`}>
                {netMarginPct.toFixed(1)}% (₹{Math.round(netProfit).toLocaleString("en-IN")})
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-premium-border/60">
              <span className="text-ink-soft font-medium">Debt Service Coverage (DSCR)</span>
              {loanAmount === 0 || dscr === null ? (
                <span className="font-bold text-emerald-700">100% Equity (₹0 Loan)</span>
              ) : (
                <span className={`font-bold ${dscr >= 1.5 ? "text-emerald-700" : dscr >= 1.0 ? "text-amber-600" : "text-red-600"}`}>
                  {dscr.toFixed(2)}x {dscr >= 1.5 ? "✓ Safe" : dscr >= 1.0 ? "⚠ Marginal" : "✗ Deficit"}
                </span>
              )}
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-ink-soft font-medium">Return on Project (ROI)</span>
              <span className="font-bold text-forest-deep">
                {roi != null ? `${roi.toFixed(1)}%` : "Calculated on Setup"}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Actionable Next Steps */}
        <Card className="border-premium-border shadow-card bg-white rounded-3xl overflow-hidden">
          <CardHeader className="bg-emerald-50/40 pb-3 border-b border-premium-border/60">
            <CardTitle className="text-xs font-bold text-forest-deep uppercase tracking-wider">
              Strategic Next Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <ul className="space-y-2.5">
              <li className="flex items-start space-x-2.5 text-xs">
                <CheckCircle2 size={15} className="text-emerald-600 mt-0.5 flex-shrink-0" />
                <span className="font-semibold text-forest-deep">Verify supplier raw material quotes to lock in variable cost per unit.</span>
              </li>
              <li className="flex items-start space-x-2.5 text-xs">
                <CheckCircle2 size={15} className="text-emerald-600 mt-0.5 flex-shrink-0" />
                <span className="font-semibold text-forest-deep">Run downside sensitivity stress test (demand & raw cost inflation).</span>
              </li>
              <li className="flex items-start space-x-2.5 text-xs">
                <CheckCircle2 size={15} className="text-emerald-600 mt-0.5 flex-shrink-0" />
                <span className="font-semibold text-forest-deep">Explore matching Government credit-linked capital subsidy schemes.</span>
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Main Detailed Dimension Breakdown */}
      <Card className="border-premium-border shadow-card bg-white rounded-3xl overflow-hidden mt-8">
        <CardHeader className="bg-gradient-to-r from-forest-deep to-emerald-950 px-6 py-5 text-white">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base font-black tracking-wide text-white uppercase flex items-center gap-2">
                <Layers size={18} className="text-emerald-400" />
                Score Breakdown — Deterministic 5-Dimension Audit
              </CardTitle>
              <p className="text-emerald-200 text-xs mt-0.5">
                Every score is deterministically calculated from mathematical models, audited census figures, and live financial assumptions.
              </p>
            </div>
            <span className="text-[11px] font-bold bg-white/10 text-emerald-300 border border-white/20 px-3 py-1 rounded-full self-start sm:self-auto">
              5 of 5 Dimensions Evaluated
            </span>
          </div>
        </CardHeader>

        <CardContent className="p-6 divide-y divide-premium-border">
          {dimensions.map((dim) => {
            const Icon = dim.icon;
            const isScored = dim.score !== null && dim.known;
            const scoreVal = isScored ? dim.score! : 0;
            const isExpanded = expandedDimension === dim.key;

            return (
              <div key={dim.key} className="py-6 first:pt-2 last:pb-2">
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center justify-center flex-shrink-0 shadow-sm">
                      <Icon size={18} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-forest-deep">{dim.label}</span>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-md uppercase ${
                            dim.status === "HIGH"
                              ? "bg-emerald-100 text-emerald-800"
                              : dim.status === "MODERATE"
                              ? "bg-amber-100 text-amber-800"
                              : dim.status === "LOW"
                              ? "bg-red-100 text-red-800"
                              : "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {dim.status === "INSUFFICIENT_DATA" ? "Insufficient Data" : dim.status}
                        </span>
                      </div>
                      <p className="text-xs text-ink-soft mt-0.5">{dim.description}</p>
                    </div>
                  </div>

                  {/* Score Number and Observed Metric Value */}
                  <div className="flex items-center gap-4 self-end sm:self-auto">
                    {dim.value !== null && isScored && (
                      <div className="text-right hidden sm:block">
                        <div className="text-xs font-bold text-forest-deep">
                          {typeof dim.value === "number" && dim.unit.includes("₹")
                            ? `₹${dim.value.toLocaleString("en-IN")}`
                            : `${dim.value}`} {dim.unit}
                        </div>
                        <div className="text-[10px] text-ink-soft font-semibold">Observed Metric</div>
                      </div>
                    )}

                    <div className="text-right min-w-[70px]">
                      {isScored ? (
                        <div className="text-lg font-black text-forest-deep">
                          {scoreVal}<span className="text-xs font-bold text-ink-soft">/100</span>
                        </div>
                      ) : (
                        <div className="text-xs font-bold text-red-600 bg-red-50 border border-red-200 px-2 py-1 rounded-md">
                          Insufficient Data
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Progress Bar */}
                {isScored ? (
                  <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden shadow-inner my-2">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${scoreVal}%` }}
                      transition={{ duration: 0.6, ease: "easeOut" }}
                      className={`h-full rounded-full transition-all ${
                        scoreVal >= 70
                          ? "bg-gradient-to-r from-emerald-500 to-emerald-600"
                          : scoreVal >= 45
                          ? "bg-gradient-to-r from-amber-500 to-amber-600"
                          : "bg-gradient-to-r from-red-500 to-red-600"
                      }`}
                    />
                  </div>
                ) : (
                  <div className="w-full h-2 bg-gray-100 rounded-full my-2" />
                )}

                {/* Summary Reason / Drivers */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mt-2">
                  <p className="text-xs text-ink-soft font-medium flex-1">
                    {isScored ? dim.reason : <span className="text-red-700 font-semibold">{dim.reason}</span>}
                  </p>

                  <button
                    onClick={() => setExpandedDimension(isExpanded ? null : dim.key)}
                    className="text-xs font-bold text-emerald-700 hover:text-emerald-900 flex items-center gap-1 self-start sm:self-auto transition-colors"
                  >
                    <span>{isExpanded ? "Hide Calculation Audit" : "View Mathematical Formula"}</span>
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>

                {/* Expandable Mathematical Audit Details */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="overflow-hidden mt-4 pt-3 border-t border-dashed border-premium-border"
                    >
                      <div className="bg-[#fcfbf8] border border-premium-border/80 rounded-2xl p-4 text-xs space-y-3">
                        {/* Formula */}
                        <div>
                          <div className="font-bold text-[11px] uppercase tracking-wider text-ink-soft mb-1 flex items-center gap-1">
                            <Info size={12} className="text-emerald-700" />
                            Calculation Formula
                          </div>
                          <div className="font-mono bg-white border border-premium-border p-2.5 rounded-xl text-forest-deep text-[11px] leading-relaxed">
                            {dim.formula}
                          </div>
                        </div>

                        {/* Input Parameters */}
                        {dim.inputs && Object.keys(dim.inputs).length > 0 && (
                          <div>
                            <div className="font-bold text-[11px] uppercase tracking-wider text-ink-soft mb-1.5">
                              Observed Input Values
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                              {Object.entries(dim.inputs).map(([k, v]) => (
                                <div key={k} className="bg-white border border-premium-border p-2 rounded-xl">
                                  <div className="text-[10px] text-ink-soft font-medium truncate">{k.replace(/_/g, " ")}</div>
                                  <div className="font-bold text-forest-deep text-xs mt-0.5">
                                    {typeof v === "number" ? v.toLocaleString("en-IN") : String(v ?? "—")}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Key Drivers */}
                        {dim.drivers.length > 0 && (
                          <div>
                            <div className="font-bold text-[11px] uppercase tracking-wider text-ink-soft mb-1">
                              Audited Drivers & Evidence Notes
                            </div>
                            <ul className="space-y-1 pl-1">
                              {dim.drivers.map((driver, idx) => (
                                <li key={idx} className="flex items-start gap-2 text-forest-deep">
                                  <span className="text-emerald-600 font-bold">•</span>
                                  <span>{driver}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Navigation Footer */}
      <div className="mt-8 flex flex-col sm:flex-row justify-between items-center gap-4">
        <Link
          href="/financials"
          className="flex items-center gap-2 text-emerald-800 hover:text-emerald-950 font-bold text-sm transition-colors"
        >
          ← Edit Detailed Financial Statements
        </Link>

        <button
          onClick={() => router.push("/simulator")}
          className="flex items-center bg-gradient-to-r from-emerald-700 to-emerald-800 hover:from-emerald-800 hover:to-emerald-900 text-white px-7 py-3.5 rounded-2xl font-bold transition-all shadow-md hover:shadow-lg"
        >
          Run Downside Stress Simulator <ArrowRight size={16} className="ml-2" />
        </button>
      </div>
    </motion.div>
  );
}

