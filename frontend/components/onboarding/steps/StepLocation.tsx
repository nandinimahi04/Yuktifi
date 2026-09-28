import React, { useState, useEffect } from 'react';
import { ChevronLeft, ArrowRight, MapPin } from 'lucide-react';
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

export function StepLocation({ data, updateData, onNext, onBack }: StepLocationProps) {
  const t = useTranslations('onboarding.step2');
  const tCommon = useTranslations('common');
  
  const [states, setStates] = useState<{id: string, name: string}[]>([]);
  const [districts, setDistricts] = useState<{id: string, name: string}[]>([]);
  const [selectedStateId, setSelectedStateId] = useState<string>('');
  
  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/locations/states`)
      .then(res => res.json())
      .then(data => setStates(data))
      .catch(err => console.error("Failed to load states:", err));
  }, []);

  useEffect(() => {
    if (selectedStateId) {
      fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/locations/districts?state_id=${selectedStateId}`)
        .then(res => res.json())
        .then(data => setDistricts(data))
        .catch(err => console.error("Failed to load districts:", err));
    } else {
      setDistricts([]);
    }
  }, [selectedStateId]);

  const handleStateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const name = e.target.value;
    const stateObj = states.find(s => s.name === name);
    setSelectedStateId(stateObj ? stateObj.id : '');
    updateData({ state: name, district: '' });
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
              {t('state')} <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <select 
              className="w-full rounded-xl border border-premium-border px-4 py-2 text-ink focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all bg-white"
              value={data.state}
              onChange={handleStateChange}
            >
              <option value="">{t('stateSelect')}</option>
              {states.map(s => (
                <option key={s.id} value={s.name}>{s.name}</option>
              ))}
            </select>
          </div>
          
          <div className="space-y-2">
            <label className="text-sm font-bold text-ink flex items-center">
              {t('district')} <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <select 
              className="w-full rounded-xl border border-premium-border px-4 py-2 text-ink focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all bg-white disabled:opacity-50"
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

          <div className="space-y-2">
            <label className="text-sm font-bold text-ink flex items-center">
              {t('village')}
            </label>
            <div className="relative">
              <input 
                type="text"
                placeholder={t('villagePlaceholder')}
                className="w-full rounded-xl border border-premium-border px-4 py-2 text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all"
                value={data.village}
                onChange={(e) => updateData({ village: e.target.value })}
              />
              <MapPin className="absolute right-3 top-2.5 text-ink-soft" size={18} />
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
