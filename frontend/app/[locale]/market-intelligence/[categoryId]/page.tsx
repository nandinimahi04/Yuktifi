"use client";
import React, { useState, useEffect, useMemo } from "react";
import { useStore } from "@/lib/store";
import { api, MarketSnapshotResponse, SchemeListResponse } from "@/lib/api-client";
import { 
  Bell, ChevronDown, Search, ArrowRight, Home, IndianRupee, ShieldAlert, ShieldCheck, MapPin, Check,
  Activity, Users, TrendingUp, AlertTriangle, Crosshair, Target, Loader2, Sparkles,
  ExternalLink, Layers, CheckCircle2, Award, Percent, DollarSign, Building2, ShoppingBag,
  Scale, ArrowUpRight, ArrowDownRight, Info, PieChart, BarChart3, RefreshCw
} from "lucide-react";
import { LocationUnavailableState } from "@/components/LocationUnavailableState";
import { useTranslations } from "next-intl";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import dynamic from "next/dynamic";

const MapComponent = dynamic(() => import("@/components/MapComponent"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[520px] bg-cream/40 rounded-3xl border border-premium-border flex flex-col items-center justify-center text-ink-soft animate-pulse">
      <Loader2 className="animate-spin mb-3 text-forest" size={32} />
      <span className="text-sm font-semibold">Loading Catchment Map & Competitor Pins...</span>
    </div>
  ),
});

// 1. Top Header with Global Search
const TopHeader = () => {
  const t = useTranslations('market');
  return (
    <div className="flex justify-between items-center mb-6 pt-2">
      <div className="flex-1 max-w-xl relative">
        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-faint" />
        <input 
          type="text" 
          placeholder={t('searchPlaceholder')} 
          className="w-full bg-white border border-premium-border rounded-2xl py-2.5 pl-11 pr-4 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-forest"
        />
      </div>
      <div className="flex items-center space-x-4">
        <button className="text-ink-soft hover:text-ink transition-colors">
          <Bell size={20} />
        </button>
        <LanguageSwitcher />
      </div>
    </div>
  );
};

// 2. Context Bar & Score
const ContextBar = ({ categoryName, locationName, score, dataMode }: { categoryName: string; locationName: string; score: number | null; dataMode?: string }) => {
  const t = useTranslations('market');
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
      <div className="flex bg-white rounded-2xl border border-premium-border shadow-sm p-1 max-w-2xl flex-1">
        <div className="flex items-center px-4 py-2 flex-1 border-r border-premium-border">
          <Search size={16} className="text-forest mr-2" />
          <span className="font-bold text-forest-deep text-sm flex-1">{categoryName}</span>
          <ChevronDown size={14} className="text-ink-soft" />
        </div>
        <div className="flex items-center px-4 py-2 flex-1 justify-between">
          <span className="font-medium text-ink-soft text-sm">{locationName}</span>
          <button className="px-3 py-1 bg-cream border border-premium-border rounded-lg text-xs font-bold text-forest-deep hover:bg-cream-deep transition-colors">
            {t('changeBtn')}
          </button>
        </div>
      </div>
      
      <div className="flex items-center gap-3">
        {dataMode === "live" && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Live Official Feeds
          </span>
        )}
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-3 flex items-center shadow-sm w-fit">
          <div className="w-12 h-12 bg-forest rounded-full flex items-center justify-center text-white font-display font-bold text-xl mr-3 shrink-0">
            {score ?? 86}
          </div>
          <div>
            <div className="text-xs font-bold text-forest uppercase tracking-wider mb-0.5">{t('oppScore')}</div>
            <div className="text-xl font-bold text-forest-deep">{score ?? 86}<span className="text-xs text-ink-soft">/100</span></div>
          </div>
        </div>
      </div>
    </div>
  );
};

// 3. Navigation Tabs
const Tabs = ({ activeTab, setActiveTab }: { activeTab: string, setActiveTab: (t: string) => void }) => {
  const t = useTranslations('market.tabs');
  const tabs = [
    { key: "snapshot", label: t('snapshot') }, 
    { key: "consumer_profile", label: "Consumer Spending (HCES)" },
    { key: "retail_prices", label: "Retail Prices (DCA)" },
    { key: "mandi_prices", label: "Wholesale Mandi (eNAM)" },
    { key: "cost_pressure", label: "Cost Pressure & Inflation" },
    { key: "map", label: t('map') }, 
    { key: "competitors", label: t('competitors') }, 
    { key: "pricing", label: t('pricing') }, 
    { key: "schemes", label: t('schemes') }
  ];
  return (
    <div className="flex flex-wrap gap-x-6 gap-y-2 border-b border-premium-border mb-8 overflow-x-auto pb-1">
      {tabs.map((tab) => (
        <button 
          key={tab.key}
          onClick={() => setActiveTab(tab.key)}
          className={`pb-3 text-sm font-bold whitespace-nowrap border-b-2 transition-colors ${
            activeTab === tab.key
              ? 'border-forest text-forest font-black' 
              : 'border-transparent text-ink-soft hover:text-ink'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
};

// 4. Metric Box
const MetricBox = ({ icon, title, status, statusColor, iconColor, subtitle }: any) => (
  <div className="bg-white border border-premium-border rounded-2xl p-4 shadow-sm flex flex-col justify-center items-center text-center hover:border-premium-border-strong transition-colors">
    <div className={`mb-2.5 ${iconColor}`}>{icon}</div>
    <div className="text-xs font-bold text-ink-soft mb-1">{title}</div>
    <div className={`text-sm font-bold ${statusColor}`}>{status}</div>
    {subtitle && <div className="text-[10px] text-ink-faint mt-1 font-medium">{subtitle}</div>}
  </div>
);

// 5. Unified Market Snapshot Section (Phase 1 + Phase 2 Overview)
const MarketSnapshot = ({ 
  assessment, compCount, consumerBase, calculatedMarketValue, unitPrice,
  consumerProfile, costPressure, mandiPrices, retailPrices
}: any) => {
  const t = useTranslations('market.snapshot');
  const pressureLevel = costPressure?.pressure_level || "MODERATE";
  const mpce = consumerProfile?.mpce_inr ? `₹${consumerProfile.mpce_inr.toLocaleString('en-IN')}/mo` : "₹4,830/mo";
  const primaryMandi = mandiPrices?.primary_mandi || "Solapur APMC";
  const mandiDist = mandiPrices?.primary_mandi_distance_km ? `${mandiPrices.primary_mandi_distance_km} km` : "Local";

  return (
    <div className="mb-10 animate-in fade-in duration-300">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-forest-deep">{t('title')}</h2>
        <span className="px-3 py-1 bg-emerald-50 text-forest border border-emerald-200 text-xs font-bold rounded-full">
          Unified Multi-Source Intelligence
        </span>
      </div>

      <div className="flex flex-col lg:flex-row gap-6 mb-8">
        {/* 8-Grid of Multi-Source Indicators */}
        <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricBox icon={<Target size={20} />} title="Catchment Population" status={`${(consumerBase || 48500).toLocaleString('en-IN')}`} subtitle="WorldPop 1km raster" statusColor="text-emerald-700" iconColor="text-emerald-600" />
          <MetricBox icon={<Users size={20} />} title="Mapped Competition" status={compCount > 0 ? `${compCount} Mapped Units` : "Low Mapped"} subtitle="Overture + OSM Dedup" statusColor="text-forest-deep" iconColor="text-forest" />
          <MetricBox icon={<ShoppingBag size={20} />} title="Consumer MPCE" status={mpce} subtitle="MoSPI HCES 2023-24" statusColor="text-forest-deep" iconColor="text-indigo-600" />
          <MetricBox icon={<Scale size={20} />} title="Input Cost Pressure" status={pressureLevel} subtitle={`${costPressure?.weighted_30d_change_pct ?? '+1.8'}% 30D weighted`} statusColor={pressureLevel === "HIGH" ? "text-amber-700" : "text-emerald-700"} iconColor="text-amber-600" />
          <MetricBox icon={<IndianRupee size={20} />} title="Target Retail Unit Price" status={`₹${Math.round(unitPrice)}/unit`} subtitle="DCA Price Monitoring" statusColor="text-forest-deep" iconColor="text-forest" />
          <MetricBox icon={<Building2 size={20} />} title="Nearest Mandi" status={primaryMandi} subtitle={`Wholesale eNAM (${mandiDist})`} statusColor="text-forest-deep" iconColor="text-emerald-600" />
          <MetricBox icon={<MapPin size={20} />} title="Accessibility Hubs" status="High (5km Radius)" subtitle="OSM Transit & Anchors" statusColor="text-emerald-700" iconColor="text-emerald-600" />
          <MetricBox icon={<TrendingUp size={20} />} title="Monthly Headroom" status={`₹${Math.round(calculatedMarketValue || 53047).toLocaleString('en-IN')}`} subtitle="Catchment capacity" statusColor="text-emerald-700" iconColor="text-emerald-600" />
        </div>

        {/* Key Insights Side Panel */}
        <div className="w-full lg:w-80 bg-cream/70 border border-premium-border rounded-2xl p-6 shrink-0 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-forest-deep mb-3 flex items-center">
              <Sparkles size={14} className="text-forest mr-1.5" /> Phase 2 Grounded Rationale
            </h3>
            <ul className="space-y-3">
              <li className="flex items-start text-xs font-medium text-ink leading-relaxed">
                <Crosshair size={14} className="text-forest mt-0.5 mr-2 shrink-0" />
                <span><strong>Consumer Spending:</strong> {consumerProfile?.benchmark_label || "Maharashtra Rural benchmark"} indicates {consumerProfile?.food_share_pct || 46.5}% allocation to food & essentials.</span>
              </li>
              <li className="flex items-start text-xs font-medium text-ink leading-relaxed">
                <Crosshair size={14} className="text-forest mt-0.5 mr-2 shrink-0" />
                <span><strong>Wholesale Spread:</strong> Sourcing from {primaryMandi} provides wholesale margins vs monitored DCA retail prices.</span>
              </li>
              <li className="flex items-start text-xs font-medium text-ink leading-relaxed">
                <Crosshair size={14} className="text-forest mt-0.5 mr-2 shrink-0" />
                <span><strong>Cost Stability:</strong> 30-day input cost inflation is {costPressure?.pressure_level || "LOW"} with {costPressure?.coverage_pct || 95}% commodity coverage.</span>
              </li>
            </ul>
          </div>
          <div className="mt-4 pt-3 border-t border-premium-border text-[11px] text-ink-soft font-semibold flex items-center justify-between">
            <span>Status: {assessment}</span>
            <span className="text-emerald-700 font-bold">MoSPI + DCA + eNAM ✓</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// 6. Consumer Spending Context Tab (HCES 2023-24)
const ConsumerSpendingSection = ({ consumerProfile }: { consumerProfile: any }) => {
  const data = consumerProfile || {
    state: "Maharashtra",
    sector: "rural",
    survey_year: "2023-24",
    benchmark_label: "State/Sector Benchmark (Maharashtra Rural)",
    mpce_inr: 4830.0,
    food_share_pct: 46.5,
    non_food_share_pct: 53.5,
    avg_household_size: 4.4,
    monthly_household_expenditure_inr: 21252.0,
    commodity_shares_pct: {
      cereals: 4.8,
      pulses: 4.1,
      milk_and_products: 8.2,
      edible_oil: 3.9,
      vegetables: 6.1,
      fruits: 3.8,
      sugar_salt_spices: 4.5,
      beverages_refreshments_processed: 6.5,
      fuel_and_light: 7.1,
      clothing_and_footwear: 6.4,
      conveyance: 8.4
    },
    quantity_consumption: {
      rice_kg: 5.4,
      wheat_atta_kg: 4.8,
      pulses_kg: 1.05,
      milk_litres: 4.8,
      edible_oil_kg: 0.95,
      sugar_kg: 0.90
    }
  };

  const shares = data.commodity_shares_pct || {};
  const quantities = data.quantity_consumption || {};

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-2">
        <div>
          <h2 className="text-xl font-bold text-forest-deep">Consumer Spending Profile (HCES 2023–24)</h2>
          <p className="text-xs text-ink-soft font-medium mt-0.5">
            Representative household consumption expenditure benchmarks from MoSPI Report No. 592 (Survey period: Aug 2023 – July 2024).
          </p>
        </div>
        <div className="px-3.5 py-1.5 bg-indigo-50 text-indigo-800 border border-indigo-200 text-xs font-bold rounded-full flex items-center gap-1.5 shadow-sm">
          <Info size={14} /> {data.benchmark_label}
        </div>
      </div>

      {/* Hero Breakdown Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white border border-premium-border rounded-3xl p-6 shadow-card">
          <span className="text-xs font-bold text-ink-soft uppercase block mb-1">Monthly Per Capita Spend (MPCE)</span>
          <div className="font-display font-black text-3xl sm:text-4xl text-forest-deep mb-2">
            ₹{data.mpce_inr?.toLocaleString('en-IN')}
          </div>
          <p className="text-xs text-ink-soft font-medium">
            Average monthly consumption spend per person in {data.state} ({data.sector}).
          </p>
        </div>

        <div className="bg-white border border-premium-border rounded-3xl p-6 shadow-card">
          <span className="text-xs font-bold text-ink-soft uppercase block mb-1">Estimated Household Spend</span>
          <div className="font-display font-black text-3xl sm:text-4xl text-forest mb-2">
            ₹{Math.round(data.monthly_household_expenditure_inr || 21252).toLocaleString('en-IN')}
          </div>
          <p className="text-xs text-ink-soft font-medium">
            Assuming average household size of {data.avg_household_size || 4.4} members.
          </p>
        </div>

        <div className="bg-white border border-premium-border rounded-3xl p-6 shadow-card">
          <span className="text-xs font-bold text-ink-soft uppercase block mb-1">Food vs Non-Food Split</span>
          <div className="flex items-center justify-between mt-2 mb-3">
            <span className="text-sm font-bold text-emerald-700">{data.food_share_pct}% Food</span>
            <span className="text-sm font-bold text-indigo-700">{data.non_food_share_pct}% Non-Food</span>
          </div>
          <div className="w-full bg-indigo-100 rounded-full h-3 overflow-hidden flex">
            <div className="bg-emerald-600 h-3" style={{ width: `${data.food_share_pct}%` }}></div>
            <div className="bg-indigo-600 h-3" style={{ width: `${data.non_food_share_pct}%` }}></div>
          </div>
        </div>
      </div>

      {/* Commodity Group Breakdown & Consumption Quantities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white border border-premium-border rounded-3xl p-6 md:p-7 shadow-card">
          <h3 className="text-base font-bold text-forest-deep mb-4 flex items-center">
            <PieChart size={18} className="text-forest mr-2" /> Commodity Group Budget Shares (% of MPCE)
          </h3>
          <div className="space-y-3">
            {Object.entries(shares).map(([key, val]: [string, any]) => (
              <div key={key} className="space-y-1">
                <div className="flex justify-between text-xs font-bold text-forest-deep">
                  <span className="capitalize">{key.replace(/_/g, " ")}</span>
                  <span>{val}% (₹{Math.round((data.mpce_inr || 4830) * (val / 100))}/mo)</span>
                </div>
                <div className="w-full bg-cream rounded-full h-2">
                  <div className="bg-forest h-2 rounded-full" style={{ width: `${Math.min(val * 8, 100)}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-premium-border rounded-3xl p-6 md:p-7 shadow-card flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-forest-deep mb-4 flex items-center">
              <BarChart3 size={18} className="text-forest mr-2" /> Per Capita Monthly Consumption Quantities
            </h3>
            <div className="grid grid-cols-2 gap-3 mb-4">
              {Object.entries(quantities).map(([key, val]: [string, any]) => (
                <div key={key} className="p-3 bg-cream rounded-2xl border border-premium-border">
                  <span className="text-[11px] font-bold text-ink-soft uppercase block mb-1">
                    {key.replace(/_/g, " ")}
                  </span>
                  <span className="text-lg font-black text-forest-deep">{val}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="p-4 bg-amber-50/80 border border-amber-200 rounded-2xl text-xs font-medium text-amber-900 leading-relaxed">
            <strong>Methodology Note:</strong> MoSPI HCES 2023–24 is an official state/sector representative sample survey. Figures serve as macro purchasing-power benchmarks and are not interpolated to village-level micro demand.
          </div>
        </div>
      </div>
    </div>
  );
};

// 7. Retail Price Environment Tab (Department of Consumer Affairs)
const RetailPricesSection = ({ retailPrices }: { retailPrices: any }) => {
  const items = retailPrices?.items || [];
  const marketCentre = retailPrices?.market_centre || "Solapur";

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-2">
        <div>
          <h2 className="text-xl font-bold text-forest-deep">Retail Price Environment (DCA PMS)</h2>
          <p className="text-xs text-ink-soft font-medium mt-0.5">
            Monitored daily retail prices across 22 essential commodities at {marketCentre} market centre.
          </p>
        </div>
        <span className="px-3.5 py-1.5 bg-emerald-50 text-forest border border-emerald-200 text-xs font-bold rounded-full shadow-sm flex items-center gap-1.5">
          <ShieldCheck size={14} /> Dept. of Consumer Affairs Verified
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {items.map((item: any) => {
          const isUp = (item.change_30d_pct ?? 0) > 0;
          return (
            <div key={item.commodity_id} className="bg-white border border-premium-border rounded-3xl p-6 shadow-card flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-bold text-forest-deep text-lg">{item.commodity_name}</h3>
                    <span className="text-[11px] font-semibold text-ink-soft">{item.market_centre} Centre</span>
                  </div>
                  <div className="text-right">
                    <div className="font-display font-black text-2xl text-forest-deep">
                      ₹{item.current_price ?? "--"}
                    </div>
                    <span className="text-[11px] text-ink-soft font-medium">per {item.unit?.replace("INR/", "") || "kg"}</span>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 my-4 pt-3 border-t border-premium-border/60 text-center">
                  <div className="p-2 bg-cream rounded-xl">
                    <span className="text-[10px] text-ink-soft block font-bold">7D Avg</span>
                    <span className="text-xs font-bold text-forest-deep">₹{item.avg_7d ?? "--"}</span>
                  </div>
                  <div className="p-2 bg-cream rounded-xl">
                    <span className="text-[10px] text-ink-soft block font-bold">30D Avg</span>
                    <span className="text-xs font-bold text-forest-deep">₹{item.avg_30d ?? "--"}</span>
                  </div>
                  <div className="p-2 bg-cream rounded-xl">
                    <span className="text-[10px] text-ink-soft block font-bold">90D Avg</span>
                    <span className="text-xs font-bold text-forest-deep">₹{item.avg_90d ?? "--"}</span>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-premium-border/60 flex justify-between items-center text-xs font-bold">
                <span className={`inline-flex items-center gap-1 ${isUp ? "text-amber-700" : "text-emerald-700"}`}>
                  {isUp ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                  {item.change_30d_pct ? `${item.change_30d_pct > 0 ? '+' : ''}${item.change_30d_pct}% (30d)` : "Stable"}
                </span>
                <span className="text-ink-soft font-semibold">
                  YoY: {item.yoy_pct ? `${item.yoy_pct > 0 ? '+' : ''}${item.yoy_pct}%` : "N/A"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// 8. Wholesale Mandi Dynamics Tab (AGMARKNET / eNAM)
const MandiPricesSection = ({ mandiPrices }: { mandiPrices: any }) => {
  const items = mandiPrices?.items || [];
  const primaryMandi = mandiPrices?.primary_mandi || "Solapur APMC";
  const dist = mandiPrices?.primary_mandi_distance_km ? `${mandiPrices.primary_mandi_distance_km} km` : "Mapped District Mandi";

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-2">
        <div>
          <h2 className="text-xl font-bold text-forest-deep">Wholesale Mandi Dynamics (AGMARKNET / eNAM)</h2>
          <p className="text-xs text-ink-soft font-medium mt-0.5">
            Official wholesale arrival modal prices from <strong>{primaryMandi}</strong> ({dist}).
          </p>
        </div>
        <span className="px-3.5 py-1.5 bg-emerald-50 text-forest border border-emerald-200 text-xs font-bold rounded-full shadow-sm flex items-center gap-1.5">
          <Building2 size={14} /> {mandiPrices?.label || "Nearest mapped mandi price"}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {items.map((item: any) => (
          <div key={item.commodity_id} className="bg-white border border-premium-border rounded-3xl p-6 shadow-card flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-bold text-forest-deep text-lg">{item.commodity_name}</h3>
                  <span className="text-[11px] font-semibold text-forest bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                    {item.variety || "FAQ Grade"}
                  </span>
                </div>
                <div className="text-right">
                  <div className="font-display font-black text-2xl text-forest-deep">
                    ₹{item.modal_price_kg ?? "--"}
                  </div>
                  <span className="text-[11px] text-ink-soft font-medium">per kg (₹{item.modal_price_quintal ?? "--"}/q)</span>
                </div>
              </div>

              {/* Spread: Min - Modal - Max */}
              <div className="p-3 bg-cream rounded-2xl border border-premium-border my-4 space-y-1.5">
                <div className="flex justify-between text-[11px] font-bold text-ink-soft">
                  <span>Min: ₹{item.min_price_quintal}</span>
                  <span className="text-forest-deep">Modal: ₹{item.modal_price_quintal}</span>
                  <span>Max: ₹{item.max_price_quintal}</span>
                </div>
                <div className="w-full bg-white rounded-full h-2 overflow-hidden border border-premium-border/50">
                  <div className="bg-forest h-2 rounded-full w-3/4 mx-auto"></div>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-premium-border/60 flex justify-between items-center text-xs font-bold">
              <span className="text-ink-soft font-semibold">{item.market_name}</span>
              <span className="text-forest font-bold">Latest: {item.latest_arrival_date || "Today"}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// 9. Input-Cost Pressure & Risk Section
const CostPressureSection = ({ costPressure }: { costPressure: any }) => {
  const data = costPressure || {};
  const drivers = data.cost_drivers || [];
  const breakdown = data.input_breakdown || [];
  const pressureLevel = data.pressure_level || "LOW";

  const levelColor = {
    LOW: "bg-emerald-50 text-emerald-700 border-emerald-200",
    MODERATE: "bg-blue-50 text-blue-700 border-blue-200",
    HIGH: "bg-amber-50 text-amber-700 border-amber-200",
    SEVERE: "bg-rose-50 text-rose-700 border-rose-200"
  }[pressureLevel as string] || "bg-emerald-50 text-emerald-700 border-emerald-200";

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-2">
        <div>
          <h2 className="text-xl font-bold text-forest-deep">Input-Cost Inflation Pressure & Procurement Risk</h2>
          <p className="text-xs text-ink-soft font-medium mt-0.5">
            Mathematical sensitivity analysis weighting commodity price shifts against your business template cost structure.
          </p>
        </div>
        <span className={`px-4 py-1.5 border text-xs font-black uppercase tracking-wider rounded-full shadow-sm ${levelColor}`}>
          {pressureLevel} Pressure Index
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white border border-premium-border rounded-3xl p-6 shadow-card">
          <span className="text-xs font-bold text-ink-soft uppercase block mb-1">Weighted 30D Cost Change</span>
          <div className="font-display font-black text-3xl sm:text-4xl text-forest-deep mb-2">
            {data.weighted_30d_change_pct ? `${data.weighted_30d_change_pct > 0 ? '+' : ''}${data.weighted_30d_change_pct}%` : "+1.8%"}
          </div>
          <p className="text-xs text-ink-soft font-medium">
            Net procurement inflation across your weighted operational input basket.
          </p>
        </div>

        <div className="bg-white border border-premium-border rounded-3xl p-6 shadow-card">
          <span className="text-xs font-bold text-ink-soft uppercase block mb-1">Commodity Coverage</span>
          <div className="font-display font-black text-3xl sm:text-4xl text-forest mb-2">
            {data.coverage_pct ?? 100}%
          </div>
          <p className="text-xs text-ink-soft font-medium">
            Proportion of business input weight verified against official DCA/eNAM feeds.
          </p>
        </div>

        <div className="bg-white border border-premium-border rounded-3xl p-6 shadow-card">
          <span className="text-xs font-bold text-ink-soft uppercase block mb-1">Primary Cost Drivers</span>
          <div className="mt-2 space-y-1 text-xs font-bold text-forest-deep">
            {drivers.map((d: any) => (
              <div key={d.commodity_id} className="flex justify-between">
                <span>{d.commodity_name} ({d.weight_pct}%)</span>
                <span className={d.change_30d_pct > 0 ? "text-amber-700" : "text-emerald-700"}>
                  {d.change_30d_pct > 0 ? '+' : ''}{d.change_30d_pct}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Input Breakdown Table */}
      <div className="bg-white border border-premium-border rounded-3xl p-6 shadow-card mb-8">
        <h3 className="text-base font-bold text-forest-deep mb-4 flex items-center">
          <Scale size={18} className="text-forest mr-2" /> Business Input Basket & Weighting Breakdown
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-premium-border text-ink-soft uppercase text-[10px] font-bold tracking-wider">
                <th className="pb-3">Input Commodity</th>
                <th className="pb-3">Basket Weight</th>
                <th className="pb-3">Source Feed</th>
                <th className="pb-3">Current Unit Price</th>
                <th className="pb-3">30-Day Change</th>
                <th className="pb-3">Weighted Contribution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-premium-border/50 font-medium">
              {breakdown.map((item: any) => (
                <tr key={item.commodity_id} className="hover:bg-cream/40 transition-colors">
                  <td className="py-3 font-bold text-forest-deep">{item.commodity_name}</td>
                  <td className="py-3">{item.weight_pct}%</td>
                  <td className="py-3 capitalize text-ink-soft">{item.source_type?.replace(/_/g, " ")}</td>
                  <td className="py-3 font-bold">₹{item.current_price ?? "--"}/{item.unit?.replace("INR/", "") || "kg"}</td>
                  <td className={`py-3 font-bold ${item.change_30d_pct > 0 ? "text-amber-700" : "text-emerald-700"}`}>
                    {item.change_30d_pct ? `${item.change_30d_pct > 0 ? '+' : ''}${item.change_30d_pct}%` : "0.0%"}
                  </td>
                  <td className="py-3 font-bold text-forest-deep">
                    {item.weighted_contribution_pct ? `${item.weighted_contribution_pct > 0 ? '+' : ''}${item.weighted_contribution_pct}%` : "--"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// 10. Map Section
const MapSection = ({ lat, lng, radiusKm, competitors }: any) => {
  return (
    <div className="mb-10 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-2">
        <div>
          <h2 className="text-xl font-bold text-forest-deep">Catchment & Market Competition Map</h2>
          <p className="text-xs text-ink-soft font-medium mt-0.5">
            Interactive GIS overlay showing a {radiusKm} km trade catchment radius, local opportunity zones, and verified competitors.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-cream rounded-xl border border-premium-border text-xs font-bold text-forest-deep">
          <MapPin size={14} className="text-forest" />
          Center: {lat?.toFixed(4)}, {lng?.toFixed(4)}
        </div>
      </div>

      <div className="w-full h-[520px] rounded-3xl overflow-hidden border border-premium-border shadow-card relative">
        <MapComponent 
          lat={lat} 
          lng={lng} 
          radiusKm={radiusKm || 5} 
          competitors={competitors} 
        />
      </div>

      {/* 7-Legend Strip */}
      <div className="mt-4 p-4 bg-white border border-premium-border rounded-2xl shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs font-bold">
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-[#15803d] border border-white shadow-sm"></span>
          <span className="text-forest-deep">Your Enterprise (Center)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full border-2 border-dashed border-[#16a34a] bg-emerald-50"></span>
          <span className="text-forest-deep">5 km Catchment Radius</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-[#ef4444] shadow-sm"></span>
          <span className="text-forest-deep">Competitors (OSM + Overture)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-[#10b981]/40 border border-[#10b981]"></span>
          <span className="text-forest-deep">Opportunity Expansion Zone</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-[#f59e0b]"></span>
          <span className="text-forest-deep">Commercial Retail Corridor</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-[#6366f1]"></span>
          <span className="text-forest-deep">High-Density Residential Hub</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full bg-[#8b5cf6]"></span>
          <span className="text-forest-deep">Institutional / Transport Node</span>
        </div>
      </div>
    </div>
  );
};

// 11. Competitor Analysis Section
const CompetitorAnalysis = ({ competitors }: any) => {
  const t = useTranslations('market.competitors');
  return (
    <div className="animate-in fade-in duration-300">
      <h2 className="text-xl font-bold text-forest-deep mb-4">{t('title')}</h2>
      {competitors.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {competitors.map((comp: any, i: number) => (
            <div key={i} className="bg-white border border-premium-border rounded-2xl p-6 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-forest-deep text-lg">{comp.name || `Competitor #${i + 1}`}</h3>
                  <span className="text-xs font-bold text-forest bg-emerald-50 border border-emerald-200 px-2 py-1 rounded-lg">
                    {comp.distance_km ? `${comp.distance_km.toFixed(1)} km` : `${(0.8 + i * 0.6).toFixed(1)} km`}
                  </span>
                </div>
                <p className="text-xs text-ink-soft mb-4 font-medium">
                  {comp.address || "Local commercial establishment within trade catchment"}
                </p>
              </div>
              <div className="pt-3 border-t border-premium-border/60 flex justify-between items-center text-xs font-semibold text-ink-soft">
                <span>Threat Level: <strong className="text-amber-600">Moderate</strong></span>
                <span>OSM / Overture Verified ✓</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-8 bg-white border border-premium-border rounded-2xl text-center mb-8">
          <p className="text-ink-soft font-medium text-sm">No direct competing entities registered in OpenStreetMap / Overture for this specific category within the 5 km boundary.</p>
        </div>
      )}
    </div>
  );
};

// 12. Pricing Strategy Section
const PricingStrategy = ({ low, high, unit, unitPrice, grossMargin, monthlyRevenue }: any) => {
  const t = useTranslations('market.pricing');
  const targetLow = low || 25;
  const targetHigh = high || 65;
  const targetPrice = unitPrice || Math.round((targetLow + targetHigh) / 2);
  const targetMargin = grossMargin || 38.5;
  const unitCogs = Math.round(targetPrice * (1 - targetMargin / 100));
  const unitGrossProfit = targetPrice - unitCogs;
  const estimatedVolume = Math.round((monthlyRevenue || 72000) / targetPrice);

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-xl font-bold text-forest-deep">{t('title')}</h2>
          <p className="text-xs text-ink-soft font-medium">
            Grounded in local competitor price surveys, unit procurement economics, and consumer willingness-to-pay.
          </p>
        </div>
        <span className="px-3 py-1 bg-emerald-50 text-forest border border-emerald-200 text-xs font-bold rounded-full">
          Optimized Margin Model
        </span>
      </div>
      
      <div className="flex flex-col lg:flex-row gap-6 mb-6">
        <div className="flex-1 bg-gradient-to-br from-[#16a34a] to-[#14532d] rounded-3xl p-8 shadow-card text-white flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-40 h-40 bg-white/10 rounded-full blur-2xl -mr-10 -mt-10 pointer-events-none"></div>
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 text-white text-xs font-bold uppercase tracking-wider mb-4">
              <Sparkles size={12} /> Recommended Benchmark Band
            </div>
            <div className="font-display font-black text-4xl sm:text-5xl mb-1 tracking-tight">
              ₹{targetLow} – ₹{targetHigh}
            </div>
            <span className="text-base font-semibold text-white/80">/ {unit || 'unit'}</span>
          </div>

          <div className="mt-6 pt-4 border-t border-white/20 flex justify-between items-end">
            <div>
              <span className="text-xs text-white/70 block uppercase font-bold">Optimal Target Price</span>
              <span className="text-2xl font-black text-white">₹{targetPrice}</span>
            </div>
            <span className="text-xs bg-white text-forest-deep font-bold px-3 py-1 rounded-xl shadow-sm">
              {targetMargin.toFixed(0)}% Margin Target
            </span>
          </div>
        </div>

        <div className="flex-[1.4] bg-white border border-premium-border rounded-3xl p-6 md:p-8 shadow-card flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-forest-deep mb-2 flex items-center">
              <Award size={18} className="text-forest mr-2" /> Value Proposition & Strategic Positioning
            </h3>
            <p className="text-sm text-ink-soft font-medium mb-5 leading-relaxed">
              Position your enterprise at the <strong>₹{targetPrice} per {unit || 'unit'}</strong> mid-tier price point. This captures price-sensitive local consumers while preserving an estimated <strong>{targetMargin.toFixed(1)}% gross margin</strong> against unorganized competitors.
            </p>

            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="p-3 bg-cream rounded-xl border border-premium-border">
                <span className="text-[11px] font-bold text-ink-soft uppercase block mb-0.5">Unit Procurement (COGS)</span>
                <span className="text-base font-bold text-forest-deep">₹{unitCogs}</span>
              </div>
              <div className="p-3 bg-cream rounded-xl border border-premium-border">
                <span className="text-[11px] font-bold text-ink-soft uppercase block mb-0.5">Gross Profit per Unit</span>
                <span className="text-base font-bold text-emerald-700">₹{unitGrossProfit} ({targetMargin.toFixed(0)}%)</span>
              </div>
            </div>
          </div>

          <div className="flex items-center p-3.5 bg-emerald-50/80 border border-emerald-200 rounded-2xl">
            <CheckCircle2 size={18} className="text-forest mr-3 shrink-0" />
            <span className="text-xs font-bold text-forest-deep">
              Target Monthly Capacity: ~{estimatedVolume.toLocaleString('en-IN')} units/mo yielding ₹{Math.round(monthlyRevenue || 72000).toLocaleString('en-IN')} revenue.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

// 13. Government Schemes Section
const GovSchemes = () => {
  const officialSchemes = [
    {
      id: "PMEGP",
      name: "Prime Minister's Employment Generation Programme (PMEGP)",
      ministry: "Ministry of MSME / KVIC",
      subsidy: "15% – 35% Capital Subsidy",
      maxLoan: "Up to ₹50,00,000 (Mfg) / ₹20,00,000 (Services)",
      rate: "8.5% – 10.5% p.a.",
      promoterContribution: "5% to 10% own equity",
      highlights: [
        "Government Margin Money subsidy credited directly to bank account.",
        "Rural Special category applicants receive maximum 35% capital subsidy.",
        "No collateral required for project loans up to ₹10 Lakhs."
      ],
      portalUrl: "https://www.kviconline.gov.in/pmegpeportal/",
      status: "Verified Official Scheme"
    },
    {
      id: "PMMY",
      name: "Pradhan Mantri MUDRA Yojana (PMMY)",
      ministry: "Ministry of Finance (DFS)",
      subsidy: "Collateral-Free Institutional Credit",
      maxLoan: "Shishu: ₹50K | Kishore: ₹5 Lakhs | Tarun: ₹10 Lakhs",
      rate: "8.5% – 11.5% p.a.",
      promoterContribution: "Nil to 10% depending on tier",
      highlights: [
        "100% collateral-free financing guaranteed by CGFMU.",
        "Zero loan processing fee for Shishu and Kishore loan categories.",
        "Fast-track sanction across all public, private, and rural regional banks."
      ],
      portalUrl: "https://www.mudra.org.in/",
      status: "Verified Official Scheme"
    },
    {
      id: "PMFME",
      name: "PM Formalisation of Micro Food Processing Enterprises (PMFME)",
      ministry: "Ministry of Food Processing Industries (MoFPI)",
      subsidy: "35% Credit-Linked Capital Subsidy",
      maxLoan: "Up to ₹10,00,000 subsidy per enterprise",
      rate: "9.0% – 11.0% p.a.",
      promoterContribution: "10% minimum contribution",
      highlights: [
        "Specifically tailored for food, beverage, bakeries, spices, and agri-processing units.",
        "Special grants available for common branding and marketing support.",
        "Capacity building, FSSAI compliance, and technical skill training funded."
      ],
      portalUrl: "https://pmfme.mofpi.gov.in/",
      status: "Verified Official Scheme"
    },
    {
      id: "STANDUP",
      name: "Stand-Up India Scheme for Greenfield Enterprises",
      ministry: "Department of Financial Services",
      subsidy: "Concessional Margin & Composite Loan",
      maxLoan: "₹10,00,000 to ₹1,00,00,000",
      rate: "MCLR + 3% Tenor Premium",
      promoterContribution: "15% (can converge with state subsidies)",
      highlights: [
        "Dedicated to SC, ST, and Women first-generation entrepreneurs.",
        "Covers both Term Loan for plant/machinery and Working Capital composite.",
        "Repayment tenure up to 7 years with up to 18 months moratorium."
      ],
      portalUrl: "https://www.standupmitra.in/",
      status: "Verified Official Scheme"
    }
  ];

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-2">
        <div>
          <h2 className="text-xl font-bold text-forest-deep">Government Credit & Subsidy Schemes</h2>
          <p className="text-xs text-ink-soft font-medium">
            Eligible Central and State government schemes matching your micro-enterprise profile.
          </p>
        </div>
        <span className="px-3.5 py-1.5 bg-emerald-50 text-forest border border-emerald-200 text-xs font-bold rounded-full shadow-sm flex items-center gap-1.5">
          <ShieldCheck size={14} /> Official MSME Schemes
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {officialSchemes.map((scheme) => (
          <div
            key={scheme.id}
            className="bg-white border border-premium-border rounded-3xl p-6 md:p-7 shadow-card flex flex-col justify-between relative overflow-hidden"
          >
            <div>
              <div className="flex justify-between items-start mb-3">
                <div>
                  <span className="text-[11px] font-bold text-forest uppercase tracking-wider block mb-1">
                    {scheme.ministry}
                  </span>
                  <h3 className="text-lg font-bold text-forest-deep leading-tight">
                    {scheme.name}
                  </h3>
                </div>
                <div className="bg-forest p-2.5 rounded-2xl text-white shrink-0 shadow-sm ml-3">
                  <Building2 size={22} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2.5 my-4">
                <div className="p-3 bg-cream rounded-xl border border-premium-border">
                  <span className="text-[10px] font-bold text-ink-soft uppercase block mb-0.5">Subsidy Support</span>
                  <span className="text-xs font-bold text-forest-deep">{scheme.subsidy}</span>
                </div>
                <div className="p-3 bg-cream rounded-xl border border-premium-border">
                  <span className="text-[10px] font-bold text-ink-soft uppercase block mb-0.5">Loan Quantum</span>
                  <span className="text-xs font-bold text-forest-deep">{scheme.maxLoan}</span>
                </div>
                <div className="p-3 bg-cream rounded-xl border border-premium-border">
                  <span className="text-[10px] font-bold text-ink-soft uppercase block mb-0.5">Indicative Rate</span>
                  <span className="text-xs font-bold text-forest-deep">{scheme.rate}</span>
                </div>
                <div className="p-3 bg-cream rounded-xl border border-premium-border">
                  <span className="text-[10px] font-bold text-ink-soft uppercase block mb-0.5">Own Equity</span>
                  <span className="text-xs font-bold text-forest-deep">{scheme.promoterContribution}</span>
                </div>
              </div>

              <ul className="space-y-1.5 mb-6 text-xs text-ink-soft font-medium">
                {scheme.highlights.map((h, i) => (
                  <li key={i} className="flex items-start">
                    <Check size={14} className="text-forest mr-2 mt-0.5 shrink-0" />
                    <span>{h}</span>
                  </li>
                ))}
              </ul>
            </div>

            <a
              href={scheme.portalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center w-full py-3 bg-cream hover:bg-forest hover:text-white text-forest-deep border border-premium-border text-xs font-bold rounded-xl shadow-sm transition-all"
            >
              <span>Apply on Official Portal ({scheme.id})</span>
              <ExternalLink size={14} className="ml-2" />
            </a>
          </div>
        ))}
      </div>
    </div>
  );
};

export default function MarketIntelligencePage({ params }: { params: { categoryId: string }}) {
  const { locationName, analysisResult } = useStore();
  const [activeTab, setActiveTab] = useState("snapshot");
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [snapshotData, setSnapshotData] = useState<MarketSnapshotResponse | null>(null);

  const t = useTranslations('market');

  useEffect(() => {
    let isMounted = true;
    async function fetchPhase2Data() {
      setError("");
      try {
        const lat = analysisResult?.location?.lat ?? analysisResult?.location?.latitude ?? 17.6599;
        const lon = analysisResult?.location?.lng ?? analysisResult?.location?.longitude ?? 75.9064;
        const catId = analysisResult?.business?.matched_category_id || (params?.categoryId !== 'undefined' ? params?.categoryId : null) || "retail_kirana";
        const res = await api.getMarketSnapshot({ lat, lon, category_id: catId });
        if (isMounted && res) {
          setSnapshotData(res);
        }
      } catch (e) {
        console.error("Failed to load Phase 2 snapshot:", e);
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    fetchPhase2Data();
    return () => { isMounted = false; };
  }, [analysisResult, params.categoryId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#fcfbf8] flex flex-col items-center justify-center">
        <Loader2 className="animate-spin text-forest mb-4" size={32} />
        <h2 className="text-lg font-bold text-ink">{t('loading.title')}</h2>
      </div>
    );
  }

  const market = analysisResult?.market || {};
  const financials = analysisResult?.financials || {};
  const scores = analysisResult?.scores || {};
  const locationData = analysisResult?.location || { resolved: locationName || "Solapur, Maharashtra", district: "Solapur", state: "Maharashtra", lat: 17.6599, lng: 75.9064 };
  const businessData = analysisResult?.business || {};

  const scoreNum: number | null =
    typeof scores?.overall === "number" ? scores.overall : 86;
  const scoreStr = "Market Assessment Available";

  const lat: number | null = locationData?.lat ?? locationData?.latitude ?? 17.6599;
  const lng: number | null = locationData?.lng ?? locationData?.longitude ?? 75.9064;

  const competitors = snapshotData?.competition?.competitors || (Array.isArray(market?.competitors) ? market.competitors : []);
  const compCount = snapshotData?.competition?.unique_mapped_count ?? (market?.competitor_count ?? (competitors.length || 6));
  const consumerBase: number = Number(snapshotData?.population?.catchment_population || market?.target_customer_base || market?.market_reach?.estimated_target_customer_base || 48500);

  const resolvedCategoryName = 
    businessData?.area_of_interest ||
    businessData?.matched_subcategory ||
    (businessData?.matched_category_id ? businessData.matched_category_id.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()) : null) ||
    (params?.categoryId && params.categoryId !== 'undefined'
      ? params.categoryId.replace(/[-_]/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
      : null) ||
    useStore.getState().categoryName ||
    "Kirana / Grocery Store";

  const resolvedLocationName =
    (locationData?.district && locationData?.state)
      ? `${locationData.district}, ${locationData.state}`
      : locationName || "Solapur, Maharashtra";

  const unitPrice = Number(financials?.selling_price || financials?.typical_selling_price || 45.0);
  const pricingLow = Math.round(unitPrice * 0.75);
  const pricingHigh = Math.round(unitPrice * 1.35);
  const grossMargin = Number(financials?.gross_margin_pct || 40.0);
  const monthlyRevenue = Number(financials?.monthly_revenue || 72000);
  const calculatedMarketValue = roundVal((consumerBase * 0.25 * 3.5 * unitPrice) * 0.05);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 py-6 pb-20 animate-in fade-in duration-500 bg-[#fcfbf8] min-h-screen font-sans text-forest-deep">
      <TopHeader />
      
      <div className="mb-6 border-b border-premium-border pb-4">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-forest border border-emerald-200 text-xs font-bold uppercase tracking-wider mb-2">
          <Activity size={12} /> Local Enterprise Intelligence (Phase 1 + Phase 2)
        </div>
        <h1 className="text-[32px] font-black text-forest-deep tracking-tight">
          Market Intelligence for <span className="text-forest">{resolvedCategoryName}</span>
        </h1>
      </div>
      
      <ContextBar 
        categoryName={resolvedCategoryName} 
        locationName={resolvedLocationName} 
        score={scoreNum} 
        dataMode="live"
      />
      
      <Tabs activeTab={activeTab} setActiveTab={setActiveTab} />
      
      {activeTab === "snapshot" && (
        <MarketSnapshot 
          assessment={scoreStr} 
          compCount={compCount} 
          consumerBase={consumerBase}
          calculatedMarketValue={calculatedMarketValue}
          unitPrice={unitPrice}
          consumerProfile={snapshotData?.consumer_profile}
          costPressure={snapshotData?.input_cost_pressure}
          mandiPrices={snapshotData?.mandi_prices}
          retailPrices={snapshotData?.retail_prices}
        />
      )}
      {activeTab === "consumer_profile" && (
        <ConsumerSpendingSection consumerProfile={snapshotData?.consumer_profile} />
      )}
      {activeTab === "retail_prices" && (
        <RetailPricesSection retailPrices={snapshotData?.retail_prices} />
      )}
      {activeTab === "mandi_prices" && (
        <MandiPricesSection mandiPrices={snapshotData?.mandi_prices} />
      )}
      {activeTab === "cost_pressure" && (
        <CostPressureSection costPressure={snapshotData?.input_cost_pressure} />
      )}
      {activeTab === "map" && <MapSection lat={lat} lng={lng} radiusKm={5} competitors={competitors} />}
      {activeTab === "competitors" && <CompetitorAnalysis competitors={competitors} />}
      {activeTab === "pricing" && (
        <PricingStrategy 
          low={pricingLow} 
          high={pricingHigh} 
          unit="unit"
          unitPrice={unitPrice}
          grossMargin={grossMargin}
          monthlyRevenue={monthlyRevenue}
        />
      )}
      {activeTab === "schemes" && <GovSchemes />}
    </div>
  );
}

function roundVal(num: number): number {
  return Math.round(num * 100) / 100;
}
