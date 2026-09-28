import React from 'react';
import { ChevronLeft, ArrowRight } from 'lucide-react';
import { useTranslations } from 'next-intl';

export interface CapitalData {
  investment: string;
  loanIntent: string;
}

interface StepCapitalProps {
  data: CapitalData;
  updateData: (updates: Partial<CapitalData>) => void;
  onNext: () => void;
  onBack: () => void;
}

export function StepCapital({ data, updateData, onNext, onBack }: StepCapitalProps) {
  const t = useTranslations('onboarding.step3');
  const tCommon = useTranslations('common');
  
  const QUICK_CHIPS = [
    { value: '20000', label: '₹20,000' },
    { value: '50000', label: '₹50,000' },
    { value: '100000', label: '₹1 Lakh' },
    { value: '500000', label: '₹5 Lakhs' }
  ];

  return (
    <div className="flex flex-col h-full bg-white rounded-3xl p-4 sm:p-6 border border-premium-border shadow-card relative overflow-hidden">
      <div className="flex-1 overflow-y-auto min-h-0 pr-2">
        <h2 className="text-[28px] font-bold text-forest-deep mb-1 font-display">Investment & Capital</h2>
        <p className="text-ink-soft text-sm font-medium mb-4">
          How much capital can you realistically arrange to start this business?
        </p>

        <div className="space-y-6">
          {/* Investment Amount */}
          <div className="space-y-3">
            <label className="text-sm font-bold text-ink flex items-center">
              Available Investment (in ₹) <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <div className="relative">
              <span className="absolute left-4 top-2.5 text-ink-soft font-bold">₹</span>
              <input 
                type="number"
                min="0"
                placeholder="e.g. 75000"
                className="w-full sm:w-64 rounded-xl border border-premium-border pl-8 pr-4 py-2 text-ink font-medium focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all"
                value={data.investment}
                onChange={(e) => updateData({ investment: e.target.value })}
              />
            </div>
            
            <div className="flex flex-wrap gap-2 mt-2">
              {QUICK_CHIPS.map(chip => (
                <button
                  key={chip.value}
                  onClick={() => updateData({ investment: chip.value })}
                  className="px-3 py-1.5 rounded-lg border border-premium-border text-xs font-bold text-ink-soft hover:bg-cream hover:text-ink transition-colors"
                >
                  {chip.label}
                </button>
              ))}
            </div>
          </div>
          
          {/* Loan Intent */}
          <div className="space-y-3 pt-4 border-t border-premium-border">
            <label className="text-sm font-bold text-ink flex items-center">
              Do you plan to use a loan? <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { id: 'no', label: 'No', desc: 'Using own savings' },
                { id: 'yes', label: 'Yes', desc: 'Planning to borrow' },
                { id: 'not_sure', label: 'Not Sure', desc: 'Depends on the business' },
              ].map(src => (
                <label key={src.id} className={`flex flex-col px-4 py-3 rounded-xl border cursor-pointer transition-colors ${data.loanIntent === src.id ? 'border-forest bg-forest-tint/30 text-forest-deep font-bold ring-1 ring-forest' : 'border-premium-border hover:bg-cream text-ink'}`}>
                  <div className="flex items-center">
                    <input 
                      type="radio" 
                      name="loanIntent" 
                      value={src.id}
                      className="mr-3 w-4 h-4 accent-forest"
                      checked={data.loanIntent === src.id}
                      onChange={() => updateData({ loanIntent: src.id })}
                    />
                    <span className="text-sm font-bold">{src.label}</span>
                  </div>
                  <span className="text-xs text-ink-soft ml-7 mt-1">{src.desc}</span>
                </label>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* Footer Nav */}
      <div className="flex items-center justify-between mt-4 pt-4 border-t border-premium-border">
        <button 
          onClick={onBack}
          className="flex items-center text-ink-soft hover:text-ink font-bold text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron rounded px-2 py-1"
        >
          <ChevronLeft size={18} className="mr-1" /> {tCommon('back')}
        </button>
        
        <button 
          onClick={onNext}
          disabled={!data.investment || !data.loanIntent}
          className="bg-[#ea580c] hover:bg-[#c2410c] text-white px-8 py-2 rounded-xl text-sm font-bold flex items-center justify-center shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-saffron disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {tCommon('next')} <ArrowRight size={18} className="ml-2" />
        </button>
      </div>
    </div>
  );
}
