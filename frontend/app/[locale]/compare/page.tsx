"use client";
import React, { useState } from 'react';
import { useStore } from '@/lib/store';
import { Card } from '@/components/ui/card';
import { ArrowRight, Sparkles, AlertTriangle, Info } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function ComparePage() {
  const router = useRouter();
  const { opportunities, updateState } = useStore();

  // Layout placeholder only. The roi field is intentionally absent so the
  // table shows "not calculated" instead of inventing a return figure. Real
  // opportunities carry a computed value from the financials engine.
  type CompareRow = {
    category_id: string;
    category_name: string;
    score?: number;
    demand?: string;
    competition?: string;
    capitalFit?: string;
    risk?: string;
    roi?: string;
  };

  // Only ranked opportunities the engines actually produced are shown.
  //
  // This used to fall back to three hardcoded businesses (Food Processing 87,
  // Local Retail 76, Transport 72) with invented demand, competition, capital-fit
  // and risk values whenever fewer than two real opportunities were available.
  // A visitor without data therefore saw a confident, fully-populated comparison
  // table of businesses that do not exist, and the highest of the invented
  // scores was decorated "Top Pick".
  const compareData: CompareRow[] = (opportunities ?? []).slice(0, 3);

  // "Top Pick" must be earned by the highest score actually present, not handed
  // to whichever row happened to be first in the array. Unscored rows are
  // excluded from the comparison entirely rather than being treated as 0.
  const scored = compareData.filter((r) => typeof r.score === 'number');
  const bestScore = scored.length ? Math.max(...scored.map((r) => r.score!)) : null;
  const bestRow = scored.length
    ? scored.reduce((a, b) => ((b.score ?? -1) > (a.score ?? -1) ? b : a))
    : null;
  const isBest = (row: CompareRow) =>
    bestScore !== null && typeof row.score === 'number' && row.score === bestScore;

  const rankedByRoi = compareData
    .filter((b) => b.roi != null)
    .sort((a, b) => parseFloat(b.roi!) - parseFloat(a.roi!));
  const bestRoi = rankedByRoi[0];
  const restRoi = rankedByRoi[1];

  // A missing value is reported as missing. Substituting a plausible-looking
  // default here would put a number on the page that no engine produced.
  const NA = <span className="text-sm font-normal text-warm-muted/70">Not assessed</span>;
  const show = (value: string | number | undefined) =>
    value == null || value === "" ? NA : value;

  const handleSelect = (categoryId: string, categoryName: string) => {
    updateState({ categoryId, categoryName });
    router.push(`/score/${categoryId.toLowerCase().replace(/\s+/g, '-')}`);
  };

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 text-warm-text animate-in fade-in duration-500">
      <div className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight">Compare Businesses</h1>
        <p className="text-warm-muted mt-2 text-lg">Evaluate your top opportunities side-by-side.</p>
      </div>

      {/* Nothing to compare: say so, rather than filling the table with invented
          businesses as the previous fallback did. */}
      {compareData.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-center bg-white rounded-2xl border border-warm-border p-12">
          <AlertTriangle className="w-10 h-10 text-amber-500 mb-4" />
          <h2 className="text-xl font-bold text-warm-text mb-2">No opportunities to compare yet</h2>
          <p className="text-warm-muted max-w-md mb-6">
            A comparison needs at least one ranked opportunity. Run the analysis for your
            location and capital, and the businesses that can actually be evaluated will
            appear here. Nothing is shown until the engines produce a result.
          </p>
          <Link href="/">
            <button className="px-6 py-3 bg-warm-primary text-white rounded-xl font-bold flex items-center">
              Start the analysis <ArrowRight className="ml-2 w-4 h-4" />
            </button>
          </Link>
        </div>
      ) : (
        <>
      <div className="overflow-x-auto pb-8">
        <table className="w-full min-w-[800px] border-collapse">
          <thead>
            <tr>
              <th className="p-4 text-left border-b-2 border-warm-border w-1/4">Metric</th>
              {compareData.map((biz: any) => (
                <th key={biz.category_id} className="p-4 text-center border-b-2 border-warm-border w-1/4">
                  <h3 className="text-xl font-bold text-warm-text">{biz.category_name}</h3>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-warm-border/50">
            <tr>
              <td className="p-4 font-semibold text-warm-muted">YuktiFi Score</td>
              {compareData.map((biz: any, i: number) => (
                <td key={biz.category_id} className="p-4 text-center">
                  <div className="inline-flex flex-col items-center justify-center">
                    <span className={`text-3xl font-black ${isBest(biz) ? 'text-emerald-600' : 'text-warm-text'}`}>{show(biz.score)}</span>
                    {isBest(biz) && <span className="text-[10px] uppercase font-bold text-warm-primary mt-1 flex items-center"><Sparkles size={10} className="mr-1"/> Top Pick</span>}
                  </div>
                </td>
              ))}
            </tr>
            <tr>
              <td className="p-4 font-semibold text-warm-muted">Demand</td>
              {compareData.map((biz: any) => (
                <td key={biz.category_id} className="p-4 text-center font-medium">{show(biz.demand)}</td>
              ))}
            </tr>
            <tr>
              <td className="p-4 font-semibold text-warm-muted">Competition</td>
              {compareData.map((biz: any) => (
                <td key={biz.category_id} className="p-4 text-center font-medium">{show(biz.competition)}</td>
              ))}
            </tr>
            <tr>
              <td className="p-4 font-semibold text-warm-muted">Capital Fit</td>
              {compareData.map((biz: any) => (
                <td key={biz.category_id} className="p-4 text-center font-medium text-emerald-600">{show(biz.capitalFit)}</td>
              ))}
            </tr>
            <tr>
              <td className="p-4 font-semibold text-warm-muted">Risk Profile</td>
              {compareData.map((biz: any) => (
                <td key={biz.category_id} className="p-4 text-center font-medium flex items-center justify-center">
                {(biz.risk === "High" || (!biz.risk && biz.score < 75)) && <AlertTriangle size={14} className="text-amber-500 mr-2" />}
                {show(biz.risk)}
                </td>
              ))}
            </tr>
            <tr>
              <td className="p-4 font-semibold text-warm-muted">
                Annual Return on Project
                <span className="block text-xs font-normal text-warm-muted/70">
                  on total project cost
                </span>
              </td>
              {compareData.map((biz: any) => (
                <td key={biz.category_id} className="p-4 text-center font-bold text-warm-text">
                  {biz.roi != null ? (
                    biz.roi
                  ) : (
                    <span className="text-sm font-normal text-warm-muted/70">
                      Not calculated — run financials
                    </span>
                  )}
                </td>
              ))}
            </tr>
            
            {/* Actions Row */}
            <tr>
              <td className="p-4"></td>
              {compareData.map((biz: any, i: number) => (
                <td key={biz.category_id} className="p-4 text-center">
                  <button 
                    onClick={() => handleSelect(biz.category_id, biz.category_name)}
                    className={`w-full py-3 rounded-lg font-bold flex items-center justify-center transition-all ${
                      i === 0 
                      ? 'bg-warm-primary text-warm-text hover:bg-warm-primary/90 hover:shadow-lg' 
                      : 'bg-warm-surface border border-warm-border hover:border-warm-primary hover:text-warm-primary'
                    }`}
                  >
                    Select Plan <ArrowRight size={16} className="ml-2" />
                  </button>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-8 bg-warm-primary/10 border border-warm-primary/20 rounded-xl p-6 flex items-start">
        <Info size={24} className="text-warm-primary mr-4 flex-shrink-0 mt-1" />
        <div>
          <h4 className="font-bold text-warm-text mb-1">YuktiFi Insight</h4>
          <p className="text-warm-muted text-sm leading-relaxed">
            {bestRoi && restRoi ? (
              <>
                {bestRoi.category_name} shows the strongest modelled return at {bestRoi.roi} on
                total project cost, against {restRoi.roi} for {restRoi.category_name}. Higher
                return is not automatically better: check the demand and competition columns
                alongside it.
              </>
            ) : (
              <>
                {bestRow
                  ? `${bestRow.category_name} currently ranks highest on overall score (${bestRow.score}). `
                  : 'No overall score could be computed for these options. '}
                Returns have not been modelled yet for them — open a plan to run the
                financials before comparing on return.
              </>
            )}
          </p>
        </div>
      </div>
        </>
      )}
    </div>
  );
}
