"use client";

import React from 'react';
import { HeroNavbar } from './HeroNavbar';
import { HeroIntelligencePanel } from './HeroIntelligencePanel';
import { HeroFeatureStrip } from './HeroFeatureStrip';
import { ArrowRight } from 'lucide-react';
import { motion, useReducedMotion, Variants } from 'framer-motion';
import Link from 'next/link';
import { useTranslations } from 'next-intl';

interface HeroSectionProps {
  onStartEntrepreneur: () => void;
  onStartAdvisor: () => void;
}

export function HeroSection({ onStartEntrepreneur, onStartAdvisor }: HeroSectionProps) {
  const t = useTranslations('Landing');
  const shouldReduceMotion = useReducedMotion();

  const titleVariants: Variants = {
    hidden: { opacity: 0, y: 30 },
    show: { opacity: 1, y: 0, transition: { duration: 0.8, ease: "easeOut" } }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#fdfbf6] flex flex-col font-sans selection:bg-saffron-tint selection:text-saffron-deep">
      {/* Background Image Layer */}
      <div className="absolute inset-0 z-0">
        <div 
          className="absolute inset-0 bg-cover bg-no-repeat opacity-100"
          style={{ 
            backgroundImage: `url('/hero-bg.png')`,
            backgroundPosition: 'center center'
          }}
        />
        {/* Softer gradient overlay to ensure text readability without hiding too much image */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#fdfbf6]/95 from-10% via-[#fdfbf6]/60 via-40% to-transparent w-full z-0 pointer-events-none" />
        
        {/* Bottom fade into the feature strip */}
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#fdfbf6] to-transparent z-0 pointer-events-none" />
      </div>

      <HeroNavbar onGetStarted={onStartAdvisor} />

      {/* Main Hero Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 flex flex-col justify-center z-10 pt-20 pb-2">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-8 items-center w-full">
          
          {/* Left Column */}
          <div className="lg:col-span-7 flex flex-col justify-center">
            <motion.div
              initial="hidden"
              animate="show"
              variants={{
                hidden: { opacity: 0 },
                show: { opacity: 1, transition: { staggerChildren: 0.2 } }
              }}
              className="max-w-2xl relative z-20"
            >
              <motion.h1 variants={titleVariants} className="font-display font-bold text-5xl lg:text-6xl xl:text-[64px] text-forest-deep leading-tight mb-8 tracking-tight">
                {t('title_1')}<br />
                <span className="text-[#ea580c]">{t('title_2')}</span>
              </motion.h1>
              
              <motion.h3 variants={titleVariants} className="text-2xl md:text-3xl text-forest-deep font-bold mb-3 tracking-tight">
                {t('subtitle')}
              </motion.h3>

              <motion.p variants={titleVariants} className="text-base text-ink-soft mb-5 font-medium leading-relaxed max-w-lg">
                {t('description')}
              </motion.p>

              <motion.div variants={titleVariants} className="flex flex-col sm:flex-row gap-3">
                <button 
                  onClick={onStartEntrepreneur}
                  className="bg-[#ea580c] hover:bg-[#c2410c] text-white px-8 py-3.5 rounded-full text-sm font-bold flex items-center justify-center shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-saffron"
                >
                  {t('start_journey')} <ArrowRight size={18} className="ml-2" />
                </button>
                <Link href="/how-it-works" passHref legacyBehavior>
                  <a 
                    className="bg-white/50 backdrop-blur-sm hover:bg-white text-forest-deep border border-forest px-8 py-3.5 rounded-full text-sm font-bold flex items-center justify-center transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-forest shadow-sm"
                  >
                    {t('see_how_it_works')}
                  </a>
                </Link>
              </motion.div>
            </motion.div>
          </div>

          {/* Right Column */}
          <div className="lg:col-span-5 flex justify-end relative">
            <HeroIntelligencePanel />
          </div>

        </div>
      </main>

      <HeroFeatureStrip />
      
    </div>
  );
}
