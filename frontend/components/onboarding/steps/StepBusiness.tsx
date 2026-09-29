import React, { useState, useEffect } from 'react';
import { ChevronLeft, ArrowRight, ChevronDown, Lightbulb, Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';

export interface BusinessData {
  industry: string;
  experience: string;
  ideaDetails: string;
}

interface StepBusinessProps {
  data: BusinessData;
  updateData: (updates: Partial<BusinessData>) => void;
  onNext: () => void;
  onBack: () => void;
}

export function StepBusiness({ data, updateData, onNext, onBack }: StepBusinessProps) {
  const t = useTranslations('onboarding.step4');
  const tCommon = useTranslations('common');
  
  const PREDEFINED_INDUSTRIES = [
    { value: 'Retail & Shop', label: t('indRetail') },
    { value: 'Manufacturing', label: t('indMfg') },
    { value: 'Agri-Business', label: t('indAgri') },
    { value: 'Services & Tech', label: t('indServices') },
    { value: 'Food & Beverage', label: t('indFood') },
    { value: 'Handicrafts & Artisanal', label: t('indCrafts') },
    { value: 'Logistics & Delivery', label: t('indLogistics') },
    { value: 'Education & Training', label: t('indEdu') },
    { value: 'Healthcare & Wellness', label: t('indHealth') },
    { value: 'Fashion & Apparel', label: t('indFashion') },
    { value: 'Other', label: t('otherSpecify') }
  ];
  
  const [matchResult, setMatchResult] = useState<{ detected_business: string | null, category: string | null, confidence: number } | null>(null);
  const [isMatching, setIsMatching] = useState(false);
  const [typingTimeout, setTypingTimeout] = useState<NodeJS.Timeout | null>(null);

  const runMatcher = async (text: string) => {
    if (!text.trim()) {
      setMatchResult(null);
      return;
    }
    setIsMatching(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/business/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      if (res.ok) {
        const data = await res.json();
        setMatchResult(data);
      }
    } catch (err) {
      console.error("Failed to match business", err);
    } finally {
      setIsMatching(false);
    }
  };

  const handleIdeaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    updateData({ ideaDetails: val });
    
    if (typingTimeout) clearTimeout(typingTimeout);
    setTypingTimeout(setTimeout(() => {
      runMatcher(val);
    }, 800));
  };
  
  const applyMatch = () => {
    if (matchResult && matchResult.category) {
      // Find the label in English or just use the mapped predefined if matches logic.
      // We rely on mapping the raw id to the select option.
      const matchMap: Record<string, string> = {
        "retail_shop": "Retail & Shop",
        "manufacturing": "Manufacturing",
        "agri_business": "Agri-Business",
        "services_tech": "Services & Tech",
        "food_beverage": "Food & Beverage",
        "handicrafts_artisanal": "Handicrafts & Artisanal",
        "logistics_delivery": "Logistics & Delivery",
        "education_training": "Education & Training",
        "healthcare_wellness": "Healthcare & Wellness",
        "fashion_apparel": "Fashion & Apparel"
      };
      const industryValue = matchMap[matchResult.category];
      if (industryValue) {
        updateData({ industry: industryValue });
      }
    }
  };
  
  return (
    <div className="flex flex-col h-full bg-white rounded-3xl p-4 sm:p-6 border border-premium-border shadow-card relative overflow-hidden">
      <div className="flex-1 overflow-y-auto min-h-0 pr-2">
        <h2 className="text-[28px] font-bold text-forest-deep mb-1 font-display">{t('title')}</h2>
        <p className="text-ink-soft text-sm font-medium mb-4">
          {t('subtitle')}
        </p>

        <div className="space-y-4">
          
          <div className="space-y-2">
            <label className="text-sm font-bold text-ink flex items-center">
              What business do you want to start? <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <textarea 
              rows={3}
              placeholder={t('ideaPlaceholder')}
              className="w-full rounded-xl border border-premium-border px-4 py-2 text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all resize-none"
              value={data.ideaDetails || ''}
              onChange={handleIdeaChange}
            />
          </div>
          
          {data.ideaDetails && (
            <div className="bg-cream-deep p-3 rounded-xl border border-premium-border">
              {isMatching ? (
                <div className="flex items-center text-sm text-ink-soft">
                  <Loader2 className="animate-spin mr-2" size={16} /> Analyzing your idea...
                </div>
              ) : matchResult ? (
                matchResult.confidence > 0 ? (
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="text-sm">
                      <span className="text-ink-soft">Detected:</span> <span className="font-bold text-ink">{matchResult.detected_business}</span> <span className="text-ink-soft mx-1">·</span>
                      <span className="text-ink-soft">Confidence:</span> <span className="font-bold text-ink">{Math.round(matchResult.confidence * 100)}%</span>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={applyMatch} className="px-3 py-1 bg-forest text-white text-xs font-bold rounded-lg hover:bg-forest-deep transition">Use this</button>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-ink-soft">
                    We couldn't match this automatically, please choose a category below.
                  </div>
                )
              ) : null}
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-bold text-ink flex items-center">
              {t('industry')} <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <div className="relative">
              <select
                className="w-full rounded-xl border border-premium-border px-4 py-2 text-ink bg-white appearance-none focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all cursor-pointer font-medium"
                value={data.industry || ""}
                onChange={(e) => updateData({ industry: e.target.value })}
              >
                <option value="" disabled>{t('selectIndustry')}</option>
                {PREDEFINED_INDUSTRIES.map(ind => (
                  <option key={ind.value} value={ind.value}>{ind.label}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-4 top-2.5 text-ink-soft pointer-events-none" size={20} />
            </div>
          </div>
          
          <div className="space-y-2 pt-4">
            <label className="text-sm font-bold text-ink flex items-center">
              {t('experience')}
            </label>
            <div className="flex flex-wrap gap-2">
              {[
                { value: 'None', label: t('expNone') },
                { value: 'Some', label: 'Some Experience' },
                { value: 'Experienced', label: 'Experienced' },
                { value: 'Prefer not to say', label: 'Prefer not to say' }
              ].map(option => (
                <label key={option.value} className={`flex items-center px-4 py-2 rounded-xl border cursor-pointer transition-colors ${data.experience === option.value ? 'border-forest bg-forest-tint/30 text-forest-deep font-bold' : 'border-premium-border hover:bg-cream text-ink font-medium'}`}>
                  <input 
                    type="radio" 
                    name="experience" 
                    value={option.value}
                    className="mr-3 w-4 h-4 accent-forest"
                    checked={data.experience === option.value}
                    onChange={() => updateData({ experience: option.value })}
                  />
                  <span className="text-sm">{option.label}</span>
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
          disabled={!data.industry && !data.ideaDetails}
          className="bg-[#ea580c] hover:bg-[#c2410c] text-white px-8 py-2 rounded-xl text-sm font-bold flex items-center justify-center shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-saffron disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {tCommon('next')} <ArrowRight size={18} className="ml-2" />
        </button>
      </div>
    </div>
  );
}
