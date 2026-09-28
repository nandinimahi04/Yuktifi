"use client";
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Increment this when the schema changes to discard incompatible localStorage data
const YUKTI_STATE_VERSION = 2;

export interface BusinessPlan {
  id: string;
  name: string;
  categoryId: string;
  categoryName: string;
  createdAt: string;
  score: number;  // 0 = not yet calculated
  status: 'Draft' | 'Planning' | 'Validated';
  locationId: string;
  locationName: string;
  marginCapital: number;
}

export interface Opportunity {
  category_id: string;
  category_name: string;
  score: number;
  rationale: string;
  // Optional context supplied by the ranking layer. `roi` is a formatted
  // return on total project cost, e.g. "12.3%". Absent means the financials
  // have not been modelled for this option, which the UI must show as such
  // rather than substituting a placeholder figure.
  roi?: string;
  demand?: string;
  competition?: string;
  capitalFit?: string;
  risk?: string;
}

export interface SessionState {
  // Schema version for migration
  _version: number;

  // Current Active Session
  sessionId: string | null;
  locationId: string | null;
  locationName: string | null;
  marginCapital: number | null;
  categoryId: string | null;
  categoryName: string | null;
  experience: string | null;
  ideaDetails: string | null;
  dataRichness: "rich" | "sparse" | null;
  opportunities: Opportunity[];
  analysisResult: any | null;
  simulationResult: any | null;
  
  // Persistent Profile
  profileName: string;
  preferredLanguage: string;
  userMode: 'entrepreneur' | 'advisor';
  savedPlans: BusinessPlan[];

  // Actions
  updateState: (updates: Partial<Omit<SessionState, 'updateState' | 'resetState' | 'saveCurrentPlan' | 'toggleUserMode' | 'setLanguage'>>) => void;
  resetState: () => void;
  saveCurrentPlan: (score?: number) => void;
  toggleUserMode: () => void;
  setLanguage: (lang: string) => void;
}

const DEFAULT_STATE = {
  _version: YUKTI_STATE_VERSION,
  sessionId: null,
  locationId: null,
  locationName: null,
  marginCapital: null,
  categoryId: null,
  categoryName: null,
  experience: null,
  ideaDetails: null,
  dataRichness: null,
  opportunities: [] as Opportunity[],
  analysisResult: null,
  simulationResult: null,
  profileName: 'Entrepreneur',
  preferredLanguage: 'EN',
  userMode: 'entrepreneur' as const,
  savedPlans: [] as BusinessPlan[],
};

export const useStore = create<SessionState>()(
  persist(
    (set, get) => ({
      ...DEFAULT_STATE,

      updateState: (updates) => set((state) => ({ ...state, ...updates })),
      
      toggleUserMode: () => set((state) => ({
        userMode: state.userMode === 'entrepreneur' ? 'advisor' : 'entrepreneur'
      })),

      setLanguage: (lang: string) => set({ preferredLanguage: lang }),

      resetState: () => set((state) => ({
        ...state,
        sessionId: null,
        locationId: null,
        locationName: null,
        marginCapital: null,
        categoryId: null,
        categoryName: null,
        experience: null,
        ideaDetails: null,
        dataRichness: null,
        opportunities: [],
        analysisResult: null,
        simulationResult: null,
      })),

      saveCurrentPlan: (score = 0) => {
        const state = get();
        if (!state.categoryId || !state.categoryName || !state.locationName || !state.marginCapital) return;
        
        const newPlan: BusinessPlan = {
          id: crypto.randomUUID(),
          name: `${state.categoryName} in ${state.locationName}`,
          categoryId: state.categoryId,
          categoryName: state.categoryName,
          createdAt: new Date().toISOString().split('T')[0],
          score,  // Real score passed in from the score page, or 0 if not yet calculated
          status: 'Draft',
          locationId: state.locationId || 'unknown',
          locationName: state.locationName,
          marginCapital: state.marginCapital
        };

        set((s) => ({
          savedPlans: [...s.savedPlans, newPlan]
        }));
      }
    }),
    {
      name: 'yukti-storage',
      version: YUKTI_STATE_VERSION,
      // If the stored state is from an older version, discard it and start fresh
      migrate: (persistedState: unknown, version: number) => {
        if (version < YUKTI_STATE_VERSION) {
          // Discard old incompatible state, keep only non-session profile data if possible
          const old = persistedState as Partial<SessionState>;
          return {
            ...DEFAULT_STATE,
            profileName: old.profileName ?? DEFAULT_STATE.profileName,
            preferredLanguage: old.preferredLanguage ?? DEFAULT_STATE.preferredLanguage,
            userMode: old.userMode ?? DEFAULT_STATE.userMode,
            savedPlans: [],  // discard saved plans that may reference deleted sessions
          };
        }
        return persistedState as SessionState;
      },
    }
  )
);

import { useState, useEffect } from "react";

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  if (!isHydrated) {
    // Return a minimally styled placeholder or null during SSR to prevent hydration mismatch and data loss
    return <div className="min-h-screen bg-neutral-900" />;
  }

  return <>{children}</>;
}
