"use client";
import React from 'react';
import { useStore, BusinessPlan } from '@/lib/store';
import { Card, CardContent } from '@/components/ui/card';
import { Folder, Calendar, Target, MapPin, ArrowRight, ShieldCheck, ShieldAlert, Sparkles, FileText, BarChart3 } from 'lucide-react';
import Link from 'next/link';
import { formatCurrency } from '@/lib/formatters';
import { SwotMatrix } from '@/components/SwotMatrix';

export default function PlansPage() {
  const { savedPlans, saveCurrentPlan, categoryId, categoryName, locationName, marginCapital, analysisResult } = useStore();

  const handleSaveCurrent = () => {
    saveCurrentPlan();
  };

  const resolvedCat = analysisResult?.business?.matched_category_id || categoryId || "agri_business";
  const resolvedName = analysisResult?.business?.area_of_interest || categoryName || "Poultry Farming (Broiler/Layer)";
  const resolvedLoc = analysisResult?.location?.resolved || locationName || "Solapur, Maharashtra";

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 animate-in fade-in duration-500 text-slate-800 min-h-screen">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 border-b border-gray-200/80 pb-6 gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 font-sans">Business Plans & Strategic Evaluation</h1>
          <p className="text-slate-500 mt-1 text-base">Comprehensive feasibility models and Gemini-powered SWOT analysis.</p>
        </div>
        
        {categoryId && (
          <button 
            onClick={handleSaveCurrent}
            className="flex items-center px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-xs font-bold text-slate-700 hover:border-emerald-600 hover:text-emerald-700 transition-all shadow-sm"
          >
            <Folder size={16} className="mr-2 text-emerald-600" /> Save Active Session
          </button>
        )}
      </div>

      {/* Active Proposal Strategic SWOT Matrix */}
      <div className="mb-10">
        <SwotMatrix 
          categoryId={resolvedCat}
          categoryName={resolvedName}
          locationName={resolvedLoc}
          financials={analysisResult?.financials}
          marketData={analysisResult?.market}
          scores={analysisResult?.scores}
        />
      </div>

      <div className="mb-6">
        <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
          <BarChart3 size={20} className="text-emerald-600" /> Saved Business Portfolios
        </h2>
      </div>

      {savedPlans && savedPlans.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {savedPlans.map((plan: BusinessPlan) => (
            <Card key={plan.id} className="bg-white border-gray-200 hover:border-emerald-500 hover:shadow-lg transition-all rounded-2xl overflow-hidden group">
              <div className="p-5 border-b border-gray-100 bg-slate-50/50">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-lg text-slate-900 group-hover:text-emerald-700 transition-colors">{plan.categoryName}</h3>
                  <div className="flex flex-col items-center bg-white border border-gray-200 px-2.5 py-1 rounded-xl shadow-2xs">
                    <span className={`text-lg font-black leading-none ${plan.score >= 80 ? 'text-emerald-600' : 'text-amber-600'}`}>
                      {plan.score}
                    </span>
                    <span className="text-[8px] uppercase font-bold text-slate-400 tracking-widest mt-1">Score</span>
                  </div>
                </div>
                <div className="flex items-center text-xs text-slate-500 uppercase tracking-wider font-semibold">
                  <MapPin size={12} className="mr-1 text-emerald-600" /> {plan.locationName}
                </div>
              </div>
              
              <CardContent className="p-5">
                <div className="space-y-3 mb-6">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500 flex items-center"><Calendar size={14} className="mr-2" /> Created</span>
                    <span className="font-semibold text-slate-800">{plan.createdAt}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500 flex items-center"><Target size={14} className="mr-2" /> Capital</span>
                    <span className="font-bold text-slate-800">{formatCurrency(plan.marginCapital)}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500 flex items-center"><Sparkles size={14} className="mr-2 text-emerald-600" /> Status</span>
                    <span className="font-bold text-emerald-700">{plan.status}</span>
                  </div>
                </div>
                
                <Link href={`/score/${plan.categoryId}`} className="w-full flex items-center justify-center px-4 py-2.5 bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold text-xs rounded-xl hover:bg-emerald-600 hover:text-white transition-all shadow-2xs">
                  <span>Open Full Assessment</span>
                  <ArrowRight size={14} className="ml-1.5" />
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="bg-white border-dashed border-2 border-gray-200 flex flex-col items-center justify-center p-12 text-center rounded-3xl">
          <div className="w-16 h-16 bg-slate-50 border border-gray-100 rounded-full flex items-center justify-center mb-4">
            <FileText size={28} className="text-slate-400" />
          </div>
          <h3 className="text-lg font-bold mb-1 text-slate-800">No Other Saved Plans in Portfolio</h3>
          <p className="text-slate-500 text-xs mb-6 max-w-sm">Save your active evaluation above or discover alternative business opportunities to compare models.</p>
          <Link href="/discover" className="bg-[#1b4d3e] text-white px-6 py-2.5 rounded-xl text-xs font-bold hover:bg-[#143e32] transition-colors shadow-sm">
            Discover Opportunities
          </Link>
        </Card>
      )}
    </div>
  );
}

