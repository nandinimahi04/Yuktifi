import React from 'react';
import { Calendar, User, Users, ChevronLeft, ArrowRight, Lightbulb } from 'lucide-react';
import { useTranslations } from 'next-intl';

export interface AboutYouData {
  fullName: string;
  age: string;
  gender: string;
  category: string;
}

interface StepAboutYouProps {
  data: AboutYouData;
  updateData: (updates: Partial<AboutYouData>) => void;
  onNext: () => void;
  onBack: () => void;
}

export function StepAboutYou({ data, updateData, onNext, onBack }: StepAboutYouProps) {
  const t = useTranslations('onboarding.step1');
  const tCommon = useTranslations('common');

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

        <div className="space-y-5">
          {/* Row 1: Name and Age */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-ink flex items-center">
                {t('fullName')} <span className="text-[#ea580c] ml-1">*</span>
              </label>
              <input 
                type="text"
                placeholder={t('namePlaceholder')}
                className="w-full rounded-xl border border-premium-border px-4 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all"
                value={data.fullName}
                onChange={(e) => updateData({ fullName: e.target.value })}
              />
            </div>
            
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-ink flex items-center">
                {t('age')} <span className="text-[#ea580c] ml-1">*</span>
              </label>
              <div className="relative">
                <input 
                  type="number"
                  placeholder={t('agePlaceholder')}
                  className="w-full rounded-xl border border-premium-border px-4 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all pr-10"
                  value={data.age}
                  onChange={(e) => updateData({ age: e.target.value })}
                />
                <Calendar className="absolute right-3.5 top-3 text-ink-soft pointer-events-none" size={18} />
              </div>
            </div>
          </div>

          {/* Gender */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-ink">{t('gender')}</label>
            <div className="flex flex-wrap gap-3">
              {[
                { label: t('male'), value: 'Male' },
                { label: t('female'), value: 'Female' },
                { label: t('other'), value: 'Other' }
              ].map(option => {
                const isChecked = data.gender === option.value;
                return (
                  <label 
                    key={option.value} 
                    className={`flex items-center px-4 py-2.5 rounded-xl border cursor-pointer transition-all ${
                      isChecked 
                        ? 'border-forest bg-forest-tint/30 text-forest-deep font-bold ring-1 ring-forest' 
                        : 'border-premium-border hover:bg-cream/60 text-ink font-medium'
                    }`}
                  >
                    <input 
                      type="radio" 
                      name="gender" 
                      value={option.value}
                      className="mr-2.5 w-4 h-4 accent-forest"
                      checked={isChecked}
                      onChange={() => updateData({ gender: option.value })}
                    />
                    <span className="text-sm">{option.label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Social Category */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-ink flex items-center">
              {t('socialCategory')} <span className="text-[#ea580c] ml-1">*</span>
            </label>
            <div className="grid grid-cols-5 gap-2.5">
              {[
                { id: 'SC', bg: 'bg-[#fff5f0]', border: 'border-[#ffecd9]', activeRing: 'ring-[#ea580c]', iconBg: 'bg-[#ffe4cc]', text: 'text-[#cc4d00]', icon: User },
                { id: 'ST', bg: 'bg-[#f2f9f4]', border: 'border-[#e0efe5]', activeRing: 'ring-[#16a34a]', iconBg: 'bg-[#d1e8d9]', text: 'text-[#166534]', icon: Users },
                { id: 'OBC', bg: 'bg-[#faf5ff]', border: 'border-[#f3e8ff]', activeRing: 'ring-[#9333ea]', iconBg: 'bg-[#e9d5ff]', text: 'text-[#6b21a8]', icon: Lightbulb },
                { id: 'General', bg: 'bg-[#f0f7ff]', border: 'border-[#e0f2fe]', activeRing: 'ring-[#0284c7]', iconBg: 'bg-[#bae6fd]', text: 'text-[#0369a1]', icon: User },
                { id: 'Other', bg: 'bg-[#fffbeb]', border: 'border-[#fef3c7]', activeRing: 'ring-[#d97706]', iconBg: 'bg-[#fde68a]', text: 'text-[#b45309]', textLabel: t('other'), icon: Lightbulb }
              ].map(cat => {
                const Icon = cat.icon;
                const isSelected = data.category === cat.id;
                return (
                  <button
                    type="button"
                    key={cat.id}
                    onClick={() => updateData({ category: cat.id })}
                    className={`flex flex-col items-center justify-center py-3 px-1 rounded-2xl border transition-all ${
                      isSelected 
                        ? `ring-2 ${cat.activeRing} ${cat.border} ${cat.bg} shadow-sm font-black` 
                        : `${cat.bg} border-transparent hover:${cat.border} opacity-85 hover:opacity-100`
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-full ${cat.iconBg} flex items-center justify-center mb-1.5 shadow-xs`}>
                      <Icon size={16} className={cat.text} />
                    </div>
                    <span className={`text-[11px] font-bold ${isSelected ? 'text-ink font-black' : 'text-ink-soft'}`}>
                      {cat.textLabel || cat.id}
                    </span>
                  </button>
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
          disabled={!data.fullName || !data.age || !data.gender || !data.category}
          className="bg-[#ea580c] hover:bg-[#c2410c] text-white px-7 py-2.5 rounded-xl text-sm font-bold flex items-center justify-center shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#ea580c] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {tCommon('next')} <ArrowRight size={18} className="ml-2" />
        </button>
      </div>
    </div>
  );
}
