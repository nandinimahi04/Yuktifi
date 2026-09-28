import React from 'react';
import { motion } from 'framer-motion';
import { useTranslations } from 'next-intl';

export type Step = {
  id: number;
  labelKey: string;
};

const steps: Step[] = [
  { id: 1, labelKey: 'step_1' },
  { id: 2, labelKey: 'step_2' },
  { id: 3, labelKey: 'step_3' },
  { id: 4, labelKey: 'step_4' },
  { id: 5, labelKey: 'step_5' },
];

interface StepperProps {
  currentStep: number;
}

export function Stepper({ currentStep }: StepperProps) {
  const t = useTranslations('Stepper');
  
  return (
    <div className="w-full max-w-3xl mx-auto px-4">
      <div className="flex justify-between items-center relative">
        {/* Background Line */}
        <div className="absolute left-[10%] right-[10%] top-4 h-0.5 bg-premium-border -z-10" />
        
        {/* Progress Line */}
        <div 
          className="absolute left-[10%] top-4 h-0.5 bg-forest -z-10 transition-all duration-500 ease-in-out"
          style={{ width: `${Math.max(0, (currentStep - 1) / (steps.length - 1)) * 80}%` }}
        />

        {steps.map((step) => {
          const isActive = step.id === currentStep;
          const isCompleted = step.id < currentStep;

          return (
            <div key={step.id} className="flex flex-col items-center">
              <div 
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors duration-300 ${
                  isActive || isCompleted 
                    ? 'bg-forest border-forest text-white' 
                    : 'bg-white border-premium-border-strong text-ink-soft'
                }`}
              >
                {step.id}
              </div>
              <span 
                className={`mt-2 text-xs font-bold transition-colors duration-300 ${
                  isActive || isCompleted ? 'text-forest' : 'text-ink-soft'
                }`}
              >
                {t(step.labelKey)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
