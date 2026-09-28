"use client";
import React, { useState } from 'react';
import Link from 'next/link';
import { useStore } from '@/lib/store';
import { Card, CardContent } from '@/components/ui/card';
import { CheckCircle2, Circle, Trophy, Calendar, Target, Flag, ArrowRight } from 'lucide-react';
import { YuktiFiInsight } from '@/components/YuktiFiInsight';

const planMilestones = [
  {
    id: 'm1',
    title: 'Phase 1: Foundation (Days 1-30)',
    tasks: [
      { id: 't1', title: 'Register as Micro, Small and Medium Enterprises on Udyam Portal', completed: true },
      { id: 't2', title: 'Open Current Bank Account', completed: true },
      { id: 't3', title: 'Submit Loan Application to NSFDC', completed: false },
      { id: 't4', title: 'Finalize Lease Agreement for location', completed: false }
    ]
  },
  {
    id: 'm2',
    title: 'Phase 2: Setup (Days 31-60)',
    tasks: [
      { id: 't5', title: 'Procure core machinery/equipment', completed: false, linkUrl: "/marketplace", linkText: "Find Vendors" },
      { id: 't6', title: 'Hire initial 2 staff members', completed: false },
      { id: 't7', title: 'Secure necessary local permits', completed: false }
    ]
  },
  {
    id: 'm3',
    title: 'Phase 3: Launch (Days 61-90)',
    tasks: [
      { id: 't8', title: 'Initial inventory stocking', completed: false },
      { id: 't9', title: 'Begin local marketing campaign', completed: false },
      { id: 't10', title: 'Soft Launch & initial sales', completed: false }
    ]
  }
];

export default function ActionPlan() {
  const { categoryName, locationName } = useStore();
  const [milestones, setMilestones] = useState(planMilestones);

  const toggleTask = (mId: string, tId: string) => {
    setMilestones(prev => prev.map(m => {
      if (m.id === mId) {
        return {
          ...m,
          tasks: m.tasks.map(t => t.id === tId ? { ...t, completed: !t.completed } : t)
        };
      }
      return m;
    }));
  };

  const totalTasks = milestones.reduce((acc, m) => acc + m.tasks.length, 0);
  const completedTasks = milestones.reduce((acc, m) => acc + m.tasks.filter(t => t.completed).length, 0);
  const progressPercent = Math.round((completedTasks / totalTasks) * 100);

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8 text-warm-text animate-in fade-in duration-500">
      <div className="mb-8 mt-6 flex flex-col md:flex-row justify-between md:items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">90-Day Execution Plan</h1>
          <p className="text-warm-muted mt-2">Your AI-generated roadmap for launching {categoryName} in {locationName}.</p>
        </div>
        <button 
          onClick={() => window.print()}
          className="mt-4 md:mt-0 flex items-center bg-warm-surface border border-warm-border px-4 py-2 rounded-xl text-sm font-bold text-warm-text hover:bg-warm-bg transition-colors"
        >
          <Flag size={16} className="mr-2" /> Export to PDF
        </button>
      </div>

      <div className="bg-warm-surface p-6 rounded-2xl border border-warm-border shadow-sm mb-8 flex flex-col md:flex-row items-center justify-between">
        <div className="flex items-center mb-6 md:mb-0">
          <div className="relative w-24 h-24 mr-6 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90">
              <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-warm-bg" />
              <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="transparent" strokeDasharray="251.2" strokeDashoffset={251.2 - (251.2 * progressPercent) / 100} className="text-warm-primary transition-all duration-1000" />
            </svg>
            <div className="absolute text-xl font-bold">{progressPercent}%</div>
          </div>
          <div>
            <h3 className="text-lg font-bold">Overall Progress</h3>
            <p className="text-sm text-warm-muted">{completedTasks} of {totalTasks} tasks completed</p>
          </div>
        </div>
        
        <div className="flex space-x-4">
          <div className="text-center px-4 border-r border-warm-border">
            <div className="text-2xl font-bold text-amber-600">3</div>
            <div className="text-[10px] uppercase font-bold text-warm-muted tracking-widest mt-1">Days Streak</div>
          </div>
          <div className="text-center px-4">
            <div className="text-2xl font-bold text-emerald-600">Level 1</div>
            <div className="text-[10px] uppercase font-bold text-warm-muted tracking-widest mt-1">Founder</div>
          </div>
        </div>
      </div>

      <YuktiFiInsight 
        type="info"
        title="NEXT BEST ACTION"
        message="Submit your loan application to NSFDC. You have successfully gathered all required documents in the Financing Readiness hub."
        className="mb-8 rounded-xl !font-sans"
      />

      <div className="space-y-8">
        {milestones.map((milestone, idx) => {
          const mCompleted = milestone.tasks.filter(t => t.completed).length;
          const mTotal = milestone.tasks.length;
          const isPhaseDone = mCompleted === mTotal;
          
          return (
            <div key={milestone.id} className="relative">
              {idx !== milestones.length - 1 && (
                <div className="absolute left-[23px] top-14 bottom-[-32px] w-0.5 bg-warm-border z-0"></div>
              )}
              
              <div className="flex items-center mb-4 relative z-10">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center border-4 border-warm-bg mr-4 transition-colors duration-500 ${isPhaseDone ? 'bg-emerald-500 text-warm-text' : 'bg-warm-surface border-warm-border text-warm-muted'}`}>
                  {isPhaseDone ? <CheckCircle2 size={24} /> : <Flag size={20} />}
                </div>
                <div className="flex-1">
                  <h3 className={`font-bold text-lg ${isPhaseDone ? 'text-emerald-700' : ''}`}>{milestone.title}</h3>
                  <div className="flex items-center mt-1">
                    <div className="flex-1 h-1.5 bg-warm-bg rounded-full mr-4">
                      <div className="h-full bg-warm-primary rounded-full transition-all duration-500" style={{ width: `${(mCompleted/mTotal)*100}%` }}></div>
                    </div>
                    <span className="text-xs font-bold text-warm-muted">{mCompleted}/{mTotal}</span>
                  </div>
                </div>
              </div>

              <Card className="ml-16 bg-warm-surface border-warm-border shadow-sm">
                <CardContent className="p-0">
                  <ul className="divide-y divide-warm-border">
                    {milestone.tasks.map(task => (
                      <li 
                        key={task.id} 
                        onClick={() => toggleTask(milestone.id, task.id)}
                        className="flex items-center p-4 hover:bg-warm-bg transition-colors cursor-pointer group"
                      >
                        <div className={`mr-4 transition-colors duration-300 ${task.completed ? 'text-emerald-500' : 'text-warm-border group-hover:text-warm-primary/50'}`}>
                          {task.completed ? <CheckCircle2 size={24} /> : <Circle size={24} />}
                        </div>
                        <span className={`flex-1 transition-all duration-300 ${task.completed ? 'text-warm-muted line-through' : 'font-medium'}`}>
                          {task.title}
                          {/* @ts-ignore */}
                          {task.linkUrl && (
                            <Link 
                              // @ts-ignore
                              href={task.linkUrl}
                              onClick={(e) => e.stopPropagation()} 
                              className="ml-3 inline-flex items-center px-2 py-1 bg-warm-primary/10 text-warm-primary text-[10px] uppercase font-bold rounded hover:bg-warm-primary/20 transition-colors"
                            >
                              {/* @ts-ignore */}
                              {task.linkText} <ArrowRight size={10} className="ml-1" />
                            </Link>
                          )}
                        </span>
                        {!task.completed && (
                          <span className="text-[10px] uppercase font-bold text-warm-primary opacity-0 group-hover:opacity-100 transition-opacity flex items-center">
                            Mark Done <ArrowRight size={12} className="ml-1" />
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
}
