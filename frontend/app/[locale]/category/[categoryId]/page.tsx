"use client";
import React, { useEffect, useState } from "react";
import { useRouter } from "@/routing";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SourceTooltip } from "@/components/SourceTooltip";
import dynamic from "next/dynamic";
const MapRadiusOverlay = dynamic(() => import("@/components/MapRadiusOverlay").then(mod => mod.MapRadiusOverlay), { ssr: false });
import { api } from "@/lib/api-client";
import { useStore } from "@/lib/store";
import { formatNumber } from "@/lib/formatters";
import { Loader2, ArrowRight, ShieldAlert, Zap, Search, Target } from "lucide-react";
import { motion } from "framer-motion";
// import { MarketRadar } from "@/components/MarketRadar";

export default function CategoryDeepDivePage({ params }: { params: { categoryId: string } }) {
 const router = useRouter();
 const state = useStore();
 const [loading, setLoading] = useState(true);
 const [data, setData] = useState<any>(null);
 const [error, setError] = useState("");

 useEffect(() => {
 if (!state.sessionId) {
 router.push("/");
 return;
 }

 const fetchMarket = async () => {
 try {
 const res = await api.analyzeMarket({
 session_id: state.sessionId!,
 location_id: state.locationId!,
 category_id: params.categoryId,
 });
 setData(res);
 } catch (err: any) {
 setError(err.message ||"Failed to fetch market analysis");
 } finally {
 setLoading(false);
 }
 };

 fetchMarket();
 }, [state, params.categoryId, router]);

 if (loading) {
 return (
 <div className="max-w-5xl mx-auto mt-10">
 <div className="h-64 flex flex-col items-center justify-center space-y-4">
 <Loader2 size={48} className="animate-spin text-warm-primary" />
 <p className="text-warm-primary font-sans animate-pulse">Gathering market intelligence...</p>
 </div>
 </div>
 );
 }

 if (error || !data) {
 return <div className="text-red-500 p-4">{error}</div>;
 }

 const mapCenter = { lat: 18.2334, lng: 75.6910 };

 // Generate fake radar data based on the gap score
 const radarData = [
 { subject: 'Local Demand', A: Math.min(100, data.opportunity_gaps.gap_score + 20), fullMark: 100 },
 { subject: 'Purchasing Power', A: 65, fullMark: 100 },
 { subject: 'Logistics', A: 80, fullMark: 100 },
 { subject: 'Competitor Density', A: 100 - (data.competitors.count * 10), fullMark: 100 },
 { subject: 'Raw Material', A: 75, fullMark: 100 },
 { subject: 'Market Growth', A: data.opportunity_gaps.gap_score, fullMark: 100 },
 ];

 return (
 <motion.div 
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ duration: 0.5 }}
 className="max-w-5xl mx-auto mt-10 pb-20"
 >
 <div className="flex flex-col sm:flex-row justify-between items-center sm:items-end mb-8 gap-4 border-b border-warm-border pb-4">
 <div>
 <h1 className="text-2xl font-sans text-warm-text tracking-widest uppercase">{data.category_name}</h1>
 <p className="text-warm-primary mt-2 text-xs font-sans">MARKET INTELLIGENCE // LOC: {state.locationName}</p>
 </div>
 <Button onClick={() => router.push(`/score/${params.categoryId}`)} variant="outline" className="text-xs">
 RUN_FINANCIAL_MODELS <ArrowRight size={14} className="ml-2" />
 </Button>
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
 {/* Left Column: Demographics & Map */}
 <div className="lg:col-span-1 space-y-6">
 <Card className="border-warm-border">
 <CardHeader className="bg-warm-surface pb-4 border-b border-warm-border">
 <CardTitle className="text-xs font-sans text-warm-muted flex items-center">
 <Target size={14} className="mr-2 text-warm-primary" />
 Market Reach
 <div className="ml-auto">
 <SourceTooltip source={data.market_reach.data_origin ||"Curated"} confidence={data.market_reach.confidence} />
 </div>
 </CardTitle>
 </CardHeader>
 <CardContent className="pt-6">
 <div className="text-4xl font-sans font-bold text-warm-text">
 {data.market_reach.consumer_base ? formatNumber(data.market_reach.consumer_base) : "Unknown"}
 </div>
 <p className="text-[10px] text-warm-muted mt-1">Estimated consumers in radius</p>
 
 <div className="mt-6 pt-6 border-t border-warm-border">
 <p className="text-[10px] font-sans text-warm-muted">Demand vs Supply Gap:</p>
 <div className="mt-2 flex items-center justify-between">
 <span className={`px-2 py-1 text-[10px] font-sans font-bold uppercase border ${data.opportunity_gaps.gap_score >= 70 ? 'bg-warm-bg text-warm-secondary border-warm-secondary' : 'bg-warm-bg text-orange-500 border-orange-500'}`}>
 Score: {data.opportunity_gaps.gap_score ||"N/A"}/100
 </span>
 <span className="text-[10px] font-sans text-warm-text uppercase">{data.opportunity_gaps.assessment}</span>
 </div>
 </div>

 <div className="mt-4 border-t border-slate-200/50">
 {/* <MarketRadar data={radarData} /> */}
 </div>
 </CardContent>
 </Card>

 <Card className="border-warm-border overflow-hidden">
 <CardHeader className="bg-warm-surface pb-4 border-b border-warm-border">
 <CardTitle className="text-xs font-sans text-warm-muted flex items-center">
 <Search size={14} className="mr-2 text-warm-primary" />
 Competition ({data.competitors.count} found)
 <div className="ml-auto">
 <SourceTooltip source={data.competitors.data_origin ||"Curated"} confidence={data.competitors.confidence} />
 </div>
 </CardTitle>
 </CardHeader>
 <CardContent className="p-0">
 <MapRadiusOverlay 
 lat={mapCenter.lat} 
 lng={mapCenter.lng} 
 radiusKm={10} 
 competitors={data.competitors.records} 
 />
 </CardContent>
 </Card>
 </div>

 {/* Right Column: Strengths, Weaknesses, Opportunities, Threats & Risks */}
 <div className="lg:col-span-2 space-y-6">
 <Card className="border-warm-border">
 <CardHeader className="bg-warm-surface pb-4 border-b border-warm-border">
 <CardTitle className="text-xs font-sans text-warm-muted flex items-center">
 <Zap size={14} className="mr-2 text-orange-500" />
 Strengths, Weaknesses, Opportunities, Threats (SWOT) Analysis (Data-Driven)
 <div className="ml-auto">
 <SourceTooltip source="Derived from structured signals" confidence={data.overall_confidence} />
 </div>
 </CardTitle>
 </CardHeader>
 <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
 <motion.div whileHover={{ scale: 1.01 }} className="bg-warm-bg p-4 border border-warm-secondary">
 <h4 className="font-sans font-bold text-warm-secondary mb-2 text-xs">Strengths</h4>
 <ul className="list-disc pl-4 text-xs font-sans text-warm-text space-y-1">
 {data.swot.strengths.map((s: string, i: number) => <li key={i}>{s}</li>)}
 </ul>
 </motion.div>
 <motion.div whileHover={{ scale: 1.01 }} className="bg-warm-bg p-4 border border-orange-500">
 <h4 className="font-sans font-bold text-orange-500 mb-2 text-xs">Weaknesses</h4>
 <ul className="list-disc pl-4 text-xs font-sans text-warm-text space-y-1">
 {data.swot.weaknesses.map((w: string, i: number) => <li key={i}>{w}</li>)}
 </ul>
 </motion.div>
 <motion.div whileHover={{ scale: 1.01 }} className="bg-warm-bg p-4 border border-warm-primary">
 <h4 className="font-sans font-bold text-warm-primary mb-2 text-xs">Opportunities</h4>
 <ul className="list-disc pl-4 text-xs font-sans text-warm-text space-y-1">
 {data.swot.opportunities.map((o: string, i: number) => <li key={i}>{o}</li>)}
 </ul>
 </motion.div>
 <motion.div whileHover={{ scale: 1.01 }} className="bg-warm-bg p-4 border border-red-600">
 <h4 className="font-sans font-bold text-red-600 mb-2 text-xs">Threats / Risks</h4>
 <ul className="list-disc pl-4 text-xs font-sans text-warm-text space-y-1">
 {data.swot.threats.map((t: string, i: number) => <li key={i}>{t}</li>)}
 </ul>
 </motion.div>
 </CardContent>
 </Card>
 
 <Card className="border-warm-border">
 <CardHeader className="bg-warm-surface pb-4 border-b border-warm-border">
 <CardTitle className="text-xs font-sans text-warm-muted flex items-center">
 <ShieldAlert size={14} className="mr-2 text-red-600" />
 Risk Assessment Matrix
 </CardTitle>
 </CardHeader>
 <CardContent className="p-0">
 <div className="divide-y divide-zinc-800">
 {data.threats.risk_factors.map((risk: any, i: number) => (
 <motion.div 
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: 0.2 + (i * 0.1) }}
 key={i} 
 className="p-4 flex flex-col sm:flex-row justify-between sm:items-center hover:bg-warm-surface transition-colors"
 >
 <div className="mb-3 sm:mb-0">
 <p className="font-bold font-sans text-warm-text text-sm mb-1 uppercase">{risk.factor}</p>
 <p className="text-xs font-sans text-warm-muted">{risk.detail}</p>
 </div>
 <span className={`px-2 py-1 text-[10px] font-sans font-bold uppercase border ${
 risk.severity === 'High' ? 'bg-warm-bg text-red-600 border-red-600' :
 risk.severity === 'Medium' ? 'bg-warm-bg text-orange-500 border-orange-500' :
 'bg-warm-bg text-warm-secondary border-warm-secondary'
 }`}>
 {risk.severity} Risk
 </span>
 </motion.div>
 ))}
 </div>
 </CardContent>
 </Card>
 </div>
 </div>
 </motion.div>
 );
}
