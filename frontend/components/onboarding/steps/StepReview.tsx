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
  
  // Create a helper for mapping the English predefined values to localized labels
  const tStep3 = useTranslations('onboarding.step3');
  const tStep4 = useTranslations('onboarding.step4');
  
  const PREDEFINED_CAPITAL: Record<string, string> = {
    'Under ₹50,000': tStep3('under50k'),
    'Above ₹5L': tStep3('above5L')
  };
  
  const PREDEFINED_INDUSTRIES: Record<string, string> = {
    'Retail & Shop': tStep4('indRetail'),
    'Manufacturing': tStep4('indMfg'),
    'Agri-Business': tStep4('indAgri'),
    'Services & Tech': tStep4('indServices'),
    'Food & Beverage': tStep4('indFood'),
    'Handicrafts & Artisanal': tStep4('indCrafts'),
    'Logistics & Delivery': tStep4('indLogistics'),
    'Education & Training': tStep4('indEdu'),
    'Healthcare & Wellness': tStep4('indHealth'),
    'Fashion & Apparel': tStep4('indFashion')
  };

  const getCapitalLabel = (val: string) => PREDEFINED_CAPITAL[val] || val;
  const getIndustryLabel = (val: string) => PREDEFINED_INDUSTRIES[val] || val;

  return (
    <div className="flex flex-col h-full bg-white rounded-3xl p-4 sm:p-6 border border-premium-border shadow-card relative overflow-hidden">
      <div className="flex-1 overflow-y-auto min-h-0 pr-2">
        <h2 className="text-[28px] font-bold text-forest-deep mb-1 font-display">{t('title')}</h2>
        <p className="text-ink-soft text-sm font-medium mb-4">
          {t('subtitle')}
        </p>

        <div className="space-y-4">
          <div className="bg-cream-deep p-4 rounded-2xl border border-premium-border">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-faint mb-3">{t('personalProfile')}</h4>
            <div className="grid grid-cols-2 gap-y-2 text-sm">
              <span className="text-ink-soft">{t('name')}:</span>
              <span className="font-bold text-ink">{data.about.fullName || '-'}</span>
              <span className="text-ink-soft">{t('age')}:</span>
              <span className="font-bold text-ink">{data.about.age || '-'}</span>
              <span className="text-ink-soft">{t('category')}:</span>
              <span className="font-bold text-ink">{data.about.category || '-'}</span>
            </div>
          </div>

          <div className="bg-cream-deep p-4 rounded-2xl border border-premium-border">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-faint mb-3">{t('locationCapital')}</h4>
            <div className="grid grid-cols-2 gap-y-2 text-sm">
              <span className="text-ink-soft">{t('district')}:</span>
              <span className="font-bold text-ink">{data.location.district || '-'}, {data.location.state || '-'}</span>
              <span className="text-ink-soft">{t('investment')}:</span>
              <span className="font-bold text-ink">{getCapitalLabel(data.capital.investment) || '-'}</span>
              <span className="text-ink-soft">{t('interest')}:</span>
              <span className="font-bold text-ink">{getIndustryLabel(data.business.industry) || '-'}</span>
            </div>
          </div>
          
          <div className="flex items-start p-4 bg-forest-tint/30 rounded-2xl border border-forest/20 mt-4">
            <CheckCircle2 size={20} className="text-forest mt-0.5 mr-3 shrink-0" />
            <p className="text-sm text-forest-deep font-medium leading-relaxed">
              {t('agreement')}
            </p>
          </div>
        </div>
      </div>

      {/* Footer Nav */}
      <div className="flex items-center justify-between mt-4 pt-4 border-t border-premium-border">
        <button 
          onClick={onBack}
          disabled={isSubmitting}
          className="flex items-center text-ink-soft hover:text-ink font-bold text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron rounded px-2 py-1 disabled:opacity-50"
        >
          <ChevronLeft size={18} className="mr-1" /> {tCommon('back')}
        </button>
        
        <button 
          onClick={onNext}
          disabled={isSubmitting}
          className="bg-forest hover:bg-forest-deep text-white px-8 py-2 rounded-xl text-sm font-bold flex items-center justify-center shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-forest disabled:opacity-70"
        >
          {isSubmitting ? (
            <><Loader2 className="animate-spin mr-2" size={18} /> {t('processing')}</>
          ) : (
            <>{t('generateBtn')} <ArrowRight size={18} className="ml-2" /></>
          )}
        </button>
      </div>
    </div>
  );
}
