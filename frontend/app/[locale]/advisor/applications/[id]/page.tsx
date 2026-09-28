"use client";
import React from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, CheckCircle2, ChevronLeft, FileText, Download, Target, TrendingUp, XCircle } from 'lucide-react';
import { YuktiFiInsight } from '@/components/YuktiFiInsight';

export default function ApplicationReview() {
  const params = useParams();
  const appId = params.id ? (params.id as string).toUpperCase() : 'APP-001';

  return (
    <div className="p-4 md:p-8 bg-warm-bg min-h-screen text-warm-text font-sans animate-in fade-in duration-500">
      <Link href="/advisor/applications" className="inline-flex items-center text-sm font-bold text-warm-muted hover:text-warm-primary mb-6 transition-colors">
        <ChevronLeft size={16} className="mr-1" /> BACK TO QUEUE
      </Link>
      
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end border-b border-warm-border pb-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-warm-text">Application Review</h1>
          <p className="text-sm text-warm-primary font-bold mt-1">ID: {appId} • Rajesh Kumar</p>
          <p className="text-xs text-warm-muted mt-1">
            Sample application — the figures below are illustrative, not computed from a
            real submission.
          </p>
        </div>
        
        <div className="flex space-x-3 mt-4 md:mt-0">
          <button className="bg-red-50 border border-red-200 text-red-600 hover:bg-red-600 hover:text-warm-text px-6 py-2.5 rounded-xl flex items-center text-sm font-bold transition-colors shadow-sm">
            <XCircle size={18} className="mr-2" /> Reject
          </button>
          <button className="bg-emerald-50 border border-emerald-200 text-emerald-700 hover:bg-emerald-600 hover:text-warm-text px-6 py-2.5 rounded-xl flex items-center text-sm font-bold transition-colors shadow-sm">
            <CheckCircle2 size={18} className="mr-2" /> Approve Loan
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="md:col-span-2 space-y-6">
          <YuktiFiInsight
            type="positive"
            title="ALGORITHMIC RECOMMENDATION: APPROVE"
            message="Scored 88/100 on the YuktiFi viability index. Applicant has requested ₹15 Lakhs for Textile Manufacturing in Nagpur Zone A. Debt service coverage is projected at 2.1x under recession stress. These figures come from a sample application and are illustrative only."
            className="shadow-sm"
          />
          
          <Card className="bg-warm-surface border-warm-border rounded-xl shadow-sm">
            <CardHeader className="border-b border-warm-border pb-4 bg-warm-bg/50">
              <CardTitle className="text-sm font-bold text-warm-text uppercase tracking-wider flex items-center">
                <Target size={16} className="mr-2 text-warm-primary" /> YuktiFi Risk Assessment
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              <div>
                <div className="flex justify-between items-end mb-2">
                  <div className="text-xs font-bold text-warm-muted uppercase tracking-wider">Market Saturation Risk</div>
                  <div className="text-emerald-600 text-sm font-black">LOW</div>
                </div>
                <div className="w-full h-2 bg-warm-border rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: '15%' }}></div>
                </div>
                <p className="text-xs font-medium text-warm-muted mt-2">Only 2 competitors within a 5km radius. Market is underserved.</p>
              </div>

              <div>
                <div className="flex justify-between items-end mb-2">
                  <div className="text-xs font-bold text-warm-muted uppercase tracking-wider">Capital Efficiency</div>
                  <div className="text-emerald-600 text-sm font-black">HIGH</div>
                </div>
                <div className="w-full h-2 bg-warm-border rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: '85%' }}></div>
                </div>
                <p className="text-xs font-medium text-warm-muted mt-2">
                  Scored against the applicant's declared capital and the category
                  benchmarks. Open the financials tab for the modelled return on project
                  cost and on the applicant's own equity.
                </p>
              </div>

              <div>
                <div className="flex justify-between items-end mb-2">
                  <div className="text-xs font-bold text-warm-muted uppercase tracking-wider">Execution Risk</div>
                  <div className="text-amber-500 text-sm font-black">MEDIUM</div>
                </div>
                <div className="w-full h-2 bg-warm-border rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500 rounded-full" style={{ width: '45%' }}></div>
                </div>
                <p className="text-xs font-medium text-warm-muted mt-2">Applicant has 3 years of sector experience, but limited formal management training.</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-warm-surface border-warm-border rounded-xl shadow-sm">
            <CardHeader className="border-b border-warm-border pb-4 bg-warm-bg/50">
              <CardTitle className="text-sm font-bold text-warm-text uppercase tracking-wider flex items-center">
                <FileText size={16} className="mr-2 text-warm-primary" /> Document Verification
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <ul className="space-y-4">
                <li className="flex items-center text-sm font-medium text-warm-text">
                  <CheckCircle2 size={18} className="text-emerald-500 mr-3" /> Aadhaar / PAN (Promoter)
                </li>
                <li className="flex items-center text-sm font-medium text-warm-text">
                  <CheckCircle2 size={18} className="text-emerald-500 mr-3" /> Address Proof
                </li>
                <li className="flex items-center text-sm font-medium text-warm-text">
                  <CheckCircle2 size={18} className="text-emerald-500 mr-3" /> Equipment Quotations
                </li>
                <li className="flex items-center text-sm font-medium text-warm-text">
                  <CheckCircle2 size={18} className="text-emerald-500 mr-3" /> Bank Statements
                </li>
              </ul>
              
              <button className="w-full mt-6 bg-white border border-warm-border hover:border-warm-primary hover:bg-orange-50 text-warm-primary px-4 py-2.5 rounded-xl flex items-center justify-center text-sm font-bold transition-all shadow-sm">
                <Download size={16} className="mr-2" /> Download Master Archive (ZIP)
              </button>
            </CardContent>
          </Card>

          <Card className="bg-warm-surface border-warm-border rounded-xl shadow-sm">
            <CardHeader className="border-b border-warm-border pb-4 bg-warm-bg/50">
              <CardTitle className="text-sm font-bold text-warm-text uppercase tracking-wider flex items-center">
                <TrendingUp size={16} className="mr-2 text-warm-primary" /> Key Financials
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-warm-muted uppercase tracking-wider">Loan Amount</span>
                <span className="text-sm text-warm-text font-black">₹15,00,000</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-warm-muted uppercase tracking-wider">Tenure</span>
                <span className="text-sm text-warm-text font-black">5 Years</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-warm-muted uppercase tracking-wider">Base Loan Repayment Capacity</span>
                <span className="text-sm text-emerald-600 font-black">2.4x</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-warm-muted uppercase tracking-wider">IRR</span>
                <span className="text-sm text-warm-text font-black">18.5%</span>
              </div>
              
              <Link href="/report" target="_blank" className="w-full mt-6 block text-center bg-warm-primary text-warm-text hover:bg-orange-600 px-4 py-3 rounded-xl text-xs uppercase tracking-wider font-bold transition-all shadow-md">
                View Detailed Project Report
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
