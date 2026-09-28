"use client";
import React, { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { api, RankResponse } from '@/lib/api-client';
import { Bell, ChevronDown, ArrowRight, Home, IndianRupee, ShieldAlert, Wallet, MapPin, Check, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { LocationUnavailableState } from '@/components/LocationUnavailableState';
import { useTranslations } from 'next-intl';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';

// Simple Top Navigation for Dashboard
const DashboardHeader = () => (
  <div className="flex justify-end items-center mb-6 pt-2">
    <button className="p-2 text-ink-soft hover:bg-black/5 rounded-full mr-4">
      <Bell size={20} />
    </button>
    <LanguageSwitcher />
  </div>
);

// Large YuktiFi Score Card
//
// Two corrections from the truthfulness pass:
//   1. `score` is `number | null`. The call site used to write `yuktiScore ?? 0`,
//      which rendered a missing score as 0/100. On an evaluation product 0 is the
//      worst possible score, so "not scored" was being displayed as "scored zero".
//   2. The verdict now comes from the engine (`scores.verdict`), not from
//      thresholds re-implemented in the client. The card previously recomputed
//      its own bands, so a score of 72 could read "Moderate" here while the API
//      reported the same 72 as withheld for insufficient coverage.
const YuktiFiScoreCard = ({
  score,
  verdict,
  reason,
}: {
  score: number | null;
  verdict: { text: string; color: string } | null;
  reason: string | null;
}) => {
  const t = useTranslations('dashboard.scoreCard');

  if (score === null) {
    return (
      <div className="bg-white rounded-3xl p-6 md:p-8 border border-premium-border shadow-card flex-1 min-w-[200px]">
        <h3 className="font-bold text-lg text-forest-deep mb-1">{t('title')}</h3>
        <div className="font-bold text-xl mb-3 text-[#ea580c]">{t('unavailable')}</div>
        <p className="text-sm font-medium text-ink-soft max-w-sm leading-relaxed">
          {reason || t('unavailableDesc')}
        </p>
      </div>
    );
  }

  // The engine maps a composite to a verdict only when coverage clears its
  // threshold, so a score can legitimately exist with no verdict attached.
  const verdictText = verdict ? verdict.text : t('verdictWithheld');
  const color =
    verdict?.color === 'emerald-600'
      ? 'text-[#16a34a]'
      : verdict?.color === 'red-600'
        ? 'text-red-500'
        : 'text-[#ea580c]';

  return (
    <div className="bg-white rounded-3xl p-6 md:p-8 border border-premium-border shadow-card flex flex-col md:flex-row items-center md:items-start gap-8 flex-1">
      {/* SVG Dial */}
      <div className="relative w-36 h-36 shrink-0">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="42" fill="none" stroke="#f0fdf4" strokeWidth="12" />
          <circle 
            cx="50" cy="50" r="42" 
            fill="none" 
            stroke="#16a34a" 
            strokeWidth="12" 
            strokeDasharray="263.89" 
            strokeDashoffset={263.89 - (263.89 * score) / 100} 
            strokeLinecap="round" 
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display font-bold text-4xl text-forest-deep leading-none -ml-1">{score}</span>
          <span className="text-xs font-bold text-ink-soft mt-1">/100</span>
        </div>
      </div>
      
      <div className="flex flex-col justify-center h-full">
        <h3 className="font-bold text-lg text-forest-deep mb-1">{t('title')}</h3>
        <div className={`${color} font-bold text-xl mb-3`}>{verdictText}</div>
        <p className="text-sm font-medium text-ink-soft mb-6 max-w-sm leading-relaxed">
          {t('desc')}
        </p>
        <Link href="/market-intelligence/custom">
          <button className="self-start px-6 py-2.5 rounded-xl border border-[#ea580c] text-[#ea580c] font-bold text-sm flex items-center hover:bg-[#fff5f0] transition-colors">
            {t('viewDetails')} <ArrowRight size={16} className="ml-2" />
          </button>
        </Link>
      </div>
    </div>
  );
};

// Recommended Business Card
const RecommendedBusinessCard = ({ categoryId, categoryName, score, ideaDetails }: { categoryId: string, categoryName: string, score: number | null, ideaDetails?: string }) => {
  const t = useTranslations('dashboard.recommended');
  
  let emoji = "🏪";
  if (categoryId === 'dairy') emoji = "🥛";
  if (categoryId === 'poultry') emoji = "🐔";
  if (categoryId === 'tailoring') emoji = "🧵";
  if (categoryId === 'flour_mill') emoji = "🌾";
  
  let title = categoryName;
  let desc = "";

  if (ideaDetails && ideaDetails.includes(':\n')) {
    const parts = ideaDetails.split(':\n');
    title = parts[0];
    desc = parts[1];
  } else if (ideaDetails) {
    desc = ideaDetails;
  }

  return (
    <div className="bg-white rounded-3xl p-6 md:p-8 border border-premium-border shadow-card flex flex-col w-full lg:w-[400px] shrink-0">
      <h3 className="text-sm font-bold text-forest-deep mb-4">{t('title')}</h3>
      
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="font-display font-bold text-2xl text-ink mb-1 leading-tight">{title}</h2>
          <span className="text-xs font-bold text-ink-soft bg-cream px-2 py-1 rounded border border-premium-border">{categoryName}</span>
        </div>
        <div className="w-16 h-16 bg-[#f4f9f6] rounded-2xl flex items-center justify-center border border-[#e5f0ea] shrink-0 ml-4">
          <span className="text-2xl">{emoji}</span>
        </div>
      </div>
      
      {desc && (
        <p className="text-sm text-ink-soft font-medium mb-6 line-clamp-3 leading-relaxed">{desc}</p>
      )}

      <div className="flex items-center space-x-3 mb-8 mt-auto">
        <span className="text-sm font-medium text-ink-soft">{t('score')}</span>
        {/* A null score must not print as "0/100". */}
        {score === null ? (
          <span className="text-sm font-bold text-ink-soft">{t('notScored')}</span>
        ) : (
          <span className="text-lg font-bold text-[#16a34a]">{score}<span className="text-xs text-ink-soft">/100</span></span>
        )}
      </div>

      <Link href={`/market-intelligence/${categoryId}`} className="mt-auto block">
        <button className="w-full px-6 py-3 rounded-xl border border-[#ea580c] text-[#ea580c] font-bold text-sm flex items-center justify-center hover:bg-[#fff5f0] transition-colors">
          {t('exploreBtn')} <ArrowRight size={16} className="ml-2" />
        </button>
      </Link>
    </div>
  );
};

// Small Metric Card
const MetricCard = ({ title, status, score, icon: Icon, colorClass }: any) => (
  <div className="bg-white rounded-2xl p-5 border border-premium-border shadow-sm flex flex-col">
    <div className="flex items-center text-xs font-bold text-ink-soft mb-3">
      <Icon size={14} className="mr-1.5 text-forest" /> {title}
    </div>
    <div className={`text-xl font-bold mb-1 ${colorClass}`}>{status}</div>
    {/* `score` is '—' when the dimension was not computed; appending "/100" to
        that reads as a malformed number rather than an absent one. */}
    <div className="text-sm font-bold text-forest-deep">
      {typeof score === 'number' ? <>{score}<span className="text-xs text-ink-soft">/100</span></> : score}
    </div>
  </div>
);

// Journey Tracker
const JourneyTracker = () => {
  const t = useTranslations('dashboard.journey');
  const steps = [
    { id: 1, label: t('profile'), status: t('completed') },
    { id: 2, label: t('location'), status: t('completed') },
    { id: 3, label: t('capital'), status: t('completed') },
    { id: 4, label: t('business'), status: t('inProgress') },
    { id: 5, label: t('plan'), status: t('next') }
  ];

  return (
    <div className="bg-white rounded-3xl p-6 md:p-8 border border-premium-border shadow-card mt-6">
      <h3 className="font-bold text-forest-deep mb-8">{t('title')}</h3>
      
      <div className="relative flex justify-between items-center max-w-4xl mx-auto px-4 md:px-12">
        <div className="absolute left-[10%] right-[10%] top-6 h-1 bg-[#f0f9f4] -z-10" />
        <div className="absolute left-[10%] top-6 h-1 bg-[#16a34a] -z-10" style={{ width: '60%' }} />

        {steps.map((step) => {
          let nodeColor = '';
          let textColor = '';
          let subTextColor = '';
          let icon = null;

          if (step.status === t('completed')) {
            nodeColor = 'bg-[#16a34a] text-white ring-4 ring-white';
            textColor = 'text-[#16a34a]';
            subTextColor = 'text-[#16a34a]';
            icon = <Check size={16} strokeWidth={3} />;
          } else if (step.status === t('inProgress')) {
            nodeColor = 'bg-[#ea580c] text-white ring-4 ring-white shadow-md scale-110';
            textColor = 'text-ink';
            subTextColor = 'text-[#ea580c]';
            icon = <div className="w-2 h-2 rounded-full bg-white" />;
          } else {
            nodeColor = 'bg-white border-2 border-premium-border-strong text-ink-soft ring-4 ring-white';
            textColor = 'text-ink';
            subTextColor = 'text-ink-soft';
            icon = <div className="w-2 h-2 rounded-full bg-premium-border-strong" />;
          }

          return (
            <div key={step.id} className="flex flex-col items-center text-center w-20">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center transition-all z-10 ${nodeColor}`}>
                {icon}
              </div>
              <div className={`mt-3 text-sm font-bold ${textColor}`}>{step.label}</div>
              <div className={`text-[11px] font-bold mt-1 ${subTextColor}`}>{step.status}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default function Dashboard() {
  const { profileName, analysisResult, marginCapital, categoryId, ideaDetails } = useStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const t = useTranslations('dashboard');

  const displayFirstName = profileName ? profileName.split(' ')[0] : 'Entrepreneur';

  useEffect(() => {
    // If analysis is already present in store, just stop loading and clear error.
    if (analysisResult) {
      setError("");
      setLoading(false);
    } else {
      // If someone hit /dashboard directly without onboarding, we might redirect or show error
      setError("No analysis found. Please complete onboarding first.");
      setLoading(false);
    }
  }, [analysisResult]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#fcfbf8] flex flex-col items-center justify-center">
        <Loader2 className="animate-spin text-forest mb-4" size={32} />
        <h2 className="text-lg font-bold text-ink">{t('loading.title')}</h2>
        <p className="text-sm text-ink-soft">{t('loading.subtitle')}</p>
      </div>
    );
  }

  if (error || !analysisResult) {
    return (
      <div className="min-h-screen bg-[#fcfbf8] flex flex-col items-center justify-center p-6 text-center">
        <ShieldAlert className="text-red-500 mb-4" size={48} />
        <h2 className="text-xl font-bold text-ink mb-2">{t('error.title')}</h2>
        <p className="text-ink-soft mb-6">{error || t('error.btn')}</p>
        <Link href="/">
          <button className="px-6 py-3 bg-forest text-white rounded-xl font-bold">{t('error.btn')}</button>
        </Link>
      </div>
    );
  }

  // Destructure real data from unified analysis payload (new API shape: business, not matched_business)
  const { market, financials, scores, ai_insights, business: matchedBusiness, matched_business, data_available, location: locationData } = analysisResult;
  const resolvedBusiness = matchedBusiness || matched_business;
  
  // Explicit null check — never use a fake fallback score
  const yuktiScore = scores?.overall ?? null;
  // Verdict and reason come from the engine. A composite can be published while
  // the verdict is still withheld for low coverage, so these are read
  // independently rather than derived from the score here.
  const yuktiVerdict = scores?.verdict ?? null;
  const notScoredReason = scores?.not_scored_reason ?? null;
  const targetBusinessName = resolvedBusiness?.area_of_interest || resolvedBusiness?.matched_category_id || "Custom Business";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 py-6 pb-20 animate-in fade-in duration-500 bg-[#fcfbf8] min-h-screen">
      
      <DashboardHeader />
      
      {/* Data Coverage Warning — strict, no fake fallback */}
      {!data_available ? (
        <LocationUnavailableState 
          locationName={locationData?.resolved || locationData?.district || 'this location'}
          message={locationData?.coverage_message}
        />
      ) : (
        <>
          {/* Main Greeting */}
          <div className="mb-8 border-b border-premium-border pb-6">
            <h1 className="text-[32px] font-bold text-forest-deep tracking-tight mb-1">
              {new Date().getHours() < 12 ? t('greeting.morning') : new Date().getHours() < 18 ? t('greeting.afternoon') : t('greeting.evening')}, {displayFirstName}!
            </h1>
            <p className="text-ink-soft font-medium text-lg">
              {t('greeting.subtitle')}
            </p>
          </div>

          {/* Top Cards Row */}
          <div className="flex flex-col lg:flex-row gap-6 mb-6">
            <YuktiFiScoreCard score={yuktiScore} verdict={yuktiVerdict} reason={notScoredReason} />
            <RecommendedBusinessCard 
              categoryId={resolvedBusiness?.matched_category_id || categoryId} 
              categoryName={targetBusinessName} 
              score={yuktiScore} 
              ideaDetails={ideaDetails || undefined} 
            />
          </div>

          {/* AI Insights & Rationale */}
          <div className="mb-6 bg-white rounded-3xl p-6 md:p-8 border border-premium-border shadow-card relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
              <svg width="100" height="100" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="#16a34a"/>
              </svg>
            </div>
            <h3 className="text-sm font-bold text-forest-deep mb-3 uppercase tracking-wider flex items-center">
              <span className="w-2 h-2 rounded-full bg-forest mr-2"></span> {t('aiInsights.title')}
            </h3>
            <p className="text-ink text-lg font-medium leading-relaxed mb-6 max-w-4xl">
              {ai_insights?.rationale}
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {ai_insights?.recommendations?.slice(0, 3).map((rec: string, i: number) => (
                <div key={i} className="bg-cream p-4 rounded-2xl border border-premium-border shadow-sm">
                  <span className="text-[#ea580c] font-bold text-xl block mb-2">0{i+1}</span>
                  <p className="text-sm text-ink-soft font-medium leading-relaxed">{rec}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Metrics Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard title={t('metrics.marketOpp')} status={scores?.dimensions?.market_opportunity != null ? (scores.dimensions.market_opportunity > 80 ? t('metrics.status.high') : t('metrics.status.medium')) : t('metrics.status.na')} score={scores?.dimensions?.market_opportunity ?? '—'} icon={Home} colorClass="text-[#16a34a]" />
            <MetricCard title={t('metrics.finViability')} status={scores?.dimensions?.financial_viability != null ? (scores.dimensions.financial_viability > 70 ? t('metrics.status.good') : t('metrics.status.warning')) : t('metrics.status.na')} score={scores?.dimensions?.financial_viability ?? '—'} icon={IndianRupee} colorClass={scores?.dimensions?.financial_viability != null && scores.dimensions.financial_viability > 70 ? "text-[#16a34a]" : "text-[#ea580c]"} />
            <MetricCard title={t('metrics.riskExp')} status={scores?.dimensions?.risk_exposure != null ? (scores.dimensions.risk_exposure > 70 ? t('metrics.status.low') : t('metrics.status.high')) : t('metrics.status.na')} score={scores?.dimensions?.risk_exposure ?? '—'} icon={ShieldAlert} colorClass={scores?.dimensions?.risk_exposure != null && scores.dimensions.risk_exposure > 70 ? "text-[#16a34a]" : "text-[#ea580c]"} />
            <MetricCard title={t('metrics.capEff')} status={scores?.dimensions?.capital_efficiency != null ? (scores.dimensions.capital_efficiency > 70 ? t('metrics.status.excellent') : t('metrics.status.fair')) : t('metrics.status.na')} score={scores?.dimensions?.capital_efficiency ?? '—'} icon={Wallet} colorClass="text-[#16a34a]" />
          </div>

          {/* Journey Tracker Row */}
          <JourneyTracker />
        </>
      )}

    </div>
  );
}
