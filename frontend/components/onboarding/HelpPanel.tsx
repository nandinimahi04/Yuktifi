import React from 'react';
import { Target, MapPin, Calculator, ShieldAlert, User } from 'lucide-react';
import { useTranslations } from 'next-intl';

export function HelpPanel() {
  const t = useTranslations('onboarding.helpPanel');
  return (
    <div className="hidden lg:flex flex-col w-[320px] shrink-0 bg-[#f4f9f6] rounded-3xl overflow-hidden border border-[#e5f0ea]">
      {/* Top Graphic Area */}
      <div className="h-40 relative flex items-end justify-center pb-0 overflow-hidden bg-[#edf5f0]">
        <div className="absolute top-4 left-4 w-8 h-8 bg-[#cce3d8] rounded-full rounded-bl-none flex items-center justify-center">
          <User size={14} className="text-forest" />
        </div>
        
        {/* Decorative blob behind avatar */}
        <div className="absolute bottom-[-20px] w-48 h-32 bg-[#faebd7] rounded-t-full opacity-60 mix-blend-multiply blur-xl"></div>
        
        {/* Placeholder for actual avatar image, using a generic shape for now */}
        <div className="relative z-10 w-24 h-24 rounded-t-full bg-forest-deep flex items-center justify-center border-b-0 overflow-hidden">
          {/* Mock avatar features */}
          <div className="absolute top-4 w-10 h-10 rounded-full bg-[#fcd5ce]"></div>
          <div className="absolute bottom-0 w-16 h-12 rounded-t-[2rem] bg-forest"></div>
        </div>
      </div>
      
      {/* Content Area */}
      <div className="p-6 bg-[#f4f9f6] flex-1">
        <h3 className="text-[17px] leading-snug font-bold text-forest-deep mb-6">
          {t('title')}
        </h3>
        
        <div className="space-y-5">
          <div className="flex items-start">
            <div className="w-8 h-8 rounded-full bg-[#fdf5e6] flex items-center justify-center shrink-0 mr-4 border border-[#f5e6d3]">
              <Target size={14} className="text-saffron-deep" />
            </div>
            <p className="text-sm font-medium text-ink-soft leading-tight pt-1">
              {t('point1')}
            </p>
          </div>
          
          <div className="flex items-start">
            <div className="w-8 h-8 rounded-full bg-[#fdf5e6] flex items-center justify-center shrink-0 mr-4 border border-[#f5e6d3]">
              <MapPin size={14} className="text-forest" />
            </div>
            <p className="text-sm font-medium text-ink-soft leading-tight pt-1">
              {t('point2')}
            </p>
          </div>
          
          <div className="flex items-start">
            <div className="w-8 h-8 rounded-full bg-[#fdf5e6] flex items-center justify-center shrink-0 mr-4 border border-[#f5e6d3]">
              <Calculator size={14} className="text-ink" />
            </div>
            <p className="text-sm font-medium text-ink-soft leading-tight pt-1">
              {t('point3')}
            </p>
          </div>
          
          <div className="flex items-start">
            <div className="w-8 h-8 rounded-full bg-[#fdf5e6] flex items-center justify-center shrink-0 mr-4 border border-[#f5e6d3]">
              <ShieldAlert size={14} className="text-saffron" />
            </div>
            <p className="text-sm font-medium text-ink-soft leading-tight pt-1">
              {t('point4')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
