import React, { useState, useEffect } from 'react';
import { ChevronLeft, ArrowRight, MapPin, Info } from 'lucide-react';
import { useTranslations } from 'next-intl';

export interface LocationData {
  state: string;
  district: string;
  village: string;
}

interface StepLocationProps {
  data: LocationData;
  updateData: (updates: Partial<LocationData>) => void;
  onNext: () => void;
  onBack: () => void;
}

const DEFAULT_STATES = [
  { id: "MH", name: "Maharashtra" },
  { id: "GJ", name: "Gujarat" },
  { id: "KA", name: "Karnataka" },
  { id: "MP", name: "Madhya Pradesh" },
  { id: "RJ", name: "Rajasthan" },
  { id: "UP", name: "Uttar Pradesh" },
  { id: "TN", name: "Tamil Nadu" },
  { id: "TS", name: "Telangana" },
  { id: "AP", name: "Andhra Pradesh" },
  { id: "DL", name: "Delhi" }
];

const DEFAULT_DISTRICTS: Record<string, { id: string; name: string }[]> = {
  "Maharashtra": [
    { id: "MH_SOL", name: "Solapur" },
    { id: "MH_PUN", name: "Pune" },
    { id: "MH_MUM", name: "Mumbai" },
    { id: "MH_NSK", name: "Nashik" },
    { id: "MH_KOL", name: "Kolhapur" },
    { id: "MH_AUR", name: "Chhatrapati Sambhajinagar (Aurangabad)" },
    { id: "MH_SAT", name: "Satara" },
    { id: "MH_NAG", name: "Nagpur" },
    { id: "MH_SAN", name: "Sangli" },
    { id: "MH_AHM", name: "Ahilyanagar (Ahmednagar)" }
  ],
  "Gujarat": [
    { id: "GJ_AMD", name: "Ahmedabad" },
    { id: "GJ_SUR", name: "Surat" },
    { id: "GJ_VAD", name: "Vadodara" },
    { id: "GJ_RAI", name: "Rajkot" }
  ],
  "Karnataka": [
    { id: "KA_BLR", name: "Bengaluru" },
    { id: "KA_MYS", name: "Mysuru" },
    { id: "KA_HUB", name: "Hubballi-Dharwad" },
    { id: "KA_BEL", name: "Belagavi" }
  ]
};

export function StepLocation({ data, updateData, onNext, onBack }: StepLocationProps) {
  const t = useTranslations('onboarding.step2');
  const tCommon = useTranslations('common');
  
  const [states, setStates] = useState<{id: string, name: string}[]>(DEFAULT_STATES);
  const [districts, setDistricts] = useState<{id: string, name: string}[]>(
    DEFAULT_DISTRICTS[data.state || "Maharashtra"] || DEFAULT_DISTRICTS["Maharashtra"]
  );

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/locations/states`)
      .then(res => {
        if (!res.ok) throw new Error("States API error");
        return res.json();
      })
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setStates(data);
        }
      })
      .catch(() => {
        // Fallback to DEFAULT_STATES
      });
  }, []);

  const handleStateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedStateName = e.target.value;
    const districtList = DEFAULT_DISTRICTS[selectedStateName] || [
      { id: `${selectedStateName}_1`, name: `Central ${selectedStateName}` },
      { id: `${selectedStateName}_2`, name: `North ${selectedStateName}` }
    ];
    setDistricts(districtList);
    updateData({ 
      state: selectedStateName, 
      district: districtList[0]?.name || '' 
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

        <div className="space-y-4">
          {/* State Select */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-ink flex items-center">
              {t('state')} <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <select 
              className="w-full rounded-xl border border-premium-border px-4 py-2.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all bg-white font-medium cursor-pointer"
              value={data.state}
              onChange={handleStateChange}
            >
              <option value="">{t('stateSelect')}</option>
              {states.map(s => (
                <option key={s.id} value={s.name}>{s.name}</option>
              ))}
            </select>
          </div>
          
          {/* District Select */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-ink flex items-center">
              {t('district')} <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <select 
              className="w-full rounded-xl border border-premium-border px-4 py-2.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all bg-white font-medium cursor-pointer disabled:opacity-50"
              value={data.district}
              onChange={(e) => updateData({ district: e.target.value })}
              disabled={!data.state}
            >
              <option value="">{t('districtSelect')}</option>
              {districts.map(d => (
                <option key={d.id} value={d.name}>{d.name}</option>
              ))}
            </select>
          </div>

          {/* Village / Taluka / City */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-ink flex items-center">
              {t('village')}
            </label>
            <div className="relative">
              <input 
                type="text"
                placeholder={t('villagePlaceholder')}
                className="w-full rounded-xl border border-premium-border px-4 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all pr-10"
                value={data.village}
                onChange={(e) => updateData({ village: e.target.value })}
              />
              <MapPin className="absolute right-3.5 top-3 text-ink-soft pointer-events-none" size={18} />
            </div>
          </div>

          {/* Demo coverage banner */}
          <div className="bg-[#fef9ee] border border-[#f5e6cb] rounded-xl px-4 py-3 flex items-center gap-2.5 text-xs text-[#854d0e] font-medium mt-2">
            <div className="w-5 h-5 rounded-full bg-[#0284c7] text-white flex items-center justify-center shrink-0 text-[11px] font-bold">
              i
            </div>
            <span>Demo coverage area: <strong>Solapur District, Maharashtra</strong></span>
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
          disabled={!data.state || !data.district}
          className="bg-[#ea580c] hover:bg-[#c2410c] text-white px-7 py-2.5 rounded-xl text-sm font-bold flex items-center justify-center shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#ea580c] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {tCommon('next')} <ArrowRight size={18} className="ml-2" />
        </button>
      </div>
    </div>
  );
}
