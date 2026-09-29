import React from 'react';
import { Target, MapPin, Calculator, ShieldCheck, User } from 'lucide-react';
import { useTranslations } from 'next-intl';

export function HelpPanel() {
  const t = useTranslations('onboarding.helpPanel');
  
  return (
    <div className="hidden lg:flex flex-col w-[320px] shrink-0 bg-[#f0f8f4] rounded-3xl overflow-hidden border border-[#d6ebe0] shadow-sm">
      {/* Top Graphic Area */}
      <div className="h-36 relative flex items-end justify-center pb-0 overflow-hidden bg-[#e4f2eb]">
        <div className="absolute top-4 left-4 w-7 h-7 bg-[#c2e2d2] rounded-full flex items-center justify-center">
          <User size={14} className="text-forest" />
        </div>
        
        {/* Stylized Avatar Illustration matching screenshots */}
        <div className="relative z-10 w-24 h-24 rounded-t-full bg-[#1b4332] flex flex-col items-center justify-end overflow-hidden pt-3">
          <div className="w-10 h-10 rounded-full bg-[#fcd5ce] mb-1"></div>
          <div className="w-16 h-10 rounded-t-2xl bg-[#2d6a4f]"></div>
        </div>
      </div>
      
      {/* Content Area */}
      <div className="p-6 bg-[#f0f8f4] flex-1 flex flex-col justify-between">
        <div>
          <h3 className="text-base font-bold text-forest-deep mb-6 font-display leading-snug">
            Your details help us find the best opportunities for you.
          </h3>
          
          <div className="space-y-4">
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-full bg-[#ffedd5] flex items-center justify-center shrink-0 mr-3 border border-[#fed7aa]">
                <Target size={15} className="text-[#ea580c]" />
              </div>
              <p className="text-xs font-semibold text-ink leading-tight">
                Personalised business recommendations
              </p>
            </div>
            
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-full bg-[#dcfce7] flex items-center justify-center shrink-0 mr-3 border border-[#bbf7d0]">
                <MapPin size={15} className="text-forest" />
              </div>
              <p className="text-xs font-semibold text-ink leading-tight">
                Location-based market analysis
              </p>
            </div>
            
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-full bg-[#fef3c7] flex items-center justify-center shrink-0 mr-3 border border-[#fde68a]">
                <Calculator size={15} className="text-[#b45309]" />
              </div>
              <p className="text-xs font-semibold text-ink leading-tight">
                Financial planning & loan guidance
              </p>
            </div>
            
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-full bg-[#ffedd5] flex items-center justify-center shrink-0 mr-3 border border-[#fed7aa]">
                <ShieldCheck size={15} className="text-[#ea580c]" />
              </div>
              <p className="text-xs font-semibold text-ink leading-tight">
                Better risk assessment
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
