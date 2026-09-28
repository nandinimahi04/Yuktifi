"use client";

import React, { useState } from "react";
import { useRouter } from "@/routing";
import Link from "next/link";
import { useStore } from "@/lib/store";
import { api } from "@/lib/api-client";
import { Loader2, ArrowRight, MapPin, GraduationCap, User, Lock } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { HeroSection } from "@/components/hero/HeroSection";
import { OnboardingFlow } from "@/components/onboarding/OnboardingFlow";
import { useTranslations, useLocale } from "next-intl";

export default function LandingPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations('Landing');
  const { updateState } = useStore();
  const [loading, setLoading] = useState(false);
  const [selectedPath, setSelectedPath] = useState<'none' | 'entrepreneur' | 'advisor'>('none');
  const [profileError, setProfileError] = useState("");
  
  const [formData, setFormData] = useState({
    name: "",
    age: "",
    // Left empty rather than pre-filled with "Solapur, Maharashtra" and "10th".
    // This is the onboarding form, so its values are what the rest of the app
    // treats as the user's declared profile - the same declaration the advisory
    // and results pages were being fed invented values for. A user who simply
    // pressed through was assigned a district and a qualification they never
    // gave, and every downstream location lookup then answered about Solapur.
    education: "",
    location: ""
  });

  const [loadingStep, setLoadingStep] = useState(0);

  const loadingSteps = [
    t('loading.step_1'),
    t('loading.step_2'),
    t('loading.step_3'),
    t('loading.step_4'),
    t('loading.step_5')
  ];

  const handleEntrepreneurComplete = async (onboardingData: any) => {
    setLoading(true);
    setLoadingStep(0);
    setProfileError("");

    // Simulate step progression for better UX while waiting for Gemini
    const stepInterval = setInterval(() => {
      setLoadingStep(prev => Math.min(prev + 1, loadingSteps.length - 1));
    }, 2000);

    try {
      // Normalize investment string → numeric value
      let investmentAmount = 0;
      const invStr = (onboardingData.investment || "").trim();
      if (invStr.includes("Under") && invStr.includes("50,000")) investmentAmount = 25000;
      else if (invStr.includes("50,000") && invStr.includes("1L")) investmentAmount = 75000;
      else if (invStr.includes("1L") && invStr.includes("3L")) investmentAmount = 200000;
      else if (invStr.includes("3L") && invStr.includes("5L")) investmentAmount = 400000;
      else if (invStr.includes("5L")) investmentAmount = 600000;
      else {
        // Parse custom numeric entry (strip ₹ commas spaces)
        const numeric = parseFloat(invStr.replace(/[₹,\s]/g, ""));
        if (!isNaN(numeric) && numeric > 0) investmentAmount = numeric;
      }

      // Create user profile
      const resProfile = await api.createProfile({
        name: onboardingData.fullName || "Entrepreneur",
        location_input: `${onboardingData.village ? onboardingData.village + ', ' : ''}${onboardingData.district}, ${onboardingData.state}`,
        language: "en"
      });
      
      // Generate full dynamic analysis via the SINGLE authoritative endpoint
      const resAnalysis = await api.generateAnalysis({
        profile: {
          name: onboardingData.fullName,
          age: onboardingData.age,
          gender: onboardingData.gender,
          social_category: onboardingData.category
        },
        location: {
          state: onboardingData.state,
          district: onboardingData.district,
          village_or_taluka: onboardingData.village
        },
        capital: {
          investment_amount: investmentAmount,
          primary_source: onboardingData.source
        },
        business: {
          area_of_interest: onboardingData.industry,
          suggested_idea: onboardingData.selectedIdea || "",
          detailed_idea_description: onboardingData.ideaDetails || "",
          prior_experience: onboardingData.experience
        },
        language: locale
      });

      // Safe extraction — data_available may be false for non-Solapur
      const matchedCategoryId = resAnalysis.matched_business?.matched_category_id || null;

      updateState({
        sessionId: resProfile.user_id,
        locationId: resProfile.location_id,
        locationName: resProfile.location_name || `${onboardingData.district}, ${onboardingData.state}`,
        profileName: onboardingData.fullName || "Entrepreneur",
        userMode: 'entrepreneur',
        marginCapital: investmentAmount,
        categoryId: matchedCategoryId,
        categoryName: onboardingData.industry || "Business",
        experience: onboardingData.experience || "None, I am a beginner",
        ideaDetails: onboardingData.ideaDetails || "",
        analysisResult: resAnalysis
      });
      
      clearInterval(stepInterval);
      router.push("/dashboard");
    } catch (error: unknown) {
      clearInterval(stepInterval);
      const msg = error instanceof Error ? error.message : "Failed to generate analysis. Please try again.";
      setProfileError(msg);
      alert(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleAdvisorSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      updateState({
        profileName: "Government Officer ID-892",
        userMode: 'advisor'
      });
      router.push("/advisor/analytics");
    }, 800);
  };

  // Direct deterministic advisory entry point
  if (selectedPath === "none") {
    return <div className="min-h-screen">{/* existing hero */}<HeroSection onStartEntrepreneur={() => setSelectedPath("entrepreneur")} onStartAdvisor={() => setSelectedPath("advisor")} /><div className="fixed bottom-6 right-6 z-40"><Link href="/advisory" className="px-5 py-3 rounded-full bg-forest text-white font-bold shadow-lg">Run YUKTIFI Advisory</Link></div></div>;
  }

  // Auth / Form Mode
  return (
    <div className="min-h-screen bg-cream flex flex-col items-center justify-center p-4 font-sans relative overflow-hidden">
      {/* Decorative Background for Auth screens */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-40">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-saffron blur-3xl opacity-20"></div>
        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] rounded-full bg-forest blur-3xl opacity-10"></div>
      </div>

      <AnimatePresence mode="wait">
        {selectedPath === 'entrepreneur' && (
          <motion.div 
            key="entrepreneur-onboarding"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 bg-[#fcfbf8] overflow-hidden"
          >
            {loading ? (
              <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#fcfbf8]">
                <Loader2 className="animate-spin text-forest mb-6" size={48} />
                <h2 className="text-2xl font-bold text-forest-deep mb-2">Analyzing your profile</h2>
                <div className="h-8 relative overflow-hidden w-64 flex justify-center">
                  <AnimatePresence mode="wait">
                    <motion.p
                      key={loadingStep}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="text-ink-soft font-medium absolute"
                    >
                      {loadingSteps[loadingStep]}
                    </motion.p>
                  </AnimatePresence>
                </div>
              </div>
            ) : (
              <OnboardingFlow 
                onCancel={() => setSelectedPath('none')}
                onComplete={handleEntrepreneurComplete}
              />
            )}
          </motion.div>
        )}

        {selectedPath === 'advisor' && (
          <motion.div 
            key="advisor-form"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-md z-10"
          >
            <div className="mb-6 flex justify-between items-center">
              <h2 className="font-display text-3xl font-bold text-ink">{t('institutional_login')}</h2>
              <button onClick={() => setSelectedPath('none')} className="text-sm font-bold text-ink-soft hover:text-forest transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forest rounded">
                ← {t('go_back')}
              </button>
            </div>
            
            <div className="bg-white p-8 rounded-3xl border border-premium-border shadow-card">
              <div className="flex justify-center mb-8">
                <div className="w-20 h-20 bg-cream rounded-full flex items-center justify-center border border-premium-border shadow-sm">
                  <Lock size={32} className="text-forest" />
                </div>
              </div>
              <form onSubmit={handleAdvisorSubmit} className="space-y-6">
                <div className="space-y-2">
                  <label className="text-sm font-bold text-ink">{t('officer_id')}</label>
                  <input 
                    type="text"
                    className="w-full rounded-xl border border-premium-border bg-cream-deep px-4 py-3 text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all font-medium"
                    placeholder="GOV-ID-..."
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-bold text-ink">{t('security_code')}</label>
                  <input 
                    type="password"
                    className="w-full rounded-xl border border-premium-border bg-cream-deep px-4 py-3 text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-forest focus:border-forest transition-all font-medium"
                    placeholder="••••••••"
                    required
                  />
                </div>
                
                <button 
                  type="submit" 
                  className="w-full py-4 rounded-full bg-forest hover:bg-forest-deep text-white font-bold text-base flex items-center justify-center transition-all disabled:opacity-70 shadow-card hover:shadow-card-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forest" 
                  disabled={loading}
                >
                  {loading ? <Loader2 className="animate-spin mr-2" size={20} /> : null}
                  {t('authenticate')}
                </button>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
