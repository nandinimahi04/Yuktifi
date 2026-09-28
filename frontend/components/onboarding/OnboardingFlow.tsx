"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Stepper } from './Stepper';
import { HelpPanel } from './HelpPanel';
import { StepAboutYou, AboutYouData } from './steps/StepAboutYou';
import { StepLocation, LocationData } from './steps/StepLocation';
import { StepCapital, CapitalData } from './steps/StepCapital';
import { StepBusiness, BusinessData } from './steps/StepBusiness';
import { StepReview } from './steps/StepReview';
import { Leaf, LogOut } from 'lucide-react';
import { useTranslations } from 'next-intl';

interface OnboardingFlowProps {
  onCancel: () => void;
  onComplete: (data: any) => Promise<void>;
}

export function OnboardingFlow({ onCancel, onComplete }: OnboardingFlowProps) {
  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [aboutData, setAboutData] = useState<AboutYouData>({
    fullName: '', age: '', gender: '', category: ''
  });
  const [locationData, setLocationData] = useState<LocationData>({
    state: '', district: '', village: ''
  });
  const [capitalData, setCapitalData] = useState<CapitalData>({
    investment: '', source: ''
  });
  const [businessData, setBusinessData] = useState<BusinessData>({
    industry: '', experience: '', ideaDetails: ''
  });

  const tCommon = useTranslations('common');

  const nextStep = () => setStep(prev => Math.min(prev + 1, 5));
  const prevStep = () => setStep(prev => Math.max(prev - 1, 1));

  const handleComplete = async () => {
    setIsSubmitting(true);
    await onComplete({
      ...aboutData,
      ...locationData,
      ...capitalData,
      ...businessData
    });
    setIsSubmitting(false);
  };

  // Render current step component
  const renderStep = () => {
    switch(step) {
      case 1:
        return <StepAboutYou data={aboutData} updateData={(d) => setAboutData({...aboutData, ...d})} onNext={nextStep} onBack={onCancel} />;
      case 2:
        return <StepLocation data={locationData} updateData={(d) => setLocationData({...locationData, ...d})} onNext={nextStep} onBack={prevStep} />;
      case 3:
        return <StepCapital data={capitalData} updateData={(d) => setCapitalData({...capitalData, ...d})} onNext={nextStep} onBack={prevStep} />;
      case 4:
        return <StepBusiness data={businessData} updateData={(d) => setBusinessData({...businessData, ...d})} onNext={nextStep} onBack={prevStep} />;
      case 5:
        return <StepReview data={{ about: aboutData, location: locationData, capital: capitalData, business: businessData }} onNext={handleComplete} onBack={prevStep} isSubmitting={isSubmitting} />;
      default:
        return null;
    }
  };

  return (
    <div className="h-screen overflow-hidden bg-[#fcfbf8] flex flex-col font-sans selection:bg-saffron-tint selection:text-saffron-deep">
      
      {/* Simple Header */}
      <header className="w-full bg-white border-b border-premium-border/50 py-2 px-6 flex justify-between items-center z-10 sticky top-0 shadow-sm">
        <div className="flex items-center cursor-pointer group" onClick={onCancel}>
          <img
            src="/yukti-logo-transparent.png"
            alt="YuktiFi Logo"
            className="h-10 w-10 object-contain mr-3 transition-transform group-hover:scale-105"
          />
          <div className="flex flex-col justify-center">
            <span className="font-display font-bold text-2xl text-forest-deep tracking-tight leading-none group-hover:text-[#ea580c] transition-colors">YuktiFi</span>
            <span className="text-[8px] font-bold text-ink-soft uppercase tracking-[0.2em] mt-1">{tCommon('govInit')}</span>
          </div>
        </div>
        <button 
          onClick={onCancel}
          className="text-ink-soft hover:text-ink text-sm font-bold flex items-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron rounded px-2 py-1"
        >
          {tCommon('cancel')} <LogOut size={16} className="ml-2" />
        </button>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col items-center pt-4 pb-4 px-4 sm:px-6 w-full max-w-6xl mx-auto overflow-hidden">
        
        {/* Stepper */}
        <div className="w-full mb-4">
          <Stepper currentStep={step} />
        </div>

        {/* Layout Split: Form on Left, Help Panel on Right */}
        <div className="w-full flex flex-col lg:flex-row gap-6 items-stretch justify-center h-full max-w-5xl overflow-hidden">
          
          <div className="flex-1 relative min-h-[300px]">
            <AnimatePresence mode="wait">
              <motion.div
                key={step}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
                className="h-full"
              >
                {renderStep()}
              </motion.div>
            </AnimatePresence>
          </div>

          <HelpPanel />
        </div>
      </main>

    </div>
  );
}
