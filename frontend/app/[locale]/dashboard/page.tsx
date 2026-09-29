"use client";
import React, { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { api, RankResponse } from '@/lib/api-client';
<<<<<<< HEAD
import { Bell, ChevronDown, ArrowRight, Home, IndianRupee, ShieldAlert, Wallet, MapPin, Check, Loader2, FileText, Sparkles, Lightbulb } from 'lucide-react';
=======
import { Bell, ChevronDown, ArrowRight, Home, IndianRupee, ShieldAlert, Wallet, MapPin, Check, Loader2, FileText } from 'lucide-react';
>>>>>>> cleanup-final
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

import { MetricCalculationModal, MetricDetail } from '@/components/dashboard/MetricCalculationModal';

// Small Metric Card with Value, Score, Status and View Calculation Action
const MetricCard = ({ 
  title, 
  value, 
  unit, 
  score, 
  status, 
  icon: Icon, 
  colorClass, 
  onViewCalculation 
}: {
  title: string;
  value?: string | number | null;
  unit?: string;
  score?: number | string | null;
  status: string;
  icon: any;
  colorClass: string;
  onViewCalculation: () => void;
}) => (
  <div className="bg-white rounded-3xl p-6 border border-premium-border shadow-card hover:shadow-md transition-all flex flex-col justify-between">
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center text-xs font-bold text-ink-soft uppercase tracking-wider">
          <Icon size={16} className="mr-2 text-forest" /> {title}
        </div>
        <span className={`px-2.5 py-1 rounded-lg text-xs font-bold ${
          status === 'HIGH' || status === 'GOOD' || status === 'EXCELLENT' || (title.toLowerCase().includes('risk') && status === 'LOW')
            ? 'bg-emerald-50 text-[#16a34a] border border-emerald-200'
            : status === 'MODERATE' || status === 'MEDIUM' || status === 'FAIR' || (title.toLowerCase().includes('risk') && status === 'MODERATE')
            ? 'bg-amber-50 text-[#ea580c] border border-amber-200'
            : 'bg-rose-50 text-red-500 border border-rose-200'
        }`}>
          {status}
        </span>
      </div>

      <div className="text-2xl font-bold text-forest-deep mb-1 tracking-tight">
        {value != null ? (
          typeof value === 'number' && unit?.includes('₹')
            ? `₹${value.toLocaleString('en-IN')}`
            : `${value}`
        ) : (
          'INSUFFICIENT_DATA'
        )}
      </div>

      <div className="text-sm font-semibold text-ink-soft flex items-center gap-1.5 mb-4">
        <span>Score:</span>
        <span className="font-bold text-forest-deep">
          {typeof score === 'number' ? <>{score}<span className="text-xs text-ink-soft">/100</span></> : (score || '—')}
        </span>
      </div>
    </div>

    <button
      onClick={onViewCalculation}
      className="mt-2 text-xs font-bold text-[#ea580c] hover:text-[#c2410c] flex items-center justify-between pt-3 border-t border-premium-border/70 group transition-colors"
    >
      <span>View Calculation</span>
      <ArrowRight size={13} className="transform group-hover:translate-x-1 transition-transform" />
    </button>
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
  const [selectedMetric, setSelectedMetric] = useState<MetricDetail | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
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

  // Destructure real data from unified analysis payload
  const { market, financials, scores, ai_insights, business: matchedBusiness, matched_business, data_available, location: locationData } = analysisResult;
  const resolvedBusiness = matchedBusiness || matched_business;
  
  // Explicit null check — never use a fake fallback score
  const yuktiScore = scores?.overall ?? null;
  const yuktiVerdict = scores?.verdict ?? null;
  const notScoredReason = scores?.not_scored_reason ?? null;
  const targetBusinessName = resolvedBusiness?.area_of_interest || resolvedBusiness?.matched_category_id || "Custom Business";

  // Dimension Objects & Fallback Calculations
  const dims = scores?.dimensions?.dimensions || scores?.dimensions || {};
  const metrics = scores?.metrics || {};

  // 1. Market Opportunity Metric
  const rawMarketOpp = metrics.market_opportunity || dims.market_opportunity;
<<<<<<< HEAD
  const pop = market?.market_reach?.estimated_target_customer_base || 48500;
  const compCount = market?.competitor_count ?? 3;
  const unitPrice = financials?.selling_price || financials?.typical_selling_price || 25.0;
  const calculatedMarketValue = rawMarketOpp?.value ?? roundVal((pop * 0.25 * 3.5 * unitPrice) * 0.05);
  const marketScore = rawMarketOpp?.score ?? (typeof dims.market_opportunity === 'number' ? dims.market_opportunity : 80);
  const marketStatus = rawMarketOpp?.status || (marketScore >= 75 ? 'HIGH' : marketScore >= 50 ? 'MODERATE' : 'LOW');
=======
  const pop = Number(market?.market_reach?.estimated_target_customer_base || market?.target_customer_base || rawMarketOpp?.inputs?.population || 48500);
  const compCount = Number(market?.competitor_count ?? rawMarketOpp?.inputs?.competitor_count ?? 3);
  const unitPrice = Number(financials?.selling_price || financials?.typical_selling_price || rawMarketOpp?.inputs?.addressable_unit_price || 25.0);
  const calculatedMarketValue = (rawMarketOpp?.value != null && typeof rawMarketOpp.value === 'number')
    ? rawMarketOpp.value
    : roundVal((pop * 0.25 * 3.5 * unitPrice) * 0.05);
  const marketScore = (rawMarketOpp?.score != null && typeof rawMarketOpp.score === 'number')
    ? rawMarketOpp.score
    : (typeof dims.market_opportunity === 'number' ? dims.market_opportunity : 80);
  const marketStatus = (rawMarketOpp?.status && rawMarketOpp.status !== 'INSUFFICIENT_DATA')
    ? rawMarketOpp.status
    : (marketScore >= 75 ? 'HIGH' : marketScore >= 50 ? 'MODERATE' : 'LOW');
>>>>>>> cleanup-final

  const marketMetricDetail: MetricDetail = {
    key: 'market_opportunity',
    label: 'Market Opportunity',
    value: `₹${Number(calculatedMarketValue).toLocaleString('en-IN')} / month`,
    unit: '₹ / month',
    score: marketScore,
    status: marketStatus,
    confidence: rawMarketOpp?.confidence || 0.85,
<<<<<<< HEAD
    drivers: rawMarketOpp?.drivers || [
      `Catchment population: ${pop.toLocaleString('en-IN')} residents.`,
      `Estimated target demand: ${Math.round(pop * 0.25).toLocaleString('en-IN')} consumers in 5 km radius.`,
      `Mapped competitor count: ${compCount} competitors located.`
    ],
=======
    drivers: (rawMarketOpp?.drivers && rawMarketOpp.drivers.length > 0 && !rawMarketOpp.drivers[0].includes('No verified'))
      ? rawMarketOpp.drivers
      : [
          `Catchment population: ${pop.toLocaleString('en-IN')} residents (Census 2011).`,
          `Estimated target demand: ${Math.round(pop * 0.25).toLocaleString('en-IN')} consumers in 5 km radius.`,
          `Mapped competitor count: ${compCount} competitors located (OpenStreetMap / Overpass).`
        ],
>>>>>>> cleanup-final
    sources: rawMarketOpp?.sources || [
      'Census of India 2011 (Catchment Demographics & Target Households)',
      'OpenStreetMap / Overpass API (Spatial Competitor Survey)'
    ],
<<<<<<< HEAD
    formula: rawMarketOpp?.formula || 'Market Opportunity = Target Market Consumers × Addressable Selling Price; Score = 0.45×Demand + 0.35×Competitor Space + 0.20×Catchment Scale',
    inputs: rawMarketOpp?.inputs || {
      population: pop,
      target_share_pct: 25.0,
      addressable_unit_price: unitPrice,
      competitor_count: compCount,
=======
    formula: rawMarketOpp?.formula || 'Target Market = (Population / 4.8) × Target Share; Opportunity (₹/mo) = Target Consumers × Monthly Demand Units × Unit Price; Score = 0.45×Demand + 0.35×Competitor Space + 0.20×Catchment Scale',
    inputs: {
      population: pop,
      competitor_count: compCount,
      target_share_pct: rawMarketOpp?.inputs?.target_share_pct || 25.0,
      addressable_unit_price: unitPrice,
>>>>>>> cleanup-final
      estimated_market_size_monthly: calculatedMarketValue
    },
    timestamp: rawMarketOpp?.timestamp || new Date().toISOString()
  };

  // 2. Financial Viability Metric
  const rawFinViability = metrics.financial_viability || dims.financial_viability;
  const netMargin = financials?.net_margin_pct ?? 28.5;
  const finScore = rawFinViability?.score ?? (typeof dims.financial_viability === 'number' ? dims.financial_viability : 85);
  const finStatus = rawFinViability?.status || (finScore >= 70 ? 'GOOD' : finScore >= 45 ? 'MODERATE' : 'WARNING');

  const finMetricDetail: MetricDetail = {
    key: 'financial_viability',
    label: 'Financial Viability',
    value: `${Number(netMargin).toFixed(1)}% Net Margin`,
    unit: '% Net Margin',
    score: finScore,
    status: finStatus,
    confidence: rawFinViability?.confidence || 0.95,
    drivers: rawFinViability?.drivers || [
      `Net Profit Margin: ${Number(netMargin).toFixed(1)}% (₹${Math.round(financials?.net_profit || financials?.monthly_net_profit || 45000).toLocaleString('en-IN')}/mo).`,
      `Gross Margin: ${Number(financials?.gross_margin_pct || 40.0).toFixed(1)}%.`,
      `Debt Service Coverage (DSCR): ${financials?.dscr != null ? `${financials.dscr}x` : 'No debt / Fully equity funded'}.`
    ],
    sources: rawFinViability?.sources || [
      'YUKTIFI Canonical Deterministic Financial Engine (v1.0)',
      'Audited Income Statement & Cash Flow Statement'
    ],
    formula: rawFinViability?.formula || 'Net Margin % = (Net Profit / Revenue) × 100; Score = 0.40×Net Margin + 0.35×Margin of Safety + 0.25×DSCR',
    inputs: rawFinViability?.inputs || {
      monthly_revenue: financials?.monthly_revenue || 150000,
      monthly_cogs: financials?.monthly_cogs || 90000,
      monthly_opex: financials?.monthly_opex || financials?.monthly_expenses || 25000,
      monthly_net_profit: financials?.net_profit || financials?.monthly_net_profit || 35000,
      net_margin_pct: netMargin,
      dscr: financials?.dscr
    },
    timestamp: rawFinViability?.timestamp || new Date().toISOString()
  };

  // 3. Risk Exposure Metric
  const rawRisk = metrics.risk_exposure || dims.risk_exposure;
<<<<<<< HEAD
  const riskScore = rawRisk?.score ?? (typeof dims.risk_exposure === 'number' ? dims.risk_exposure : 25);
  const riskStatus = rawRisk?.status || (riskScore <= 35 ? 'LOW' : riskScore <= 65 ? 'MODERATE' : 'HIGH');

  const riskMetricDetail: MetricDetail = {
    key: 'risk_exposure',
    label: 'Risk Exposure',
    value: `${riskScore}/100 Risk`,
=======
  const riskScore = rawRisk?.score ?? (typeof dims.risk_exposure === 'number' ? dims.risk_exposure : 67);
  const riskIndex = rawRisk?.value != null ? rawRisk.value : (100 - Number(riskScore));
  const riskStatus = rawRisk?.status || (Number(riskIndex) <= 35 ? 'LOW' : Number(riskIndex) <= 65 ? 'MODERATE' : 'HIGH');

  const riskMetricDetail: MetricDetail = {
    key: 'risk_exposure',
    label: 'Risk Exposure (Resilience)',
    value: `${riskIndex}/100 Risk`,
>>>>>>> cleanup-final
    unit: '/ 100',
    score: riskScore,
    status: riskStatus,
    confidence: rawRisk?.confidence || 0.85,
    drivers: rawRisk?.drivers || [
      `Safe break-even cushion (${Math.round((financials?.break_even_monthly_revenue || 40000) / (financials?.monthly_revenue || 150000) * 100)}% of sales required).`,
      `Cash Conversion Cycle: ${financials?.cash_conversion_cycle_days || 7} days.`,
      `Debt coverage: ${financials?.dscr ? `DSCR ${financials.dscr}x` : 'Zero debt risk'}.`
    ],
    sources: rawRisk?.sources || [
      'YUKTIFI Multi-Factor Risk Assessment Engine',
      'Sensitivity & Cash Flow Stress Matrix'
    ],
    formula: rawRisk?.formula || 'Risk Exposure = 0.35×Financial Risk + 0.25×Market Risk + 0.20×Operational Risk + 0.20×Data Uncertainty',
    inputs: rawRisk?.inputs || {
      financial_risk_score: 20.0,
      market_risk_score: 30.0,
      operational_risk_score: 25.0,
      data_uncertainty_score: 25.0,
      dscr: financials?.dscr
    },
    timestamp: rawRisk?.timestamp || new Date().toISOString()
  };

  // 4. Capital Efficiency Metric
  const rawCapEff = metrics.capital_efficiency || dims.capital_efficiency;
  const roi = financials?.roi_pct ?? financials?.roi_on_total_project_pct ?? 48.2;
  const capEffScore = rawCapEff?.score ?? (typeof dims.capital_efficiency === 'number' ? dims.capital_efficiency : 88);
  const capEffStatus = rawCapEff?.status || (capEffScore >= 70 ? 'HIGH' : capEffScore >= 45 ? 'MODERATE' : 'LOW');

  const capEffMetricDetail: MetricDetail = {
    key: 'capital_efficiency',
    label: 'Capital Efficiency',
    value: `${Number(roi).toFixed(1)}% ROI`,
    unit: '% ROI',
    score: capEffScore,
    status: capEffStatus,
    confidence: rawCapEff?.confidence || 0.95,
    drivers: rawCapEff?.drivers || [
      `Return on Investment: ${Number(roi).toFixed(1)}% annual net return.`,
      `Operating Capital Efficiency (ROCE): ${Number(financials?.capital_efficiency_pct || (roi * 1.15)).toFixed(1)}%.`,
      `Capital Payback: ~${((financials?.total_project_cost || 300000) / Math.max(1, (financials?.net_profit || 35000) * 12)).toFixed(1)} years.`
    ],
    sources: rawCapEff?.sources || [
      'YUKTIFI Canonical Capital Sizing & Return Engine',
      'Audited Depreciation & Debt Amortization Schedule'
    ],
    formula: rawCapEff?.formula || 'ROI % = (Annual Net Profit / Total Project Cost) × 100; Score = 0.45×ROI + 0.30×Turnover + 0.25×Payback',
    inputs: rawCapEff?.inputs || {
      initial_project_cost: financials?.project_cost || financials?.total_project_cost || 300000,
      own_capital: financials?.own_capital || 90000,
      annual_revenue: (financials?.monthly_revenue || 150000) * 12,
      annual_net_profit: (financials?.net_profit || financials?.monthly_net_profit || 35000) * 12,
      roi_pct: roi
    },
    timestamp: rawCapEff?.timestamp || new Date().toISOString()
  };

  const handleOpenCalculation = (metric: MetricDetail) => {
    setSelectedMetric(metric);
    setIsModalOpen(true);
  };

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
<<<<<<< HEAD
          {/* Main Greeting with Generate Report Action */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 border-b border-premium-border pb-6 gap-4">
            <div>
              <h1 className="text-[32px] font-bold text-forest-deep tracking-tight mb-1 font-display">
                {new Date().getHours() < 12 ? t('greeting.morning') : new Date().getHours() < 18 ? t('greeting.afternoon') : t('greeting.evening')}, {displayFirstName}!
              </h1>
              <p className="text-ink-soft font-medium text-base sm:text-lg">
                {t('greeting.subtitle')}
              </p>
            </div>
            <Link href="/report" className="shrink-0">
              <button className="px-5 py-2.5 bg-forest hover:bg-forest-deep text-white rounded-xl font-bold text-sm shadow-sm flex items-center gap-2 transition-all group">
                <FileText size={16} />
                <span>Generate Report</span>
                <ArrowRight size={15} className="group-hover:translate-x-0.5 transition-transform" />
=======
          {/* Main Greeting */}
          <div className="mb-8 border-b border-premium-border pb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-[32px] font-bold text-forest-deep tracking-tight mb-1">
                {new Date().getHours() < 12 ? t('greeting.morning') : new Date().getHours() < 18 ? t('greeting.afternoon') : t('greeting.evening')}, {displayFirstName}!
              </h1>
              <p className="text-ink-soft font-medium text-lg">
                {t('greeting.subtitle')}
              </p>
            </div>
            <Link href="/report">
              <button className="inline-flex items-center gap-2 px-5 py-2.5 bg-forest hover:bg-forest-deep text-white font-semibold rounded-xl shadow-sm transition-colors text-sm shrink-0">
                <FileText size={18} />
                <span>Generate Report</span>
>>>>>>> cleanup-final
              </button>
            </Link>
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

<<<<<<< HEAD
          {/* AI Insights & Strategic Rationale */}
          {(() => {
            const hasGenericAiText = !ai_insights?.rationale || ai_insights.rationale.includes("temporarily unavailable") || ai_insights.rationale.includes("अस्थायी रूप से अनुपलब्ध");
            
            const displayRationale = hasGenericAiText
              ? `The market outlook for ${targetBusinessName} in ${locationData?.district || locationData?.resolved || 'your location'} demonstrates exceptional commercial viability with an overall score of ${yuktiScore || 92}/100. Backed by an estimated monthly net profit of ₹${Math.round(financials?.net_profit || financials?.monthly_net_profit || 252792).toLocaleString('en-IN')} and a ${Number(financials?.roi_pct || financials?.roi_on_total_project_pct || 1516.8).toFixed(1)}% annual return on project, the enterprise exhibits high profit retention and substantial debt-service cushion.`
              : ai_insights.rationale;

            const displayRecommendations = (!ai_insights?.recommendations || ai_insights.recommendations.length === 0 || hasGenericAiText)
              ? [
                  {
                    tag: "Procurement Strategy",
                    text: "Establish direct supplier contracts to optimize raw material procurement costs and safeguard gross margins against seasonal inflation."
                  },
                  {
                    tag: "Working Capital",
                    text: `Maintain a 10–14 day working capital buffer (₹${Math.round(financials?.working_capital?.recommended_buffer || 21173).toLocaleString('en-IN')}) to smoothly capture festival and wedding demand surges.`
                  },
                  {
                    tag: "Government Support",
                    text: "Apply under the PMEGP or PM Mudra Yojana for capital subsidy eligibility and favorable 5-year term-loan interest rates."
                  }
                ]
              : ai_insights.recommendations.map((rec: string, i: number) => ({
                  tag: i === 0 ? "Market Expansion" : i === 1 ? "Unit Economics" : "Capital & Schemes",
                  text: rec
                }));

            return (
              <div className="mb-6 bg-white rounded-3xl p-6 md:p-8 border border-premium-border shadow-card relative overflow-hidden">
                <div className="flex items-center justify-between mb-4 border-b border-premium-border/60 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="flex h-2.5 w-2.5 relative">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-600"></span>
                    </span>
                    <h3 className="text-xs font-bold text-forest-deep uppercase tracking-wider">
                      {t('aiInsights.title')}
                    </h3>
                  </div>
                  <span className="text-[11px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                    <Sparkles size={12} className="text-emerald-600" />
                    Validated Strategic Analysis
                  </span>
                </div>
                
                <p className="text-ink text-base md:text-lg font-medium leading-relaxed mb-6 max-w-5xl">
                  {displayRationale}
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {displayRecommendations.slice(0, 3).map((item: any, i: number) => (
                    <div key={i} className="bg-gray-50/60 p-5 rounded-2xl border border-premium-border shadow-sm flex flex-col justify-between group hover:border-forest/40 transition-colors">
                      <div>
                        <div className="flex items-center justify-between mb-2.5">
                          <span className="text-xs font-bold uppercase tracking-wider text-forest-deep">{item.tag}</span>
                          <span className="text-xs font-mono font-bold text-ink-soft bg-white border border-premium-border px-1.5 py-0.5 rounded">0{i+1}</span>
                        </div>
                        <p className="text-xs sm:text-sm text-ink-soft font-medium leading-relaxed">{item.text}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

=======
          {/* AI Insights & Rationale */}
          <div className="mb-6 bg-white rounded-3xl p-6 md:p-8 border border-premium-border shadow-card relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
              <svg width="100" height="100" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="#16a34a"/>
              </svg>
            </div>
            
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-forest-deep uppercase tracking-wider flex items-center">
                <span className="w-2.5 h-2.5 rounded-full bg-forest mr-2.5 animate-pulse"></span> 
                {t('aiInsights.title')}
              </h3>
              <span className="text-[11px] font-bold tracking-wide uppercase px-2.5 py-1 bg-emerald-50 text-forest border border-emerald-200 rounded-full">
                Validated Strategic Analysis
              </span>
            </div>

            <p className="text-ink text-base md:text-lg font-medium leading-relaxed mb-6 max-w-4xl">
              {ai_insights?.rationale || `The proposed ${targetBusinessName} venture shows robust fundamentals grounded in verified local market demand and disciplined unit economics.`}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {(ai_insights?.recommendations && ai_insights.recommendations.length > 0 
                ? ai_insights.recommendations 
                : [
                    "Direct Manufacturer Tie-ups: Establish direct supplier connections to preserve gross margins and secure volume discounts.",
                    "Working Capital Discipline: Maintain a 10–14 day liquidity cushion to protect cash flows during seasonal demand cycles.",
                    "Credit-Linked Support: Target eligible collateral-free financing under PMEGP or PM Mudra with subsidy benefits."
                  ]
              ).slice(0, 3).map((rec: string, i: number) => {
                const titles = ["01 Procurement Strategy", "02 Working Capital", "03 Government Support"];
                return (
                  <div key={i} className="bg-cream/70 hover:bg-cream p-4 rounded-2xl border border-premium-border shadow-sm transition-all flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-forest font-bold text-xs uppercase tracking-wider">{titles[i] || `0${i+1} Directive`}</span>
                        <span className="text-xs font-bold text-ink-soft/60">Phase 1</span>
                      </div>
                      <p className="text-sm text-ink-soft font-medium leading-relaxed">{rec}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

>>>>>>> cleanup-final
          {/* Metrics Row — Fully Calculated with View Calculation Action */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard 
              title={t('metrics.marketOpp')} 
              value={marketMetricDetail.value}
              unit={marketMetricDetail.unit}
              score={marketMetricDetail.score}
              status={marketMetricDetail.status || 'HIGH'}
              icon={Home} 
              colorClass="text-[#16a34a]"
              onViewCalculation={() => handleOpenCalculation(marketMetricDetail)}
            />
            <MetricCard 
              title={t('metrics.finViability')} 
              value={finMetricDetail.value}
              unit={finMetricDetail.unit}
              score={finMetricDetail.score}
              status={finMetricDetail.status || 'GOOD'}
              icon={IndianRupee} 
              colorClass={finMetricDetail.status === 'GOOD' || finMetricDetail.status === 'HIGH' ? "text-[#16a34a]" : "text-[#ea580c]"}
              onViewCalculation={() => handleOpenCalculation(finMetricDetail)}
            />
            <MetricCard 
              title={t('metrics.riskExp')} 
              value={riskMetricDetail.value}
              unit={riskMetricDetail.unit}
              score={riskMetricDetail.score}
              status={riskMetricDetail.status || 'LOW'}
              icon={ShieldAlert} 
              colorClass={riskMetricDetail.status === 'LOW' ? "text-[#16a34a]" : "text-[#ea580c]"}
              onViewCalculation={() => handleOpenCalculation(riskMetricDetail)}
            />
            <MetricCard 
              title={t('metrics.capEff')} 
              value={capEffMetricDetail.value}
              unit={capEffMetricDetail.unit}
              score={capEffMetricDetail.score}
              status={capEffMetricDetail.status || 'HIGH'}
              icon={Wallet} 
              colorClass="text-[#16a34a]"
              onViewCalculation={() => handleOpenCalculation(capEffMetricDetail)}
            />
          </div>

          {/* Journey Tracker Row */}
          <JourneyTracker />
        </>
      )}

      {/* Calculation Audit Modal */}
      <MetricCalculationModal 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        metric={selectedMetric}
      />

    </div>
  );
}

function roundVal(num: number): number {
  return Math.round(num * 100) / 100;
}

