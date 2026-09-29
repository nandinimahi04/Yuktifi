import React from "react";
import { ShieldCheck, AlertTriangle, XCircle, HelpCircle } from "lucide-react";

interface Props {
  verdict?: any;
  score?: number | null;
}

export function VerdictBanner({ verdict, score }: Props) {
  const verdictText = typeof verdict === 'object' && verdict !== null ? (verdict.text || '') : (verdict || '');
  const v = (verdictText || "").toUpperCase().trim();

  // If score is high (>=75) or verdict is positive
  const isGo =
    v === "GO" ||
    v.includes("STRONG") ||
    v.includes("HIGHLY") ||
    v.includes("OPPORTUNITY") ||
    (v.includes("RECOMMENDED") && !v.includes("NOT")) ||
    (typeof score === "number" && score >= 75 && !v.includes("NOT") && !v.includes("HIGH RISK"));

  // If score is moderate (50-74) or caution
  const isCaution =
    !isGo &&
    (v === "CAUTION" ||
      v.includes("MODERATE") ||
      v.includes("POTENTIAL") ||
      v.includes("CAUTION") ||
      v.includes("WATCH") ||
      (typeof score === "number" && score >= 50 && score < 75 && !v.includes("NOT") && !v.includes("HIGH RISK")));

  const isAlternative = !isGo && !isCaution && (v === "ALTERNATIVE" || v.includes("ALTERNATIVE") || v.includes("OPTION"));

  const isNotRecommended =
    !isGo &&
    !isCaution &&
    !isAlternative &&
    (v === "NOT_RECOMMENDED" ||
      v === "NO_GO" ||
      v.includes("NOT RECOMMENDED") ||
      v.includes("HIGH RISK") ||
      v.includes("UNVIABLE") ||
      (typeof score === "number" && score < 50));

  if (isGo) {
    return (
      <div className="flex items-start space-x-3.5 p-5 bg-emerald-50/90 border border-emerald-200 rounded-2xl shadow-sm mb-6">
        <ShieldCheck className="text-emerald-600 mt-0.5 shrink-0" size={24} />
        <div>
          <h4 className="font-bold text-forest-deep text-base">Highly Recommended — Strong Opportunity</h4>
          <p className="text-sm text-ink-soft font-medium mt-1 leading-relaxed">
            Strong financial viability with healthy margin of safety and verified market demand.
          </p>
        </div>
      </div>
    );
  }

  if (isCaution) {
    return (
      <div className="flex items-start space-x-3.5 p-5 bg-amber-50/90 border border-amber-200 rounded-2xl shadow-sm mb-6">
        <AlertTriangle className="text-amber-600 mt-0.5 shrink-0" size={24} />
        <div>
          <h4 className="font-bold text-forest-deep text-base">Proceed with Caution — Moderate Potential</h4>
          <p className="text-sm text-ink-soft font-medium mt-1 leading-relaxed">
            Viable project fundamentals. Maintain disciplined working capital and monitor monthly cash flows.
          </p>
        </div>
      </div>
    );
  }

  if (isAlternative) {
    return (
      <div className="flex items-start space-x-3.5 p-5 bg-blue-50/90 border border-blue-200 rounded-2xl shadow-sm mb-6">
        <HelpCircle className="text-blue-600 mt-0.5 shrink-0" size={24} />
        <div>
          <h4 className="font-bold text-forest-deep text-base">Alternative Options Available</h4>
          <p className="text-sm text-ink-soft font-medium mt-1 leading-relaxed">
            Consider exploring higher margin business variations or optimizing fixed costs.
          </p>
        </div>
      </div>
    );
  }

  if (isNotRecommended) {
    return (
      <div className="flex items-start space-x-3.5 p-5 bg-rose-50/90 border border-rose-200 rounded-2xl shadow-sm mb-6">
        <XCircle className="text-red-500 mt-0.5 shrink-0" size={24} />
        <div>
          <h4 className="font-bold text-red-700 text-base">High Risk Exposure — Restructure Plan</h4>
          <p className="text-sm text-red-600 font-medium mt-1 leading-relaxed">
            High risk of defaulting on loans. Project does not cover its operational costs and monthly installments under current assumptions.
          </p>
        </div>
      </div>
    );
  }

  // Fallback if neither matches (e.g. initial loading or custom text)
  return (
    <div className="flex items-start space-x-3.5 p-5 bg-emerald-50/90 border border-emerald-200 rounded-2xl shadow-sm mb-6">
      <ShieldCheck className="text-emerald-600 mt-0.5 shrink-0" size={24} />
      <div>
        <h4 className="font-bold text-forest-deep text-base">
          {typeof score === "number" && score >= 75 ? "Strong Opportunity" : "Automated Decision Assessment"}
        </h4>
        <p className="text-sm text-ink-soft font-medium mt-1 leading-relaxed">
          {verdictText || "Derived deterministically from multi-factor analysis across verified market and financial metrics."}
        </p>
      </div>
    </div>
  );
}
