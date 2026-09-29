import React from 'react';
import { ChevronLeft, ArrowRight, CheckCircle2, Loader2 } from 'lucide-react';
import { AboutYouData } from './StepAboutYou';
import { LocationData } from './StepLocation';
import { CapitalData } from './StepCapital';
import { BusinessData } from './StepBusiness';
import { useTranslations } from 'next-intl';

interface StepReviewProps {
  data: {
    about: AboutYouData;
    location: LocationData;
    capital: CapitalData;
    business: BusinessData;
  };
  onNext: () => void;
  onBack: () => void;
  isSubmitting: boolean;
}

export function StepReview({ data, onNext, onBack, isSubmitting }: StepReviewProps) {
  const t = useTranslations('onboarding.step5');
  const tCommon = useTranslations('common');

  const formatCapital = (val?: string) => {
    if (!val) return '-';
    const num = Number(val);
    if (isNaN(num) || num <= 0) return val;
    return `₹${num.toLocaleString('en-IN')}`;
  };

  const finalInvestment = data.capital.customInvestment 
    ? data.capital.customInvestment 
    : data.capital.investment;

  return (
    <div className="flex flex-col h-full bg-white rounded-3xl p-6 sm:p-8 border border-premium-border shadow-card relative overflow-hidden justify-between">
      <div className="flex-1 overflow-y-auto min-h-0 pr-1 space-y-5">
        <div>
          <h2 className="text-2xl sm:text-[28px] font-bold text-forest-deep mb-1 font-display tracking-tight">
            {t('title')}
          </h2>
          <p className="text-ink-soft text-sm font-medium">
            {t('subtitle')}
          </p>
        </div>

        <div className="space-y-4">
          {/* Personal Profile Box */}
          <div className="bg-[#f6eee3] p-5 rounded-2xl border border-[#ebdccb]">
            <h4 className="text-[11px] font-bold uppercase tracking-wider text-ink-soft mb-3">
              PERSONAL PROFILE
            </h4>
            <div className="grid grid-cols-[140px_1fr] gap-y-2 text-xs sm:text-sm">
              <span className="text-ink-soft font-medium">Name:</span>
              <span className="font-bold text-ink">{data.about.fullName || '-'}</span>
              
              <span className="text-ink-soft font-medium">Age:</span>
              <span className="font-bold text-ink">{data.about.age || '-'}</span>
              
              <span className="text-ink-soft font-medium">Social Category:</span>
              <span className="font-bold text-ink">{data.about.category || '-'}</span>
            </div>
          </div>

          {/* Location & Capital Box */}
          <div className="bg-[#f6eee3] p-5 rounded-2xl border border-[#ebdccb]">
            <h4 className="text-[11px] font-bold uppercase tracking-wider text-ink-soft mb-3">
              LOCATION & CAPITAL
            </h4>
            <div className="grid grid-cols-[140px_1fr] gap-y-2 text-xs sm:text-sm">
              <span className="text-ink-soft font-medium">District:</span>
              <span className="font-bold text-ink">
                {data.location.district ? `${data.location.district}, ${data.location.state}` : '-'}
              </span>
              
              <span className="text-ink-soft font-medium">Investment:</span>
              <span className="font-bold text-ink">{formatCapital(finalInvestment)}</span>
              
              <span className="text-ink-soft font-medium">Interest:</span>
              <span className="font-bold text-ink">
                {data.business.ideaDetails || data.business.industry || '-'}
              </span>
            </div>
          </div>
          
          {/* Agreement Box */}
          <div className="flex items-start p-4 bg-emerald-50/70 rounded-2xl border border-emerald-200">
            <CheckCircle2 size={18} className="text-emerald-700 mt-0.5 mr-3 shrink-0" />
            <p className="text-xs sm:text-sm text-forest-deep font-medium leading-relaxed">
              By proceeding, you agree to let YuktiFi analyze your data to generate business insights.
            </p>
          </div>
        </div>
      </div>

      {/* Footer Nav */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-premium-border">
        <button 
          type="button"
          onClick={onBack}
          disabled={isSubmitting}
          className="flex items-center text-ink-soft hover:text-ink font-bold text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron rounded px-2 py-1 disabled:opacity-50"
        >
          <ChevronLeft size={18} className="mr-1" /> {tCommon('back')}
        </button>
        
        <button 
          type="button"
          onClick={onNext}
          disabled={isSubmitting}
          className="bg-[#2d5a43] hover:bg-[#234734] text-white px-8 py-2.5 rounded-xl text-sm font-bold flex items-center justify-center shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-forest disabled:opacity-70"
        >
          {isSubmitting ? (
            <><Loader2 className="animate-spin mr-2" size={18} /> Processing...</>
          ) : (
            <>Generate My Analysis <ArrowRight size={18} className="ml-2" /></>
          )}
        </button>
      </div>
    </div>
  );
}
