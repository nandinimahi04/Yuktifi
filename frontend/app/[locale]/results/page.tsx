"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "@/routing";
import { useStore } from "@/lib/store";
import { api } from "@/lib/api-client";
import { formatCurrency } from "@/lib/formatters";
import { MapPin, TrendingUp, ArrowRight, CheckCircle2, ShieldAlert, Zap, AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";

export default function ResultsPage() {
  const router = useRouter();
  const { locationId, marginCapital, updateState, locationName, opportunities, sessionId } = useStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // If we already simulated opportunities in discover page, use them
    if (opportunities && opportunities.length > 0) {
      setLoading(false);
      return;
    }

    const fetchResults = async () => {
      if (!sessionId) {
        router.push("/");
        return;
      }

      /*
        Removed two fabrications from this call.

        `margin_capital: marginCapital || 50000` and `location_id: locationId ||
        "loc_1"` meant that a user who had declared neither still got a full,
        confident ranking - computed against a capital and a city they never
        entered. `/rank-opportunities` answers 400 for a non-positive margin
        precisely because ranking is capital-dependent, and
        `rank_opportunities` abstains per category when the cost is unknown. The
        client was quietly undoing both.

        The header made it worse. It rendered `Capital: ... : "₹75,000"`, a third
        invented figure that matched neither the 50,000 sent to the API nor
        anything the user typed, so the page displayed one capital and scored
        against another.

        Without a declared location and capital there is nothing to rank, so the
        page now says so and asks for the two inputs.
      */
      if (!locationId) {
        setError("No location has been confirmed yet, so opportunities cannot be ranked.");
        setLoading(false);
        return;
      }
      if (!marginCapital || marginCapital <= 0) {
        setError(
          "Your capital has not been declared. Opportunities are ranked against what you can bring to the table, so this cannot be computed without it."
        );
        setLoading(false);
        return;
      }

      try {
        const res = await api.rankOpportunities({
          session_id: sessionId,
          location_id: locationId,
          margin_capital: marginCapital
        });
        const mappedRankings = res.rankings.map((r: any) => ({
          category_id: r.category_id,
          category_name: r.category_name,
          score: r.yukti_score,
          rationale: r.note
        }));
        updateState({ opportunities: mappedRankings });
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load opportunities");
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, locationId, marginCapital]);

  const handleSelect = (categoryId: string, categoryName: string) => {
    updateState({ categoryId, categoryName });
    router.push(`/score/${categoryId.toLowerCase().replace(/\s+/g, '-')}`);
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto mt-20 flex flex-col items-center justify-center space-y-6 text-warm-text">
        <div className="w-16 h-16 border-4 border-warm-border border-t-warm-primary rounded-full animate-spin"></div>
        <h2 className="text-2xl font-bold animate-pulse">Analyzing Local Market...</h2>
        <p className="text-warm-muted">Finding the best matches for your capital in {locationName}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto mt-16 p-8 text-warm-text text-center">
        <AlertTriangle size={32} className="text-amber-600 mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-3">Cannot rank opportunities yet</h2>
        <p className="text-warm-muted">{error}</p>
        <button
          onClick={() => router.push("/capital")}
          className="mt-6 inline-flex items-center bg-warm-primary text-warm-text font-bold px-6 py-3 rounded-xl"
        >
          Declare your capital
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-4 md:p-8 text-warm-text animate-in fade-in duration-500">
      <div className="mb-10 border-b border-warm-border pb-6">
        <h1 className="text-3xl font-bold tracking-tight">Top Opportunities</h1>
        <div className="flex items-center space-x-4 mt-3">
          <span className="flex items-center text-sm font-medium text-warm-muted bg-warm-surface border border-warm-border px-3 py-1 rounded-full">
            <MapPin size={14} className="mr-2 text-warm-primary" />{" "}
            {locationName || "Location not confirmed"}
          </span>
          <span className="flex items-center text-sm font-medium text-warm-muted bg-warm-surface border border-warm-border px-3 py-1 rounded-full">
            Capital: {marginCapital ? formatCurrency(marginCapital) : "Not declared"}
          </span>
        </div>
      </div>

      <div className="space-y-6">
        {opportunities.map((opp, index) => (
          <motion.div 
            key={opp.category_id || index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <div 
              onClick={() => handleSelect(opp.category_id, opp.category_name)}
              className="bg-warm-surface border border-warm-border rounded-2xl overflow-hidden hover:border-warm-primary hover:shadow-lg transition-all cursor-pointer group flex flex-col md:flex-row"
            >
              <div className="p-6 md:p-8 flex-1">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="text-xs font-bold text-warm-muted uppercase tracking-wider mb-1">Rank {String(index + 1).padStart(2, '0')}</div>
                    <h2 className="text-2xl font-bold text-warm-text group-hover:text-warm-primary transition-colors">
                      {opp.category_name}
                    </h2>
                  </div>
                  <div className="text-center bg-warm-bg px-4 py-2 rounded-xl border border-warm-border">
                    <div className="text-2xl font-black text-emerald-600">{opp.score ?? "—"}</div>
                    <div className="text-[10px] font-bold text-warm-muted uppercase tracking-widest mt-1">YuktiFi Score</div>
                  </div>
                </div>

                <div className="bg-warm-primary/5 p-4 rounded-xl border border-warm-primary/20 mb-6">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-warm-primary mb-2 flex items-center">
                    <Zap size={14} className="mr-1" /> Why YuktiFi Recommends This
                  </h4>
                  <p className="text-warm-text font-medium text-sm leading-relaxed">
                    {opp.rationale || "High local demand signal. Moderate competition in a 5km radius. Strong fit for your available capital contribution."}
                  </p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-xs text-warm-muted uppercase tracking-wider mb-1">Demand</div>
                    <div className="font-semibold text-warm-text">High</div>
                  </div>
                  <div>
                    <div className="text-xs text-warm-muted uppercase tracking-wider mb-1">Competition</div>
                    <div className="font-semibold text-warm-text">Moderate</div>
                  </div>
                  <div>
                    <div className="text-xs text-warm-muted uppercase tracking-wider mb-1">Capital Fit</div>
                    <div className="font-semibold text-emerald-600">Strong</div>
                  </div>
                  <div>
                    <div className="text-xs text-warm-muted uppercase tracking-wider mb-1">Risk</div>
                    <div className="font-semibold text-amber-600">Moderate</div>
                  </div>
                </div>
              </div>

              <div className="bg-warm-bg border-t md:border-t-0 md:border-l border-warm-border p-6 flex flex-col justify-center items-center md:w-56">
                {opp.score == null ? (
                  <ShieldAlert size={32} className="text-warm-muted mb-3" />
                ) : opp.score >= 75 ? (
                  <CheckCircle2 size={32} className="text-emerald-500 mb-3" />
                ) : (
                  <ShieldAlert size={32} className="text-amber-500 mb-3" />
                )}
                <span className="text-sm font-bold text-warm-text uppercase tracking-wider text-center mb-4">
                  {opp.score == null
                    ? "Not Scored"
                    : opp.score >= 75
                    ? "High Potential"
                    : "Viable Option"}
                </span>
                
                <button className="w-full bg-warm-surface border border-warm-border hover:border-warm-primary hover:text-warm-primary text-warm-text px-4 py-2 rounded-lg font-medium text-sm flex items-center justify-center transition-colors">
                  View Analytics <ArrowRight size={16} className="ml-2" />
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
