import React from 'react';
import { Map, PieChart, BrainCircuit } from 'lucide-react';

export function TrustIndicators() {
  return (
    <div className="mt-8 border-t border-premium-border pt-6">
      <p className="text-xs font-bold uppercase tracking-widest text-ink-faint mb-4">
        Trusted by local enterprise
      </p>
      
      <div className="flex flex-col sm:flex-row gap-4 sm:gap-6 text-sm text-ink-soft">
        <div className="flex items-center">
          <Map className="w-5 h-5 text-saffron mr-2" />
          <span className="font-medium">Local Market Intelligence</span>
        </div>
        <div className="flex items-center">
          <PieChart className="w-5 h-5 text-forest mr-2" />
          <span className="font-medium">Financial Planning</span>
        </div>
        <div className="flex items-center">
          <BrainCircuit className="w-5 h-5 text-saffron mr-2" />
          <span className="font-medium">AI-Assisted Insights</span>
        </div>
      </div>
    </div>
  );
}
