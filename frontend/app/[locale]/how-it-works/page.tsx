'use client';

import React from 'react';
import { HeroNavbar } from '@/components/hero/HeroNavbar';
import { Search, BarChart3, Calculator, Rocket, ArrowRight, CheckCircle2 } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';

export default function HowItWorksPage() {
  const steps = [
    {
      step: "01",
      icon: <Search className="w-7 h-7 text-[#ea580c]" />,
      title: "Discover Opportunities",
      description: "Enter your location and available capital. YuktiFi instantly scans your local micro-economy and suggests hyper-local business opportunities with high success probabilities.",
      highlights: ["District-level demand analysis", "Capital requirement matching", "Local market gap detection"]
    },
    {
      step: "02",
      icon: <BarChart3 className="w-7 h-7 text-[#ea580c]" />,
      title: "Analyze Feasibility",
      description: "Dive deep into AI-generated Market Intelligence reports. Understand local demand, competitor landscape, optimal pricing strategies, and potential supply chain risks.",
      highlights: ["Competitive intensity map", "Raw material availability", "Target customer profiling"]
    },
    {
      step: "03",
      icon: <Calculator className="w-7 h-7 text-[#ea580c]" />,
      title: "Financial Planning",
      description: "The financial engine computes project cost, break-even and cash flow from the figures you declare and any published cost reference, routes your project to a government scheme band, and simulates repayment. Scheme terms are prototype constants and are never presented as verified current terms.",
      highlights: ["Scheme routing by project-cost band, marked unverified", "Break-even estimate from declared unit economics", "Cash flow projection across the loan tenure"]
    },
    {
      step: "04",
      icon: <Rocket className="w-7 h-7 text-[#ea580c]" />,
      title: "Launch & Grow",
      description: "Export a project report that states its sources, keep track of implementation milestones on your dashboard, and work from supplier listings that are labelled as unverified samples rather than screened suppliers.",
      highlights: ["Project report export with per-figure sources", "Milestone tracking on your dashboard", "Supplier listings labelled as unverified samples"]
    }
  ];

  return (
    <div className="min-h-screen bg-[#fdfbf6] flex flex-col font-sans relative overflow-hidden">
      {/* Subtle Background Pattern */}
      <div 
        className="absolute inset-0 opacity-[0.03] pointer-events-none bg-repeat"
        style={{ backgroundImage: `url('/hero-bg.png')`, backgroundSize: '600px' }}
      />

      <HeroNavbar onGetStarted={() => window.location.href = '/onboarding'} />
      
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 pt-28 pb-16 relative z-10">
        {/* Header Badge & Title */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#ea580c]/10 text-[#ea580c] font-semibold text-xs tracking-wider uppercase mb-4">
            <span className="w-2 h-2 rounded-full bg-[#ea580c] animate-pulse"></span>
            Step-by-Step Guidance Process
          </div>
          <h1 className="font-display font-bold text-4xl sm:text-5xl text-forest-deep mb-4 tracking-tight">
            How <span className="text-[#ea580c]">YuktiFi</span> Works
          </h1>
          <p className="text-base sm:text-lg text-ink font-medium max-w-2xl mx-auto leading-relaxed">
            A seamless, 4-step data-driven journey designed to turn rural entrepreneurial aspirations into bankable, profitable businesses.
          </p>
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
          {steps.map((item, index) => (
            <div 
              key={index} 
              className="bg-white/80 backdrop-blur-sm border border-emerald-900/10 p-8 rounded-[2rem] shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative group flex flex-col justify-between"
            >
              <div className="absolute top-6 right-8 text-4xl font-display font-extrabold text-forest-deep/10 group-hover:text-[#ea580c]/20 transition-colors">
                {item.step}
              </div>

              <div>
                <div className="w-14 h-14 bg-[#fff5f0] border border-[#ea580c]/20 rounded-2xl flex items-center justify-center mb-6 shadow-inner group-hover:scale-110 transition-transform">
                  {item.icon}
                </div>
                
                <h3 className="text-2xl font-bold text-forest-deep mb-3 group-hover:text-[#ea580c] transition-colors">
                  {item.title}
                </h3>
                
                <p className="text-ink-soft leading-relaxed text-sm sm:text-base mb-6">
                  {item.description}
                </p>
              </div>

              <div className="border-t border-emerald-900/5 pt-4 mt-2">
                <div className="space-y-2">
                  {item.highlights.map((h, i) => (
                    <div key={i} className="flex items-center text-xs font-semibold text-forest-deep/80 gap-2">
                      <CheckCircle2 className="w-4 h-4 text-[#ea580c] shrink-0" />
                      <span>{h}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Bottom Callout Banner */}
        <div className="bg-gradient-to-r from-forest-deep via-[#1e4620] to-forest-deep text-white p-8 sm:p-10 rounded-[2.5rem] shadow-lg flex flex-col sm:flex-row items-center justify-between gap-6 relative overflow-hidden">
          <div className="absolute right-0 top-0 bottom-0 opacity-10 pointer-events-none flex items-center pr-6">
            <Image src="/india-emblem.png" alt="Emblem" width={180} height={180} />
          </div>
          <div className="relative z-10 max-w-xl text-center sm:text-left">
            <h3 className="text-2xl font-bold font-display mb-2 text-amber-100">Ready to start your business evaluation?</h3>
            <p className="text-white/80 text-sm sm:text-base">
              It takes less than 3 minutes to see the business categories this build can cost, along with exactly which figures are known and which are still missing for each one.
            </p>
          </div>
          <Link
            href="/onboarding"
            className="relative z-10 shrink-0 inline-flex items-center gap-2 bg-[#ea580c] hover:bg-[#d94e05] text-white px-7 py-3.5 rounded-full font-bold shadow-md hover:shadow-lg transition-all"
          >
            <span>Explore Opportunities</span>
            <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </main>
    </div>
  );
}

