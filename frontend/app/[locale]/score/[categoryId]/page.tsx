"use client";
import React, { useEffect, useState } from "react";
import { useRouter } from "@/routing";
import { useStore } from "@/lib/store";
import { api, type RecommendResponse } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScoreDial } from "@/components/ScoreDial";
import { VerdictBanner } from "@/components/VerdictBanner";
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
  type LucideIcon,
} from "lucide-react";
import { motion } from "framer-motion";
import Link from "next/link";

const DIMENSION_META: Record<
  string,
  { label: string; icon: LucideIcon; description: string }
> = {
  financial_viability: {
    label: "Financial Viability",
    icon: TrendingUp,
    description: "Revenue vs costs vs debt obligations",
  },
  repayment_capacity: {
    label: "Repayment Capacity",
    icon: Wallet,
    description: "Ability to service the loan (Loan Repayment Capacity)",
  },
  market_opportunity: {
    label: "Market Opportunity",
    icon: Target,
    description: "Demand, competition gap, consumer base",
  },
  capital_efficiency: {
    label: "Capital Efficiency",
    icon: BarChart3,
    description: "Return per rupee invested",
  },
  risk_exposure: {
    label: "Risk Exposure",
    icon: Shield,
    description: "Threat density and market volatility",
  },
};

export default function ScorePage() {
  const router = useRouter();
  const state = useStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
          <Loader2 size={48} className="animate-spin text-warm-primary" />
          <p className="text-warm-primary font-sans animate-pulse font-medium">
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
              className="inline-flex items-center bg-warm-primary text-warm-text px-6 py-3 rounded-lg font-bold hover:bg-orange-600 transition-colors"
            >
              Start Over <ArrowRight size={16} className="ml-2" />
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const analysisResult = state.analysisResult;
  const { scores, financials } = analysisResult;
  // A null DSCR means the session carries no debt, which is not a score of
  // zero. Coercing it to 0 would both invent a failing ratio and hide the
  // reason. Same for ROI: unknown stays unknown.
  const dscr: number | null = financials.dscr ?? null;
  const roi: number | null = financials.roi_pct ?? null;
  /*
    Removed three client-side fabrications from this block.

    `confidence: "High"` and `confidence_multiplier: 1.0` were literals. The
    page therefore labelled a score "High" confidence no matter how little had
    actually been computed, and then displayed "x 100% confidence" next to it as
    though it had been measured. The backend models this properly -
    `RecommendResponse` carries `confidence`, `confidence_multiplier`,
    `unscored_dimensions`, `dscr_status` and `roi_status`, and the score card
    carries a coverage percentage - and the page was overriding all of it.

    `verdict` was re-derived from the score alone, with bands at 70 and 50
    ("Excellent Opportunity" / "Moderate Potential" / "High Risk") that exist
    nowhere else in the product. A score is not a decision: `advisory/decision.py`
    gates on financial viability, repayment capacity and evidence, so a business
    failing a financial gate could still be labelled "Moderate Potential" here
    from its score alone. That is the one-source-of-truth violation the
    acceptance criteria name, sitting in the client.

    Confidence now comes from the API when the session has it and falls back to
    an honest "unavailable" when it does not. The verdict is only shown if the
    engine produced one; otherwise the page says the verdict is not computed
    rather than inventing a band.
  */
  const apiConfidence: string | null =
    analysisResult?.confidence ?? analysisResult?.recommendation?.confidence ?? null;
  const apiVerdict: string | null =
    analysisResult?.verdict ?? analysisResult?.recommendation?.verdict ?? null;
  const confidence: string = apiConfidence ?? "Unavailable";
  const confidenceIsKnown = apiConfidence !== null;
  const confidenceMultiplier: number | null =
    analysisResult?.confidence_multiplier ?? analysisResult?.recommendation?.confidence_multiplier ?? null;

  const data: any = {
    yukti_score: scores.overall,
    // `raw_score` was a copy of `yukti_score`; displaying it as a separate
    // "raw" figure implied a pre-confidence value that does not exist here.
    raw_score: scores.overall,
    confidence,
    confidence_multiplier: confidenceMultiplier,
    confidence_is_known: confidenceIsKnown,
    // Null, not a locally derived band. `VerdictBanner` is only rendered when
    // the engine supplied one.
    verdict: apiVerdict,
    dscr,
    roi,
    next_steps: [
      "Review the financial model in detail",
      "Check market intelligence for local competitors",
      "Run what-if simulations to stress-test your margins"
    ],
    dimension_scores: {
      financial_viability: scores.financial,
      repayment_capacity: dscr != null ? Math.min(100, (dscr / 2) * 100) : null,
      market_opportunity: scores.market,
      capital_efficiency: roi != null ? Math.min(100, Math.max(0, roi)) : null,
      risk_exposure: scores.risk,
    }
  };

  const scoreColor =
    data.yukti_score >= 70
      ? "text-emerald-600"
      : data.yukti_score >= 50
      ? "text-amber-600"
      : "text-red-600";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="max-w-5xl mx-auto p-4 md:p-8 pb-20 font-sans text-warm-text"
    >
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-8 border-b border-warm-border pb-4 mt-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">YuktiFi Score</h1>
          <p className="text-warm-muted mt-1 text-sm font-medium">
            Deterministic multi-factor analysis for{" "}
            <strong className="text-warm-text">{state.categoryName || "your business"}</strong>
          </p>
        </div>
        <div className="mt-4 sm:mt-0 text-right">
          <div className="text-xs font-bold text-warm-muted uppercase tracking-wider mb-1">
            Data Confidence
          </div>
          <span
            className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${
              data.confidence === "High"
                ? "bg-emerald-100 text-emerald-800"
                : data.confidence === "Medium"
                ? "bg-amber-100 text-amber-800"
                : "bg-red-100 text-red-800"
            }`}
          >
            {data.confidence}
          </span>
        </div>
      </div>

      {data.verdict ? (
        <VerdictBanner verdict={data.verdict} />
      ) : (
        <div className="rounded-2xl border border-premium-border bg-white p-5">
          <div className="text-xs font-bold uppercase tracking-widest text-warm-muted">
            Decision
          </div>
          <div className="text-lg font-bold text-warm-text mt-1">
            No verdict computed
          </div>
          <p className="text-sm text-warm-muted mt-1">
            A score is not a decision. The engine has not run its evidence gates
            for this session, and this page will not derive a verdict from the
            score alone.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Score Dial */}
        <Card className="border-warm-border shadow-sm bg-warm-surface rounded-2xl overflow-hidden">
          <CardHeader className="bg-warm-bg/50 pb-3 border-b border-warm-border">
            <CardTitle className="text-sm font-bold text-warm-text uppercase tracking-wider">
              Final Score
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center pt-6 pb-6 space-y-4">
            <ScoreDial score={data.yukti_score} />
            <div className={`text-5xl font-black ${scoreColor}`}>{data.yukti_score}</div>
            <div className="text-xs text-warm-muted font-medium">
              {data.confidence_is_known && data.confidence_multiplier !== null
          ? `Score × ${(data.confidence_multiplier * 100).toFixed(0)}% confidence`
          : "Confidence not computed for this session"}
            </div>
          </CardContent>
        </Card>

        {/* Key Metrics */}
        <Card className="border-warm-border shadow-sm bg-warm-surface rounded-2xl overflow-hidden">
          <CardHeader className="bg-warm-bg/50 pb-3 border-b border-warm-border">
            <CardTitle className="text-sm font-bold text-warm-text uppercase tracking-wider">
              Key Metrics
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-warm-border">
              <span className="text-sm text-warm-muted font-medium">Loan Repayment Capacity</span>
              {data.dscr == null ? (
                <span className="text-sm font-bold text-warm-muted">
                  Not applicable — no debt in this plan
                </span>
              ) : (
                <span
                  className={`text-sm font-bold ${
                    data.dscr >= 1.5
                      ? "text-emerald-600"
                      : data.dscr >= 1.0
                      ? "text-amber-600"
                      : "text-red-600"
                  }`}
                >
                  {data.dscr.toFixed(2)}x{" "}
                  {data.dscr >= 1.5 ? "✓ Healthy" : data.dscr >= 1.0 ? "⚠ Marginal" : "✗ Below gate"}
                </span>
              )}
            </div>
            <div className="flex justify-between items-center py-2 border-b border-warm-border">
              <span className="text-sm text-warm-muted font-medium">Annual Return on Project</span>
              <span className="text-sm font-bold text-warm-text">
                {data.roi == null ? "Not calculated" : `${data.roi.toFixed(1)}%`}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-warm-border">
              <span className="text-sm text-warm-muted font-medium">Confidence</span>
              <span className="text-sm font-bold text-warm-text">{data.confidence}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-sm text-warm-muted font-medium">Engine</span>
              <span className="text-xs font-bold text-warm-muted bg-warm-bg border border-warm-border px-2 py-1 rounded-md">
                Deterministic v2
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Next Steps */}
        <Card className="border-warm-border shadow-sm bg-warm-surface rounded-2xl overflow-hidden">
          <CardHeader className="bg-warm-bg/50 pb-3 border-b border-warm-border">
            <CardTitle className="text-sm font-bold text-warm-text uppercase tracking-wider">
              Recommended Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <ul className="space-y-3">
              {data.next_steps.map((step: string, i: number) => (
                <li key={i} className="flex items-start space-x-3">
                  <CheckCircle2
                    size={16}
                    className="text-warm-secondary mt-0.5 flex-shrink-0"
                  />
                  <span className="text-sm text-warm-text font-medium leading-snug">{step}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Dimension Breakdown */}
      <Card className="border-warm-border shadow-sm bg-warm-surface rounded-2xl overflow-hidden mt-6">
        <CardHeader className="bg-warm-bg/50 pb-3 border-b border-warm-border">
          <CardTitle className="text-sm font-bold text-warm-text uppercase tracking-wider">
            Score Breakdown — Why this score?
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="space-y-5">
            {Object.entries(data.dimension_scores).map(([key, value]) => {
              const meta = DIMENSION_META[key];
              const Icon = meta?.icon;
              // A dimension with no underlying metric is unscored, not zero.
              // Rendering it as 0/100 would read as a failing grade.
              const scored = typeof value === "number" && Number.isFinite(value);
              const pct = scored ? Math.min(100, Math.max(0, value as number)) : 0;
              return (
                <div key={key}>
                  <div className="flex justify-between items-center mb-1.5">
                    <div className="flex items-center space-x-2">
                      {Icon && <Icon size={14} className="text-warm-primary" />}
                      <span className="text-sm font-bold text-warm-text">
                        {meta?.label || key}
                      </span>
                    </div>
                    <span
                      className={
                        scored
                          ? "text-sm font-bold text-warm-text"
                          : "text-sm font-bold text-warm-muted"
                      }
                    >
                      {scored ? `${pct.toFixed(0)}/100` : "Not applicable"}
                    </span>
                  </div>
                  {scored ? (
                    <div className="w-full h-2 bg-warm-border rounded-full">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          pct >= 70
                            ? "bg-emerald-500"
                            : pct >= 45
                            ? "bg-amber-500"
                            : "bg-red-500"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  ) : (
                    <div className="w-full h-2 bg-warm-border/40 rounded-full" />
                  )}
                  {meta?.description && (
                    <p className="text-xs text-warm-muted mt-1">{meta.description}</p>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <div className="mt-8 flex justify-end">
        <button
          onClick={() => router.push("/simulator")}
          className="flex items-center bg-warm-primary text-warm-text px-6 py-3 rounded-xl font-bold hover:bg-orange-600 transition-colors shadow-md"
        >
          Run What-If Simulator <ArrowRight size={16} className="ml-2" />
        </button>
      </div>
    </motion.div>
  );
}
