"use client";
import React, { useState, useEffect } from "react";
import { 
  ShieldCheck, 
  AlertTriangle, 
  TrendingUp, 
  ShieldAlert, 
  Sparkles, 
  RefreshCw, 
  Loader2,
  CheckCircle2,
  ArrowRight,
  Info
} from "lucide-react";
import { api } from "@/lib/api-client";

export interface SwotItem {
  title: string;
  description: string;
  impact?: string;
  mitigation?: string;
  potential?: string;
  contingency?: string;
}

export interface SwotData {
  strengths: SwotItem[];
  weaknesses: SwotItem[];
  opportunities: SwotItem[];
  threats: SwotItem[];
  strategic_summary?: string;
  ai_generated?: boolean;
  model_used?: string;
}

interface SwotMatrixProps {
  categoryId?: string;
  categoryName?: string;
  locationName?: string;
  financials?: any;
  marketData?: any;
  scores?: any;
  initialSwot?: SwotData | null;
}

export const SwotMatrix: React.FC<SwotMatrixProps> = ({
  categoryId = "poultry",
  categoryName = "Poultry Farming (Broiler/Layer)",
  locationName = "Solapur, Maharashtra",
  financials,
  marketData,
  scores,
  initialSwot
}) => {
  const [swot, setSwot] = useState<SwotData | null>(initialSwot || null);
  const [loading, setLoading] = useState<boolean>(!initialSwot);
  const [regenerating, setRegenerating] = useState<boolean>(false);

  const fetchSwot = async (isRefresh = false) => {
    if (isRefresh) setRegenerating(true);
    else setLoading(true);

    try {
      const res = await api.getSwotAnalysis({
        category_id: categoryId,
        category_name: categoryName,
        location_name: locationName,
        financials: financials || {},
        market_data: marketData || {},
        scores: scores || {}
      });
      if (res) {
        setSwot(res);
      }
    } catch (err) {
      console.error("Failed to load SWOT analysis:", err);
    } finally {
      setLoading(false);
      setRegenerating(false);
    }
  };

  useEffect(() => {
    if (!initialSwot) {
      fetchSwot();
    }
  }, [categoryId, categoryName, locationName]);

  if (loading) {
    return (
      <div className="bg-white border border-gray-200/80 rounded-3xl p-8 shadow-sm flex flex-col items-center justify-center min-h-[300px]">
        <Loader2 size={32} className="animate-spin text-emerald-600 mb-3" />
        <p className="text-xs font-bold text-slate-700 uppercase tracking-wider">
          Synthesizing AI SWOT Matrix with Gemini...
        </p>
        <span className="text-[11px] text-slate-400 mt-1">
          Evaluating unit economics, catchment density & supply risks
        </span>
      </div>
    );
  }

  const strengths = swot?.strengths || [];
  const weaknesses = swot?.weaknesses || [];
  const opportunities = swot?.opportunities || [];
  const threats = swot?.threats || [];
  const summary = swot?.strategic_summary || 
    "The enterprise demonstrates strong unit margins and recurring local demand. Long-term capital security depends on feed procurement control and disciplined cash reserve buffers.";

  return (
    <div className="bg-white border border-gray-200/80 rounded-3xl p-6 sm:p-8 shadow-sm relative overflow-hidden">
      {/* Header Row */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-3 border-b border-gray-100 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              ENTERPRISE SWOT ANALYSIS (GEMINI POWERED)
            </h3>
          </div>
          <p className="text-xs text-slate-500 font-medium">
            AI-grounded strategic feasibility matrix tailored for <strong className="text-slate-800">{categoryName}</strong> in <strong className="text-slate-800">{locationName}</strong>.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[11px] font-bold text-emerald-800 bg-[#ecfdf5] border border-[#a7f3d0] px-3 py-1 rounded-full flex items-center gap-1.5 shadow-2xs">
            <Sparkles size={13} className="text-emerald-600" />
            {swot?.ai_generated ? "Gemini 1.5 Flash Verified" : "Grounded Strategic Engine"}
          </span>

          <button
            onClick={() => fetchSwot(true)}
            disabled={regenerating}
            title="Regenerate with Gemini AI"
            className="p-2 border border-gray-200 rounded-xl hover:bg-slate-50 text-slate-600 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={regenerating ? "animate-spin text-emerald-600" : ""} />
          </button>
        </div>
      </div>

      {/* Strategic Executive Summary Callout */}
      <div className="mb-6 p-4 bg-emerald-50/60 border border-emerald-200/70 rounded-2xl flex items-start gap-3">
        <CheckCircle2 size={18} className="text-emerald-600 mt-0.5 shrink-0" />
        <div>
          <span className="text-[10px] font-black uppercase tracking-wider text-emerald-800 block mb-0.5">
            Executive SWOT Synthesis
          </span>
          <p className="text-xs text-emerald-950 font-medium leading-relaxed">
            {summary}
          </p>
        </div>
      </div>

      {/* 4-Quadrant SWOT Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        
        {/* STRENGTHS */}
        <div className="bg-[#f0fdf4] border border-[#bbf7d0] rounded-2xl p-5 shadow-2xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 border-b border-[#bbf7d0]/60 pb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-emerald-100/80 rounded-lg text-emerald-700">
                  <ShieldCheck size={16} />
                </div>
                <h4 className="text-xs font-black uppercase tracking-wider text-emerald-900">
                  Strengths (Internal)
                </h4>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-200/70 text-emerald-800 rounded-md">
                {strengths.length} Factors
              </span>
            </div>

            <div className="space-y-3">
              {strengths.map((item, idx) => (
                <div key={idx} className="bg-white/80 p-3 rounded-xl border border-emerald-100/90 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-900">{item.title}</span>
                    {item.impact && (
                      <span className="text-[9px] font-extrabold uppercase px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded border border-emerald-200">
                        {item.impact} IMPACT
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-600 font-medium leading-relaxed">
                    {item.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* WEAKNESSES */}
        <div className="bg-[#fffbeb] border border-[#fde68a] rounded-2xl p-5 shadow-2xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 border-b border-[#fde68a]/60 pb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-amber-100/80 rounded-lg text-amber-700">
                  <AlertTriangle size={16} />
                </div>
                <h4 className="text-xs font-black uppercase tracking-wider text-amber-900">
                  Weaknesses (Internal)
                </h4>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-amber-200/70 text-amber-800 rounded-md">
                {weaknesses.length} Factors
              </span>
            </div>

            <div className="space-y-3">
              {weaknesses.map((item, idx) => (
                <div key={idx} className="bg-white/80 p-3 rounded-xl border border-amber-100/90 text-xs">
                  <span className="font-bold text-slate-900 block mb-1">{item.title}</span>
                  <p className="text-[11px] text-slate-600 font-medium leading-relaxed mb-2">
                    {item.description}
                  </p>
                  {item.mitigation && (
                    <div className="pt-2 border-t border-amber-100 text-[11px] text-amber-800 font-semibold flex items-start gap-1">
                      <span className="text-[10px] uppercase font-black text-amber-900">Mitigation:</span>
                      <span>{item.mitigation}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* OPPORTUNITIES */}
        <div className="bg-[#f0f9ff] border border-[#bae6fd] rounded-2xl p-5 shadow-2xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 border-b border-[#bae6fd]/60 pb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-sky-100/80 rounded-lg text-sky-700">
                  <TrendingUp size={16} />
                </div>
                <h4 className="text-xs font-black uppercase tracking-wider text-sky-900">
                  Opportunities (External)
                </h4>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-sky-200/70 text-sky-800 rounded-md">
                {opportunities.length} Avenues
              </span>
            </div>

            <div className="space-y-3">
              {opportunities.map((item, idx) => (
                <div key={idx} className="bg-white/80 p-3 rounded-xl border border-sky-100/90 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-900">{item.title}</span>
                    {item.potential && (
                      <span className="text-[9px] font-extrabold uppercase px-1.5 py-0.5 bg-sky-50 text-sky-700 rounded border border-sky-200">
                        {item.potential} POTENTIAL
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-600 font-medium leading-relaxed">
                    {item.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* THREATS */}
        <div className="bg-[#fff1f2] border border-[#fecdd3] rounded-2xl p-5 shadow-2xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 border-b border-[#fecdd3]/60 pb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-rose-100/80 rounded-lg text-rose-700">
                  <ShieldAlert size={16} />
                </div>
                <h4 className="text-xs font-black uppercase tracking-wider text-rose-900">
                  Threats (External)
                </h4>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-rose-200/70 text-rose-800 rounded-md">
                {threats.length} Risks
              </span>
            </div>

            <div className="space-y-3">
              {threats.map((item, idx) => (
                <div key={idx} className="bg-white/80 p-3 rounded-xl border border-rose-100/90 text-xs">
                  <span className="font-bold text-slate-900 block mb-1">{item.title}</span>
                  <p className="text-[11px] text-slate-600 font-medium leading-relaxed mb-2">
                    {item.description}
                  </p>
                  {item.contingency && (
                    <div className="pt-2 border-t border-rose-100 text-[11px] text-rose-800 font-semibold flex items-start gap-1">
                      <span className="text-[10px] uppercase font-black text-rose-900">Contingency:</span>
                      <span>{item.contingency}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
