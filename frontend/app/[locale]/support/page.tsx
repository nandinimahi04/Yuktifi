'use client';

import React, { useState } from 'react';
import { HeroNavbar } from '@/components/hero/HeroNavbar';
import { Phone, Mail, FileQuestion, ChevronDown, MessageSquare, Clock, MapPin } from 'lucide-react';
import Image from 'next/image';

export default function SupportPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const faqs = [
    {
      q: "Is YuktiFi completely free to use for citizens?",
      a: "Yes, YuktiFi is an official Government of India portal. All core micro-market intelligence features, project feasibility reports, and scheme matching tools are provided 100% free of charge to all Indian citizens."
    },
    {
      q: "How accurate is the district market intelligence data?",
      a: "Our data models aggregate official census figures, district economic indicators, regional trade data, and periodic micro-market surveys. While highly reliable for feasibility planning, local ground verification is always recommended before final execution."
    },
    {
      q: "Can I apply for government loans directly through YuktiFi?",
      a: "YuktiFi helps you generate an official, bank-ready Detailed Project Report (Detailed Project Report). You can submit this Detailed Project Report to partnered public sector banks or upload it directly on the Jansamarth / Prime Minister Employment Generation Programme portals to expedite credit sanction."
    },
    {
      q: "Which government schemes are integrated into YuktiFi?",
      a: "YuktiFi supports prime credit-linked subsidy schemes including Prime Minister Employment Generation Programme (Prime Minister's Employment Generation Programme), PM Mudra Yojana, Stand-Up India, PM Formalisation of Micro Food Processing Enterprises (Prime Minister Formalisation of Micro Food Processing Enterprises), and state-specific Micro, Small and Medium Enterprises policies."
    },
    {
      q: "Can I get assistance in my regional language?",
      a: "Yes, YuktiFi supports 12 official Indian languages. You can switch your preferred language using the header dropdown menu."
    }
  ];

  return (
    <div className="min-h-screen bg-[#fdfbf6] flex flex-col font-sans relative overflow-hidden">
      {/* Background Subtle Pattern */}
      <div 
        className="absolute inset-0 opacity-[0.03] pointer-events-none bg-repeat"
        style={{ backgroundImage: `url('/hero-bg.png')`, backgroundSize: '600px' }}
      />

      <HeroNavbar onGetStarted={() => window.location.href = '/onboarding'} />
      
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 lg:px-8 pt-28 pb-16 relative z-10">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#ea580c]/10 text-[#ea580c] font-semibold text-xs tracking-wider uppercase mb-4">
            <span className="w-2 h-2 rounded-full bg-[#ea580c]"></span>
            24/7 Entrepreneurship Helpdesk
          </div>
          <h1 className="font-display font-bold text-4xl sm:text-5xl text-forest-deep mb-4 tracking-tight">
            Help & <span className="text-[#ea580c]">Support</span>
          </h1>
          <p className="text-base sm:text-lg text-ink font-medium max-w-2xl mx-auto leading-relaxed">
            Have questions about scheme eligibility, Detailed Project Report generation, or business selection? We're here to assist you.
          </p>
        </div>

        {/* Contact Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
          {/* Toll Free Card */}
          <div className="bg-white/80 backdrop-blur-sm border border-emerald-900/10 p-8 rounded-[2rem] shadow-sm hover:shadow-md transition-all flex flex-col justify-between group">
            <div>
              <div className="w-14 h-14 bg-[#fff5f0] border border-[#ea580c]/20 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Phone className="w-7 h-7 text-[#ea580c]" />
              </div>
              <h3 className="text-2xl font-bold text-forest-deep mb-2">Toll-Free Helpline</h3>
              <p className="text-ink-soft text-sm mb-6 leading-relaxed">
                Connect with our certified district business advisors for immediate phone guidance.
              </p>
            </div>
            
            <div className="bg-[#fdfbf6] p-4 rounded-xl border border-emerald-900/10">
              <div className="text-2xl font-extrabold text-[#ea580c] font-mono mb-1">1800-123-4567</div>
              <div className="flex items-center text-xs text-ink-soft gap-1">
                <Clock className="w-3.5 h-3.5 text-forest-deep" />
                <span>Mon – Sat, 9:00 AM – 6:00 PM IST</span>
              </div>
            </div>
          </div>

          {/* Email Support Card */}
          <div className="bg-white/80 backdrop-blur-sm border border-emerald-900/10 p-8 rounded-[2rem] shadow-sm hover:shadow-md transition-all flex flex-col justify-between group">
            <div>
              <div className="w-14 h-14 bg-[#fff5f0] border border-[#ea580c]/20 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Mail className="w-7 h-7 text-[#ea580c]" />
              </div>
              <h3 className="text-2xl font-bold text-forest-deep mb-2">Email Help Desk</h3>
              <p className="text-ink-soft text-sm mb-6 leading-relaxed">
                Send your Detailed Project Report queries or portal assistance requests. Guaranteed response within 24 hours.
              </p>
            </div>

            <div className="bg-[#fdfbf6] p-4 rounded-xl border border-emerald-900/10">
              <a href="mailto:support@yukti.gov.in" className="text-xl font-bold text-forest-deep hover:text-[#ea580c] transition-colors font-sans block mb-1">
                support@yukti.gov.in
              </a>
              <div className="flex items-center text-xs text-ink-soft gap-1">
                <MessageSquare className="w-3.5 h-3.5 text-[#ea580c]" />
                <span>Official Nodal Help Desk</span>
              </div>
            </div>
          </div>
        </div>

        {/* FAQs Accordion Section */}
        <div className="bg-white/80 backdrop-blur-md border border-emerald-900/10 p-8 sm:p-10 rounded-[2.5rem] shadow-sm">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-3 bg-emerald-900/10 rounded-xl">
              <FileQuestion className="w-6 h-6 text-forest-deep" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-forest-deep font-display">Frequently Asked Questions</h2>
              <p className="text-xs sm:text-sm text-ink-soft">Quick answers to common questions about YuktiFi</p>
            </div>
          </div>

          <div className="space-y-4">
            {faqs.map((faq, idx) => {
              const isOpen = openFaq === idx;
              return (
                <div 
                  key={idx} 
                  className={`border rounded-2xl transition-all overflow-hidden ${
                    isOpen ? 'border-[#ea580c]/40 bg-[#fff5f0]/40' : 'border-emerald-900/10 bg-white/50 hover:bg-white'
                  }`}
                >
                  <button
                    onClick={() => setOpenFaq(isOpen ? null : idx)}
                    className="w-full px-6 py-5 flex items-center justify-between text-left gap-4"
                  >
                    <span className="font-bold text-base sm:text-lg text-forest-deep">{faq.q}</span>
                    <ChevronDown className={`w-5 h-5 text-[#ea580c] shrink-0 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
                  </button>
                  {isOpen && (
                    <div className="px-6 pb-6 text-ink-soft text-sm sm:text-base leading-relaxed border-t border-emerald-900/5 pt-4">
                      {faq.a}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}

