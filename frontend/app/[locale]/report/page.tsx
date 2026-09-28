"use client";
import React, { useEffect, useState, useRef } from "react";
import { useRouter } from "@/routing";
import { api } from "@/lib/api-client";
import { useStore } from "@/lib/store";
import { Loader2, Download, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTranslations } from "next-intl";

export default function ReportPage() {
  const router = useRouter();
  const state = useStore();
  const [downloading, setDownloading] = useState(false);
  const reportRef = useRef<HTMLDivElement>(null);
  const t = useTranslations('report');

  useEffect(() => {
    if (!state.analysisResult) {
      router.push("/");
    }
  }, [state.analysisResult, router]);

  const handleDownload = async () => {
    if (!reportRef.current) return;
    try {
      setDownloading(true);
      // Dynamically import html2pdf to avoid Next.js SSR window issues
      const html2pdf = (await import('html2pdf.js')).default;
      
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const opt: any = {
        margin:       10,
        filename:     `YuktiFi_Detailed Project Report_${state.categoryName || 'Report'}.pdf`.replace(/[^a-z0-9]/gi, '_'),
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
      };

      await html2pdf().set(opt).from(reportRef.current).save();
    } catch (err) {
      console.error("Error generating PDF:", err);
      alert("Failed to download PDF. Falling back to print dialog.");
      window.print();
    } finally {
      setDownloading(false);
    }
  };

  if (!state.analysisResult) {
    return (
      <div className="max-w-4xl mx-auto mt-20 flex flex-col items-center justify-center space-y-4 font-sans">
        <Loader2 size={48} className="animate-spin text-warm-primary" />
        <p className="text-warm-primary font-bold text-lg">{t('loading')}</p>
      </div>
    );
  }

  const today = new Date().toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' });
  const { market, financials, scores, ai_insights } = state.analysisResult;

  return (
    <div className="max-w-4xl mx-auto mt-6 pb-20 font-sans">
      <div className="flex justify-between items-center mb-6 border-b border-warm-border pb-4 print:hidden">
        <h1 className="text-3xl font-bold text-warm-text">{t('title')}</h1>
        <Button 
          onClick={handleDownload} 
          disabled={downloading}
          className="bg-warm-primary hover:bg-orange-600 text-warm-text font-bold text-sm shadow-md transition-all"
        >
          {downloading ? <Loader2 size={16} className="animate-spin mr-2" /> : <Download size={16} className="mr-2" />}
          {downloading ? t('exporting') : t('export')}
        </Button>
      </div>
      
      <div ref={reportRef} className="bg-white text-slate-800 p-8 md:p-16 min-h-[1056px] shadow-lg rounded-2xl border border-warm-border print:shadow-none print:border-none print:p-0">
        
        {/* Cover Page */}
        <div className="flex flex-col justify-center min-h-[800px] print:min-h-[100vh] border-b-4 border-warm-primary mb-12 pb-12">
          <div className="flex items-center space-x-3 mb-16">
            <div className="w-12 h-12 bg-warm-primary text-warm-text flex items-center justify-center font-bold text-2xl rounded-lg shadow-sm">Y</div>
            <span className="text-3xl font-extrabold tracking-tight text-warm-text">YuktiFi</span>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-black mb-6 leading-tight text-warm-text whitespace-pre-line">{t('cover.title')}</h1>
          <h2 className="text-2xl text-warm-muted mb-12 font-medium">{t('cover.for')} {state.categoryName || "Business Implementation"}</h2>
          
          <div className="mt-auto grid grid-cols-2 gap-8 border-t border-warm-border pt-8">
            <div>
              <p className="text-xs uppercase tracking-wider text-warm-muted font-bold mb-1">{t('cover.prepared')}</p>
              <p className="font-bold text-lg text-warm-text">{state.profileName || "Entrepreneur"}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-warm-muted font-bold mb-1">{t('cover.location')}</p>
              <p className="font-bold text-lg text-warm-text">{state.locationName || "Target Region"}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-warm-muted font-bold mb-1">{t('cover.date')}</p>
              <p className="font-bold text-lg text-warm-text">{today}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-warm-muted font-bold mb-1">{t('cover.version')}</p>
              <p className="font-bold text-lg text-warm-text">YuktiFi 2.0 Engine</p>
            </div>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="mb-12 print:break-before-page">
          <h3 className="text-2xl font-bold border-b border-warm-border pb-2 mb-6 text-warm-text">{t('summary.title')}</h3>
          <div className="bg-emerald-50 p-6 border border-emerald-100 rounded-xl mb-6">
            <div className="flex items-start">
              <CheckCircle2 size={24} className="text-emerald-600 mr-4 flex-shrink-0 mt-1" />
              <div>
                <h4 className="font-bold text-lg mb-2 text-emerald-900">{t('summary.viability')} {scores?.overall >= 70 ? t('summary.highly') : scores?.overall >= 50 ? t('summary.caution') : t('summary.risk')}</h4>
                <p className="text-emerald-800 leading-relaxed font-medium">
                  {ai_insights?.rationale || "Analysis generated."}
                </p>
              </div>
            </div>
          </div>

          <h4 className="font-bold text-lg mb-4 text-warm-text">{t('summary.strategies')}</h4>
          <ul className="list-disc pl-5 space-y-2 text-slate-700">
            {ai_insights?.recommendations?.map((rec: string, i: number) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </div>

        {/* Financials Summary */}
        <div className="mb-12 print:break-before-page">
          <h3 className="text-2xl font-bold border-b border-warm-border pb-2 mb-6 text-warm-text">{t('financials.title')}</h3>
          <table className="w-full text-left border-collapse border border-warm-border">
            <thead>
              <tr className="bg-warm-bg text-warm-text font-bold">
                <th className="border border-warm-border p-2">{t('financials.metric')}</th>
                <th className="border border-warm-border p-2">{t('financials.value')}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-warm-border p-2 font-medium">{t('financials.cost')}</td>
                <td className="border border-warm-border p-2">₹{financials?.project_cost?.toLocaleString()}</td>
              </tr>
              <tr>
                <td className="border border-warm-border p-2 font-medium">{t('financials.loan')}</td>
                <td className="border border-warm-border p-2">₹{financials?.loan_amount?.toLocaleString()}</td>
              </tr>
              <tr>
                <td className="border border-warm-border p-2 font-medium">{t('financials.emi')}</td>
                <td className="border border-warm-border p-2">₹{financials?.emi?.toLocaleString()}</td>
              </tr>
              <tr>
                <td className="border border-warm-border p-2 font-medium">{t('financials.profit')}</td>
                <td className="border border-warm-border p-2">₹{financials?.net_profit?.toLocaleString()}</td>
              </tr>
              <tr>
                <td className="border border-warm-border p-2 font-medium">{t('financials.roi')}</td>
                <td className="border border-warm-border p-2">{financials?.roi_pct?.toFixed(1)}%</td>
              </tr>
              <tr>
                <td className="border border-warm-border p-2 font-medium">{t('financials.dscr')}</td>
                <td className="border border-warm-border p-2">{financials?.dscr?.toFixed(2)}x</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Legal Disclaimer */}
        <div className="mt-20 pt-8 border-t border-warm-border text-sm text-warm-muted leading-relaxed print:break-before-page">
          <p className="font-bold mb-2 uppercase tracking-wider text-warm-text">{t('disclaimer.title')}</p>
          <p>{t('disclaimer.p1')}</p>
          <p className="mt-2">{t('disclaimer.p2')}</p>
        </div>
      </div>
    </div>
  );
}
