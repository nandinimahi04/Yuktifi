'use client';

import React from 'react';
import { HeroNavbar } from '@/components/hero/HeroNavbar';
import { Target, Users, ShieldCheck, Award, TrendingUp, Compass, ArrowRight } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';

export default function AboutPage() {
  const pillars = [
    {
      icon: <Target className="w-8 h-8 text-[#ea580c]" />,
      title: "Data-Driven Intelligence",
      description: "Business suggestions are assembled from declared evidence: location, published cost references, and the figures you enter. Where evidence is missing the engine says so rather than estimating, and every number carries its source."
    },
    {
      icon: <Users className="w-8 h-8 text-[#ea580c]" />,
      title: "Built for Bharat",
      description: "Designed specifically for first-time entrepreneurs, SHG members, and rural youth across Tier-2, Tier-3, and village economies."
    },
    {
      icon: <ShieldCheck className="w-8 h-8 text-[#ea580c]" />,
      title: "Government Backed",
      description: "Direct integration with central and state credit-linked subsidies like Prime Minister Employment Generation Programme, Mudra Y योजना, and Micro, Small and Medium Enterprises cluster initiatives."
    }
  ];

  /*
    These four statistics were removed rather than relabelled.

    "700+ districts", "2,400+ active opportunities", "15,000+ reports" and "a 35%
    average subsidy matched" were literals in this array with nothing behind
    them. The repository contains three seeded locations and a handful of cost
    references, so every one of the four was false by a wide margin, and "average
    subsidy matched" claims a statistic computed over subsidy matching that the
    product does not collect. Unlike a placeholder price on a mock vendor card, a
    landing-page statistic is the kind of claim a reader assumes has been counted
    - so there is no honest relabelling of it, only removal.

    Add real figures here when they are measured, with the period and the
    denominator, and cite where they came from.
  */
  const stats: Array<{ label: string; value: string }> = [];

  return (
    <div className="min-h-screen bg-[#fdfbf6] flex flex-col font-sans relative overflow-hidden">
      {/* Subtle Background Pattern */}
      <div 
        className="absolute inset-0 opacity-[0.03] pointer-events-none bg-repeat"
        style={{ backgroundImage: `url('/hero-bg.png')`, backgroundSize: '600px' }}
      />

      <HeroNavbar onGetStarted={() => window.location.href = '/onboarding'} />
      
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 pt-28 pb-16 relative z-10">
        {/* Header Section */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-900/10 text-forest-deep font-semibold text-xs tracking-wider uppercase mb-4">
            <Image src="/india-emblem.png" alt="Emblem" width={16} height={16} className="object-contain" />
            Official Government Initiative
          </div>
          <h1 className="font-display font-bold text-4xl sm:text-5xl text-forest-deep mb-4 tracking-tight">
            About <span className="text-[#ea580c]">YuktiFi</span>
          </h1>
          <p className="text-base sm:text-lg text-ink font-medium max-w-2xl mx-auto leading-relaxed">
            Empowering rural India through data-driven entrepreneurship, market transparency, and institutional credit support.
          </p>
        </div>

        {/* Hero Mission Card */}
        <div className="bg-white/80 backdrop-blur-md border border-emerald-900/10 p-8 sm:p-12 rounded-[2.5rem] shadow-sm mb-16 relative overflow-hidden">
          <div className="absolute right-[-40px] bottom-[-40px] opacity-5 pointer-events-none">
            <Image src="/india-emblem.png" alt="Ashoka Emblem Watermark" width={320} height={320} />
          </div>
          
          <div className="max-w-3xl mx-auto text-center relative z-10">
            <div className="w-16 h-16 bg-[#fff5f0] rounded-2xl flex items-center justify-center mx-auto mb-6 border border-[#ea580c]/20">
              <Compass className="w-8 h-8 text-[#ea580c]" />
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-forest-deep mb-6 font-display">Our Mission</h2>
            <p className="text-ink-soft text-base sm:text-lg leading-relaxed mb-6">
              YuktiFi is a landmark initiative designed to bridge the gap between rural ambition and economic viability. We believe that lack of market data or complex paperwork should never stand in the way of a viable business.
            </p>
            <p className="text-ink-soft text-base sm:text-lg leading-relaxed">
              By placing institutional-grade market intelligence, financial modeling, and instant government scheme eligibility directly into the hands of citizens, YuktiFi is driving the next wave of self-reliant micro-entrepreneurs across Bharat.
            </p>
          </div>
        </div>

        {/* Key Pillars Grid */}
        <div className="mb-16">
          <h3 className="text-center font-display font-bold text-2xl text-forest-deep mb-8">
            Built on Three Foundation Pillars
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {pillars.map((pillar, idx) => (
              <div 
                key={idx} 
                className="bg-white/80 backdrop-blur-sm border border-emerald-900/10 p-8 rounded-[2rem] shadow-sm hover:shadow-md transition-all group"
              >
                <div className="w-14 h-14 bg-[#fff5f0] border border-[#ea580c]/20 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  {pillar.icon}
                </div>
                <h4 className="font-bold text-xl text-forest-deep mb-3 group-hover:text-[#ea580c] transition-colors">
                  {pillar.title}
                </h4>
                <p className="text-ink-soft text-sm sm:text-base leading-relaxed">
                  {pillar.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Impact Statistics */}
        <div className="bg-forest-deep text-white rounded-[2.5rem] p-8 sm:p-12 mb-16 shadow-lg relative overflow-hidden">
          {stats.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center relative z-10">
              {stats.map((st, i) => (
                <div key={i} className="flex flex-col items-center">
                  <div className="text-3xl sm:text-4xl font-extrabold text-amber-300 font-display mb-1">{st.value}</div>
                  <div className="text-white/80 text-xs sm:text-sm font-medium">{st.label}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center relative z-10">
              <h3 className="text-xl font-bold text-amber-300 mb-3">
                What this build can actually tell you
              </h3>
              <p className="text-white/80 text-sm max-w-2xl mx-auto">
                No coverage or outcome statistics are published here, because none
                have been measured. The repository currently holds a small seeded
                set of locations and cost references, so any district or
                opportunity count would be invented. What it does provide is a
                traceable calculation: each figure is either stated by you, taken
                from a cited source, or reported as missing.
              </p>
            </div>
          )}
        </div>

        {/* Call to Action */}
        <div className="text-center bg-white/70 border border-emerald-900/10 p-8 rounded-[2rem]">
          <h3 className="text-xl font-bold text-forest-deep mb-3">Ready to begin your journey?</h3>
          <p className="text-ink-soft text-sm mb-6 max-w-md mx-auto">
            Calculate your investment capital and see curated business opportunities instantly.
          </p>
          <Link
            href="/onboarding"
            className="inline-flex items-center gap-2 bg-[#ea580c] hover:bg-[#d94e05] text-white px-8 py-3.5 rounded-full font-bold shadow-sm hover:shadow transition-all"
          >
            <span>Get Started Now</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </main>
    </div>
  );
}

