import React, { useState } from 'react';
import { ChevronLeft, ArrowRight, Wallet } from 'lucide-react';
import { useTranslations } from 'next-intl';

export interface CapitalData {
  investment: string;
  source: string;
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
  
  const PREDEFINED_OPTIONS = [
    { value: 'Under ₹50,000', label: t('under50k') },
    { value: '₹50,000 - ₹1L', label: '₹50,000 - ₹1L' },
    { value: '₹1L - ₹3L', label: '₹1L - ₹3L' },
    { value: '₹3L - ₹5L', label: '₹3L - ₹5L' },
    { value: 'Above ₹5L', label: t('above5L') }
  ];
  const predefinedValues = PREDEFINED_OPTIONS.map(o => o.value);
  const isCustomMode = data.investment !== '' && !predefinedValues.includes(data.investment);

  return (
    <div className="flex flex-col h-full bg-white rounded-3xl p-4 sm:p-6 border border-premium-border shadow-card relative overflow-hidden">
      <div className="flex-1 overflow-y-auto min-h-0 pr-2">
        <h2 className="text-[28px] font-bold text-forest-deep mb-1 font-display">{t('title')}</h2>
        <p className="text-ink-soft text-sm font-medium mb-4">
          {t('subtitle')}
        </p>

        <div className="space-y-4">
          {/* Investment Amount */}
          <div className="space-y-2">
            <label className="text-sm font-bold text-ink flex items-center">
              {t('investment')} <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <div className="flex flex-wrap gap-3">
              {PREDEFINED_OPTIONS.map(option => (
                <label key={option.value} className={`flex items-center px-4 py-2 rounded-xl border cursor-pointer transition-colors ${data.investment === option.value ? 'border-forest bg-forest-tint/30 text-forest-deep font-bold' : 'border-premium-border hover:bg-cream text-ink font-medium'}`}>
                  <input 
                    type="radio" 
                    name="investment" 
                    value={option.value}
                    className="mr-3 w-4 h-4 accent-forest"
                    checked={data.investment === option.value}
                    onChange={() => updateData({ investment: option.value })}
                  />
                  <span className="text-sm">{option.label}</span>
                </label>
              ))}
              <input 
                type="text"
                placeholder={t('investmentPlaceholder')}
                className={`w-full sm:w-64 rounded-xl border px-4 py-2 text-sm font-medium transition-colors focus:outline-none ${isCustomMode ? 'border-forest bg-forest-tint/30 text-forest-deep font-bold ring-1 ring-forest' : 'border-premium-border hover:bg-cream text-ink placeholder:text-ink-faint'}`}
                value={isCustomMode && data.investment !== 'Custom' ? data.investment : ''}
                onChange={(e) => updateData({ investment: e.target.value })}
                onFocus={() => {
                  if (!isCustomMode) updateData({ investment: 'Custom' });
                }}
              />
            </div>
          </div>
          
          {/* Primary Source */}
          <div className="space-y-2 pt-4">
            <label className="text-sm font-bold text-ink flex items-center">
              {t('source')} <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { id: 'Savings', label: t('sourceSavings'), desc: t('descSavings') },
                { id: 'Bank Loan', label: t('sourceLoan'), desc: t('descLoan') },
                { id: 'Govt Scheme', label: t('sourceGovt'), desc: t('descGovt') },
                { id: 'Friends/Relatives', label: t('sourceFriends'), desc: t('descFriends') },
              ].map(src => (
                <label key={src.id} className={`flex flex-col px-4 py-2 rounded-xl border cursor-pointer transition-colors ${data.source === src.id ? 'border-forest bg-forest-tint/30 text-forest-deep font-bold' : 'border-premium-border hover:bg-cream text-ink'}`}>
                  <div className="flex items-center">
                    <input 
                      type="radio" 
                      name="source" 
                      value={src.id}
                      className="mr-3 w-4 h-4 accent-forest"
                      checked={data.source === src.id}
                      onChange={() => updateData({ source: src.id })}
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
          className="bg-[#ea580c] hover:bg-[#c2410c] text-white px-8 py-2 rounded-xl text-sm font-bold flex items-center justify-center shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-saffron"
        >
          {tCommon('next')} <ArrowRight size={18} className="ml-2" />
        </button>
      </div>
    </div>
  );
}
