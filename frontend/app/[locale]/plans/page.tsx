"use client";
import React from 'react';
import { useStore, BusinessPlan } from '@/lib/store';
import { Card, CardContent } from '@/components/ui/card';
import { Folder, Calendar, Target, MapPin, ArrowRight, ShieldCheck, ShieldAlert, Sparkles, FileText } from 'lucide-react';
import Link from 'next/link';
import { formatCurrency } from '@/lib/formatters';

export default function PlansPage() {
  const { savedPlans, saveCurrentPlan, categoryId, categoryName, locationName, marginCapital } = useStore();

  const handleSaveCurrent = () => {
    saveCurrentPlan();
  };

  return (
    <div className="max-w-5xl mx-auto p-4 md:p-8 animate-in fade-in duration-500 text-warm-text min-h-screen">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 border-b border-warm-border pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My Business Plans</h1>
          <p className="text-warm-muted mt-2 text-lg">Manage your saved business evaluations.</p>
        </div>
        
        {categoryId && (
          <button 
            onClick={handleSaveCurrent}
            className="mt-4 md:mt-0 flex items-center px-4 py-2 bg-warm-surface border border-warm-border rounded-lg text-sm font-semibold hover:border-warm-primary hover:text-warm-primary transition-colors shadow-sm"
          >
            <Folder size={16} className="mr-2" /> Save Active Session
          </button>
        )}
      </div>

      {savedPlans && savedPlans.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {savedPlans.map((plan: BusinessPlan) => (
            <Card key={plan.id} className="bg-warm-surface border-warm-border hover:border-warm-primary hover:shadow-lg transition-all rounded-xl overflow-hidden group">
              <div className="p-5 border-b border-warm-border bg-warm-bg/30">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-lg text-warm-text group-hover:text-warm-primary transition-colors">{plan.categoryName}</h3>
                  <div className="flex flex-col items-center bg-warm-surface border border-warm-border px-2 py-1 rounded-md">
                    <span className={`text-lg font-black leading-none ${plan.score >= 80 ? 'text-emerald-600' : 'text-amber-600'}`}>
                      {plan.score}
                    </span>
                    <span className="text-[8px] uppercase font-bold text-warm-muted tracking-widest mt-1">Score</span>
                  </div>
                </div>
                <div className="flex items-center text-xs text-warm-muted uppercase tracking-wider font-semibold">
                  <MapPin size={12} className="mr-1" /> {plan.locationName}
                </div>
              </div>
              
              <CardContent className="p-5">
                <div className="space-y-3 mb-6">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-warm-muted flex items-center"><Calendar size={14} className="mr-2" /> Created</span>
                    <span className="font-medium">{plan.createdAt}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-warm-muted flex items-center"><Target size={14} className="mr-2" /> Capital</span>
                    <span className="font-medium">{formatCurrency(plan.marginCapital)}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-warm-muted flex items-center"><Sparkles size={14} className="mr-2" /> Status</span>
                    <span className="font-bold text-warm-primary">{plan.status}</span>
                  </div>
                </div>
                
                <Link href={`/score/${plan.categoryId}`} className="w-full flex items-center justify-center px-4 py-2 bg-warm-primary/10 text-warm-primary font-semibold rounded-lg hover:bg-warm-primary hover:text-warm-text transition-colors">
                  Open Plan <ArrowRight size={16} className="ml-2" />
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="bg-warm-surface border-dashed border-2 border-warm-border flex flex-col items-center justify-center p-12 text-center rounded-2xl">
          <div className="w-16 h-16 bg-warm-bg rounded-full flex items-center justify-center mb-4">
            <FileText size={32} className="text-warm-muted" />
          </div>
          <h2 className="text-xl font-bold mb-2">No Saved Plans</h2>
          <p className="text-warm-muted mb-6 max-w-sm">You haven't saved any business plans yet. Discover opportunities to create your first plan.</p>
          <Link href="/discover" className="bg-warm-primary text-warm-text px-6 py-3 rounded-lg font-medium hover:bg-warm-primary/90 transition-colors shadow-sm">
            Discover Opportunities
          </Link>
        </Card>
      )}
    </div>
  );
}
