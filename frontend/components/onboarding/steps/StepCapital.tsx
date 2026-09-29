import React from 'react';
import { ChevronLeft, ArrowRight } from 'lucide-react';
import { useTranslations } from 'next-intl';

export interface CapitalData {
  investment: string;
  investmentTier?: string;
  sourceOfFunds: string;
  customInvestment?: string;
}

interface StepCapitalProps {
  data: CapitalData;
  updateData: (updates: Partial<CapitalData>) => void;
  onNext: () => void;
  onBack: () => void;
}

const INVESTMENT_OPTIONS = [
  { label: 'Under ₹50,000', value: '35000' },
  { label: '₹50,000 - ₹1L', value: '75000' },
  { label: '₹1L - ₹3L', value: '200000' },
  { label: '₹3L - ₹5L', value: '400000' },
  { label: 'Above ₹5L', value: '750000' }
];

const SOURCE_OPTIONS = [
  { 
    id: 'personal_savings', 
    label: 'Personal Savings', 
    desc: 'Your own money' 
  },
  { 
    id: 'bank_loan', 
    label: 'Bank Loan', 
    desc: 'Planning to borrow from a bank' 
  },
  { 
    id: 'govt_scheme', 
    label: 'Govt Scheme', 
    desc: 'Mudra, PMEGP, etc.' 
  },
  { 
    id: 'friends_family', 
    label: 'Friends / Family', 
    desc: 'Borrowing from relatives' 
  }
];

export function StepCapital({ data, updateData, onNext, onBack }: StepCapitalProps) {
  const t = useTranslations('onboarding.step3');
  const tCommon = useTranslations('common');

  const isCustomSelected = !!data.customInvestment || (!INVESTMENT_OPTIONS.some(opt => opt.value === data.investment) && !!data.investment);

  const handleSelectTier = (opt: { label: string; value: string }) => {
    updateData({
      investment: opt.value,
      investmentTier: opt.label,
      customInvestment: ''
    });
  };

  const handleCustomChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/\D/g, '');
    updateData({
      customInvestment: raw,
      investment: raw,
      investmentTier: 'Custom'
    });
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-3xl p-6 sm:p-8 border border-premium-border shadow-card relative overflow-hidden justify-between">
      <div className="flex-1 overflow-y-auto min-h-0 pr-1 space-y-6">
        <div>
          <h2 className="text-2xl sm:text-[28px] font-bold text-forest-deep mb-1 font-display tracking-tight">
            {t('title')}
          </h2>
          <p className="text-ink-soft text-sm font-medium">
            {t('subtitle')}
          </p>
        </div>

        <div className="space-y-6">
          {/* Available Investment */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-ink flex items-center">
              Available Investment <span className="text-[#ea580c] ml-1">*</span>
            </label>
            
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {INVESTMENT_OPTIONS.map(opt => {
                const isSelected = !isCustomSelected && data.investment === opt.value;
                return (
                  <label 
                    key={opt.value}
                    onClick={() => handleSelectTier(opt)}
                    className={`flex items-center px-4 py-2.5 rounded-xl border cursor-pointer transition-all ${
                      isSelected 
                        ? 'border-forest bg-forest-tint/30 text-forest-deep font-bold ring-1 ring-forest' 
                        : 'border-premium-border hover:bg-cream/60 text-ink font-medium'
                    }`}
                  >
                    <input 
                      type="radio" 
                      name="investmentTier" 
                      value={opt.value}
                      className="mr-2.5 w-4 h-4 accent-forest"
                      checked={isSelected}
                      onChange={() => handleSelectTier(opt)}
                    />
                    <span className="text-xs font-semibold">{opt.label}</span>
                  </label>
                );
              })}

              {/* Custom Amount Input */}
              <div className="relative">
                <input 
                  type="text"
                  placeholder="Or type a custom amount (e.g. 75...)"
                  className={`w-full rounded-xl border px-3.5 py-2.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-forest transition-all ${
                    isCustomSelected 
                      ? 'border-forest bg-forest-tint/20 font-bold ring-1 ring-forest' 
                      : 'border-premium-border hover:bg-cream/40'
                  }`}
                  value={data.customInvestment || ''}
                  onChange={handleCustomChange}
                />
              </div>
            </div>
          </div>
          
          {/* Primary Source of Funds */}
          <div className="space-y-2 pt-2">
            <label className="text-xs font-bold text-ink flex items-center">
              Primary Source of Funds <span className="text-[#ea580c] ml-1">*</span>
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {SOURCE_OPTIONS.map(src => {
                const isSelected = data.sourceOfFunds === src.id;
                return (
                  <label 
                    key={src.id}
                    onClick={() => updateData({ sourceOfFunds: src.id })}
                    className={`flex items-start px-4 py-3 rounded-2xl border cursor-pointer transition-all ${
                      isSelected 
                        ? 'border-forest bg-forest-tint/30 ring-1 ring-forest shadow-xs' 
                        : 'border-premium-border hover:bg-cream/60'
                    }`}
                  >
                    <input 
                      type="radio" 
                      name="sourceOfFunds" 
                      value={src.id}
                      className="mt-1 mr-3 w-4 h-4 accent-forest"
                      checked={isSelected}
                      onChange={() => updateData({ sourceOfFunds: src.id })}
                    />
                    <div className="flex flex-col">
                      <span className="text-sm font-bold text-forest-deep">{src.label}</span>
                      <span className="text-xs text-ink-soft mt-0.5">{src.desc}</span>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

        </div>
      </div>

      {/* Footer Nav */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-premium-border">
        <button 
          type="button"
          onClick={onBack}
          className="flex items-center text-ink-soft hover:text-ink font-bold text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron rounded px-2 py-1"
        >
          <ChevronLeft size={18} className="mr-1" /> {tCommon('back')}
        </button>
        
        <button 
          type="button"
          onClick={onNext}
          disabled={!data.investment || !data.sourceOfFunds}
          className="bg-[#ea580c] hover:bg-[#c2410c] text-white px-7 py-2.5 rounded-xl text-sm font-bold flex items-center justify-center shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#ea580c] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {tCommon('next')} <ArrowRight size={18} className="ml-2" />
        </button>
      </div>
    </div>
  );
}
