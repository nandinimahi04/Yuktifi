import React from 'react';
import { CheckCircle2, ArrowRight } from 'lucide-react';

export function BusinessRecommendationCard() {
  return (
    <div className="bg-white rounded-3xl p-5 shadow-card border border-premium-border flex-1 min-w-[200px] flex flex-col justify-between relative overflow-hidden">
      {/* Decorative gradient bleed */}
      <div className="absolute -right-10 -top-10 w-32 h-32 bg-saffron-tint rounded-full blur-2xl opacity-50 pointer-events-none aria-hidden='true'"></div>
      
      <div>
        <div className="text-[10px] uppercase font-bold tracking-widest text-saffron mb-1">Recommended Opportunity</div>
        <h3 className="font-display font-bold text-xl text-ink leading-tight mb-1">E-Rickshaw</h3>
        <p className="text-xs text-ink-soft mb-4">Transport & Mobility</p>

        <div className="space-y-2 mb-4">
          <div className="flex items-start text-xs text-ink-soft">
            <CheckCircle2 className="w-4 h-4 text-forest mr-2 shrink-0" />
            <span>High local demand gap identified</span>
          </div>
          <div className="flex items-start text-xs text-ink-soft">
            <CheckCircle2 className="w-4 h-4 text-forest mr-2 shrink-0" />
            <span>Matches available capital</span>
          </div>
          <div className="flex items-start text-xs text-ink-soft">
            <CheckCircle2 className="w-4 h-4 text-forest mr-2 shrink-0" />
            <span>Low market saturation</span>
          </div>
        </div>
      </div>

      <button className="text-sm font-bold text-saffron hover:text-saffron-deep transition-colors flex items-center group w-fit focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron rounded">
        Explore Opportunity <ArrowRight size={16} className="ml-1 group-hover:translate-x-1 transition-transform" />
      </button>
    </div>
  );
}
