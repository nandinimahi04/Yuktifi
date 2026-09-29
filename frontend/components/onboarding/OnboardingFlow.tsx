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
import { LogOut, MessageSquare } from 'lucide-react';
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
    fullName: '',
    age: '',
    gender: 'Male',
    category: 'General'
  });

  const [locationData, setLocationData] = useState<LocationData>({
    state: 'Maharashtra',
    district: 'Solapur',
    village: ''
  });

  const [capitalData, setCapitalData] = useState<CapitalData>({
    investment: '75000',
    investmentTier: '₹50,000 - ₹1L',
    sourceOfFunds: 'personal_savings',
    customInvestment: ''
  });

  const [businessData, setBusinessData] = useState<BusinessData>({
    industry: 'Retail & Shop',
    experience: 'None, I am a beginner',
    ideaDetails: '',
    considerSimilar: true
  });

  const tCommon = useTranslations('common');

  const nextStep = () => setStep(prev => Math.min(prev + 1, 5));
  const prevStep = () => setStep(prev => Math.max(prev - 1, 1));

  const handleComplete = async () => {
    setIsSubmitting(true);
    // Resolve final investment amount
    const finalInvestment = capitalData.customInvestment
      ? capitalData.customInvestment
      : capitalData.investment || '75000';

    await onComplete({
      ...aboutData,
      ...locationData,
      ...capitalData,
      investment: finalInvestment,
      loanIntent: capitalData.sourceOfFunds === 'personal_savings' ? 'no' : 'yes',
      ...businessData
    });
    setIsSubmitting(false);
  };

  // Render current step component in exact order: About You (1) -> Location (2) -> Capital (3) -> Business (4) -> Review (5)
  const renderStep = () => {
    switch(step) {
      case 1:
        return (
          <StepAboutYou 
            data={aboutData} 
            updateData={(d) => setAboutData({...aboutData, ...d})} 
            onNext={nextStep} 
            onBack={onCancel} 
          />
        );
      case 2:
        return (
          <StepLocation 
            data={locationData} 
            updateData={(d) => setLocationData({...locationData, ...d})} 
            onNext={nextStep} 
            onBack={prevStep} 
          />
        );
      case 3:
        return (
          <StepCapital 
            data={capitalData} 
            updateData={(d) => setCapitalData({...capitalData, ...d})} 
            onNext={nextStep} 
            onBack={prevStep} 
          />
        );
      case 4:
        return (
          <StepBusiness 
            data={businessData} 
            updateData={(d) => setBusinessData({...businessData, ...d})} 
            onNext={nextStep} 
            onBack={prevStep} 
          />
        );
      case 5:
        return (
          <StepReview 
            data={{ about: aboutData, location: locationData, capital: capitalData, business: businessData }} 
            onNext={handleComplete} 
            onBack={prevStep} 
            isSubmitting={isSubmitting} 
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-[#fcfbf8] flex flex-col font-sans selection:bg-saffron-tint selection:text-saffron-deep relative">
      
      {/* Top Header */}
      <header className="w-full bg-white border-b border-premium-border/60 py-3 px-6 sm:px-10 flex justify-between items-center z-10 sticky top-0 shadow-sm">
        <div className="flex items-center cursor-pointer group" onClick={onCancel}>
          <img
            src="/yukti-logo-transparent.png"
            alt="YuktiFi Logo"
            className="h-9 w-9 object-contain mr-3 transition-transform group-hover:scale-105"
          />
          <div className="flex flex-col justify-center">
            <span className="font-display font-black text-2xl text-forest-deep tracking-tight leading-none group-hover:text-[#ea580c] transition-colors">
              YuktiFi
            </span>
            <span className="text-[9px] font-bold text-ink-soft uppercase tracking-[0.2em] mt-1">
              {tCommon('govInit')}
            </span>
          </div>
        </div>
        <button 
          onClick={onCancel}
          className="text-ink-soft hover:text-ink text-sm font-bold flex items-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron rounded-lg px-3 py-1.5 hover:bg-cream"
        >
          {tCommon('cancel')} <LogOut size={16} className="ml-2" />
        </button>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col items-center pt-6 pb-8 px-4 sm:px-8 w-full max-w-6xl mx-auto">
        
        {/* Stepper */}
        <div className="w-full mb-6">
          <Stepper currentStep={step} />
        </div>

        {/* Layout Split: Form on Left, Help Panel on Right */}
        <div className="w-full flex flex-col lg:flex-row gap-6 items-stretch justify-center max-w-5xl">
          
          <div className="flex-1 relative min-h-[460px]">
            <AnimatePresence mode="wait">
              <motion.div
                key={step}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
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

      {/* Floating Chatbot Action Button */}
      <button 
        type="button"
        title="YuktiFi Assistant"
        className="fixed bottom-6 right-6 w-12 h-12 bg-[#ea580c] hover:bg-[#c2410c] text-white rounded-full shadow-2xl flex items-center justify-center transition-transform hover:scale-110 active:scale-95 z-50"
      >
        <MessageSquare size={22} className="fill-white/20 stroke-[2.5]" />
      </button>

    </div>
  );
}
