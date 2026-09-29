import React, { useState } from 'react';
import { ChevronLeft, ArrowRight, ChevronDown, Sparkles } from 'lucide-react';
import { useTranslations } from 'next-intl';

export interface BusinessData {
  industry: string;
  experience: string;
  ideaDetails: string;
  considerSimilar?: boolean;
}

interface StepBusinessProps {
  data: BusinessData;
  updateData: (updates: Partial<BusinessData>) => void;
  onNext: () => void;
  onBack: () => void;
}

const PREDEFINED_INDUSTRIES = [
  { value: 'Retail & Shop', label: 'Retail & Shop' },
  { value: 'Food & Beverage', label: 'Food & Beverage' },
  { value: 'Agri-Business & Farming', label: 'Agri-Business & Farming' },
  { value: 'Manufacturing & Processing', label: 'Manufacturing & Processing' },
  { value: 'Services & Tech', label: 'Services & Tech' },
  { value: 'Logistics & Transport', label: 'Logistics & Transport' },
  { value: 'Handicrafts & Artisanal', label: 'Handicrafts & Artisanal' },
  { value: 'Healthcare & Wellness', label: 'Healthcare & Wellness' },
  { value: 'Education & Training', label: 'Education & Training' },
  { value: 'Other', label: 'Other (Specify)' }
];

const SECTOR_SUGGESTIONS: Record<string, string[]> = {
  'Retail & Shop': [
    'Kirana / Grocery Store',
    'General Store',
    'Pooja Samagri Store',
    'Stationery & Xerox',
    'Supermarket & Mart'
  ],
  'Food & Beverage': [
    'Tea & Snacks Shop',
    'Vada Pav Center',
    'Bakery & Confectionery',
    'Juice & Milkshake Bar',
    'Fast Food & Chaat Stall'
  ],
  'Agri-Business & Farming': [
    'Dairy Farming & Milk Chilling',
    'Poultry Farm',
    'Organic Fertilizer & Vermicompost',
    'Goat Farming',
    'Cold Storage & Grading'
  ],
  'Manufacturing & Processing': [
    'Atta Chakki / Flour Mill',
    'Spices Grinding & Packaging',
    'Paper Bag Manufacturing',
    'Garment Stitching Unit',
    'Oil Extraction Mill'
  ],
  'Services & Tech': [
    'Mobile & Electronics Repair',
    'Two-Wheeler Service Garage',
    'Beauty & Hair Salon',
    'Diagnostic & Pathology Lab',
    'Solar Installation & Service'
  ],
  'Logistics & Transport': [
    'E-Rickshaw Passenger Fleet',
    'Local Parcel Delivery Service',
    'Mini Cargo Van Transport'
  ]
};

const POPULAR_ALL_SUGGESTIONS = [
  { name: 'Kirana / Grocery Store', sector: 'Retail & Shop' },
  { name: 'Tea & Snacks Shop', sector: 'Food & Beverage' },
  { name: 'Mobile Repair Shop', sector: 'Services & Tech' },
  { name: 'Dairy Farming', sector: 'Agri-Business & Farming' },
  { name: 'Atta Chakki / Flour Mill', sector: 'Manufacturing & Processing' },
  { name: 'E-Rickshaw Transport', sector: 'Logistics & Transport' }
];

const EXPERIENCE_OPTIONS = [
  { value: 'None, I am a beginner', label: 'None, I am a beginner' },
  { value: '1–3 Years', label: '1–3 Years' },
  { value: '3–5 Years', label: '3–5 Years' },
  { value: '5+ Years', label: '5+ Years' }
];

export function StepBusiness({ data, updateData, onNext, onBack }: StepBusinessProps) {
  const t = useTranslations('onboarding.step4');
  const tCommon = useTranslations('common');

  const currentSuggestions = data.industry && SECTOR_SUGGESTIONS[data.industry]
    ? SECTOR_SUGGESTIONS[data.industry]
    : [];

  const handleSelectSuggestion = (ideaName: string, sectorName?: string) => {
    updateData({
      ideaDetails: ideaName,
      ...(sectorName ? { industry: sectorName } : {})
    });
  };

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
          {/* Industry / Sector Dropdown */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-ink flex items-center">
              Industry / Sector <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <div className="relative">
              <select
                className="w-full rounded-xl border border-premium-border px-4 py-2.5 text-sm text-ink bg-white appearance-none focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all cursor-pointer font-medium"
                value={data.industry || ""}
                onChange={(e) => updateData({ industry: e.target.value })}
              >
                <option value="" disabled>Select a sector</option>
                {PREDEFINED_INDUSTRIES.map(ind => (
                  <option key={ind.value} value={ind.value}>{ind.label}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-4 top-3 text-ink-soft pointer-events-none" size={18} />
            </div>
          </div>

          {/* Dynamic Suggestion Ideas based on sector or popular recommendations */}
          <div className="space-y-1.5 pt-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold uppercase tracking-wider text-forest-deep flex items-center">
                <Sparkles size={13} className="text-forest mr-1" />
                Suggested Ideas {data.industry ? `for ${data.industry}` : ''}
              </label>
              <span className="text-[11px] text-ink-soft font-medium">Click to auto-fill</span>
            </div>

            <div className="flex flex-wrap gap-2">
              {currentSuggestions.length > 0 ? (
                currentSuggestions.map(idea => {
                  const isSelected = data.ideaDetails === idea;
                  return (
                    <button
                      type="button"
                      key={idea}
                      onClick={() => handleSelectSuggestion(idea)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        isSelected
                          ? 'bg-forest text-white shadow-xs'
                          : 'bg-cream text-ink border border-premium-border hover:border-forest/50 hover:bg-forest-tint/30'
                      }`}
                    >
                      {idea}
                    </button>
                  );
                })
              ) : (
                POPULAR_ALL_SUGGESTIONS.map(item => {
                  const isSelected = data.ideaDetails === item.name;
                  return (
                    <button
                      type="button"
                      key={item.name}
                      onClick={() => handleSelectSuggestion(item.name, item.sector)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        isSelected
                          ? 'bg-forest text-white shadow-xs'
                          : 'bg-cream text-ink border border-premium-border hover:border-forest/50 hover:bg-forest-tint/30'
                      }`}
                    >
                      {item.name}
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {/* Specific Idea (Optional) */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-ink flex items-center">
              Specific Idea (Optional)
            </label>
            <textarea 
              rows={2}
              placeholder="e.g. I want to open a small grocery store near the bus stand..."
              className="w-full rounded-xl border border-premium-border px-4 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all resize-none font-medium"
              value={data.ideaDetails || ''}
              onChange={(e) => updateData({ ideaDetails: e.target.value })}
            />
          </div>

          {/* Prior Experience */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-ink flex items-center">
              Prior Experience <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {EXPERIENCE_OPTIONS.map(opt => {
                const isSelected = data.experience === opt.value;
                return (
                  <label 
                    key={opt.value} 
                    className={`flex items-center px-3 py-2 rounded-xl border cursor-pointer transition-all ${
                      isSelected 
                        ? 'border-forest bg-forest-tint/30 text-forest-deep font-bold ring-1 ring-forest' 
                        : 'border-premium-border hover:bg-cream/60 text-ink font-medium'
                    }`}
                  >
                    <input 
                      type="radio" 
                      name="experience" 
                      value={opt.value}
                      className="mr-2 w-3.5 h-3.5 accent-forest"
                      checked={isSelected}
                      onChange={() => updateData({ experience: opt.value })}
                    />
                    <span className="text-xs">{opt.label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Consider Similar Businesses Checkbox */}
          <label className="flex items-start gap-3 p-3 rounded-2xl border border-premium-border/80 bg-cream/40 cursor-pointer hover:bg-cream/70 transition-colors">
            <input 
              type="checkbox"
              className="mt-0.5 w-4 h-4 rounded text-forest accent-forest"
              checked={data.considerSimilar ?? true}
              onChange={(e) => updateData({ considerSimilar: e.target.checked })}
            />
            <div className="flex flex-col">
              <span className="text-xs font-bold text-ink">Consider similar businesses?</span>
              <span className="text-[11px] text-ink-soft leading-tight mt-0.5">
                Would you like YuktiFi to also evaluate alternative business ideas similar to your choice?
              </span>
            </div>
          </label>

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
          disabled={!data.industry}
          className="bg-[#ea580c] hover:bg-[#c2410c] text-white px-7 py-2.5 rounded-xl text-sm font-bold flex items-center justify-center shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#ea580c] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {tCommon('next')} <ArrowRight size={18} className="ml-2" />
        </button>
      </div>
    </div>
  );
}
