import React from 'react';
import { Users, BarChart3, Landmark } from 'lucide-react';

export function HeroFeatureStrip() {
  return (
    <div className="w-full bg-[#fdfbf6] border-t border-premium-border/50 z-20 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2 lg:py-3">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-4 divide-y md:divide-y-0 md:divide-x divide-premium-border">
          
          <div className="flex items-center justify-center md:justify-start px-4 pt-4 md:pt-0">
            <div className="w-10 h-10 rounded-full bg-[#f6f9f6] flex items-center justify-center border border-premium-border mr-3 shrink-0">
              <Users size={18} className="text-forest" />
            </div>
            <div className="text-xs font-medium text-ink leading-snug">
              <span className="block text-ink-soft">Trusted by</span>
              <span className="font-bold">Rural Entrepreneurs</span>
            </div>
          </div>

          <div className="flex items-center justify-center md:justify-center px-4 pt-4 md:pt-0">
            <div className="w-10 h-10 rounded-full bg-[#f6f9f6] flex items-center justify-center border border-premium-border mr-3 shrink-0">
              <BarChart3 size={18} className="text-forest" />
            </div>
            <div className="text-xs font-medium text-ink leading-snug">
              <span className="block text-ink-soft">Data-Driven</span>
              <span className="font-bold">Decisions</span>
            </div>
          </div>

          <div className="flex items-center justify-center md:justify-end px-4 pt-4 md:pt-0">
            <div className="w-10 h-10 rounded-full bg-[#f6f9f6] flex items-center justify-center border border-premium-border mr-3 shrink-0">
              <Landmark size={18} className="text-forest" />
            </div>
            <div className="text-xs font-medium text-ink leading-snug">
              <span className="block text-ink-soft">Government & Financial</span>
              <span className="font-bold">Institution Friendly</span>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
