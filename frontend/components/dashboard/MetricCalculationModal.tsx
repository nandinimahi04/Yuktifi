"use client";
import React from 'react';
import { X, Calculator, Database, ShieldCheck, Clock, CheckCircle, AlertTriangle } from 'lucide-react';

export interface MetricDetail {
  key: string;
  label: string;
  value?: number | string | null;
  unit?: string;
  score?: number | null;
  status?: string;
  confidence?: number;
  drivers?: string[];
  sources?: string[];
  formula?: string;
  inputs?: Record<string, any>;
  timestamp?: string;
  reason?: string;
}

interface MetricCalculationModalProps {
  isOpen: boolean;
  onClose: () => void;
  metric: MetricDetail | null;
}

export const MetricCalculationModal: React.FC<MetricCalculationModalProps> = ({
  isOpen,
  onClose,
  metric,
}) => {
  if (!isOpen || !metric) return null;

  const getStatusColor = (status?: string) => {
    switch (status?.toUpperCase()) {
      case 'HIGH':
      case 'GOOD':
      case 'EXCELLENT':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'MODERATE':
      case 'MEDIUM':
      case 'FAIR':
      case 'WARNING':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'LOW':
      case 'ALERT':
      case 'POOR':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  const formatInputValue = (val: any): string => {
    if (val === null || val === undefined) return 'N/A';
    if (typeof val === 'number') {
      if (Math.abs(val) >= 1000) {
        return `₹${val.toLocaleString('en-IN')}`;
      }
      return val.toString();
    }
    if (typeof val === 'boolean') return val ? 'Yes' : 'No';
    return String(val);
  };

  const formatInputLabel = (key: string): string => {
    return key
      .replace(/_/g, ' ')
      .replace(/\bpct\b/gi, '(%)')
      .replace(/\bper\b/gi, '/')
      .replace(/\b(mo|monthly)\b/gi, 'Monthly')
      .replace(/\b(rev|revenue)\b/gi, 'Revenue')
      .replace(/\b(cogs)\b/gi, 'COGS')
      .replace(/\b(opex)\b/gi, 'OPEX')
      .replace(/\b(ebit)\b/gi, 'EBIT')
      .replace(/\b(dscr)\b/gi, 'DSCR')
      .replace(/\b(roi)\b/gi, 'ROI')
      .replace(/\b(roe)\b/gi, 'ROE')
      .replace(/\b(ccc)\b/gi, 'Cash Conversion Cycle')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="bg-white rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-premium-border"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="sticky top-0 bg-white/95 backdrop-blur-md px-6 py-5 border-b border-premium-border flex items-center justify-between z-10">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-forest/10 flex items-center justify-center text-forest">
              <Calculator size={22} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-forest-deep">{metric.label}</h2>
              <p className="text-xs text-ink-soft font-medium">Deterministic Mathematical Audit & Breakdown</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-black/5 text-ink-soft hover:text-ink transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Main Metric Hero Card */}
          <div className="bg-[#fcfbf8] p-5 rounded-2xl border border-premium-border flex flex-wrap items-center justify-between gap-4">
            <div>
              <span className="text-xs font-bold text-ink-soft uppercase tracking-wider block mb-1">Calculated Metric</span>
              <div className="text-2xl sm:text-3xl font-bold text-forest-deep">
                {metric.value != null ? (
                  <>
                    {typeof metric.value === 'number' && metric.unit?.includes('₹')
                      ? `₹${metric.value.toLocaleString('en-IN')}`
                      : `${metric.value}`}
                    <span className="text-sm font-semibold text-ink-soft ml-1.5">{metric.unit || ''}</span>
                  </>
                ) : (
                  'INSUFFICIENT_DATA'
                )}
              </div>
            </div>

            <div className="flex items-center gap-3">
              {metric.score != null && (
                <div className="text-right">
                  <span className="text-xs font-bold text-ink-soft block">Normalized Score</span>
                  <span className="text-xl font-bold text-forest">{metric.score}<span className="text-xs text-ink-soft">/100</span></span>
                </div>
              )}
              {metric.status && (
                <span className={`px-3 py-1.5 rounded-xl text-xs font-bold border ${getStatusColor(metric.status)}`}>
                  {metric.status}
                </span>
              )}
            </div>
          </div>

          {/* Mathematical Formula */}
          {metric.formula && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-forest-deep flex items-center">
                <Calculator size={14} className="mr-1.5 text-forest" /> Calculation Formula
              </h3>
              <div className="bg-[#f4f7f5] p-3.5 rounded-xl border border-[#d9e6de] font-mono text-xs text-forest-deep leading-relaxed">
                {metric.formula}
              </div>
            </div>
          )}

          {/* Underlying Inputs */}
          {metric.inputs && Object.keys(metric.inputs).length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-forest-deep flex items-center">
                <Database size={14} className="mr-1.5 text-forest" /> Underlying Parameters & Inputs
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {Object.entries(metric.inputs).map(([k, v]) => (
                  <div key={k} className="p-3 bg-cream/70 rounded-xl border border-premium-border flex justify-between items-center text-xs">
                    <span className="font-medium text-ink-soft">{formatInputLabel(k)}</span>
                    <span className="font-bold text-forest-deep text-right ml-2">{formatInputValue(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Key Drivers */}
          {metric.drivers && metric.drivers.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-forest-deep flex items-center">
                <CheckCircle size={14} className="mr-1.5 text-forest" /> Key Contributing Drivers
              </h3>
              <ul className="space-y-2">
                {metric.drivers.map((driver, i) => (
                  <li key={i} className="flex items-start text-xs font-medium text-ink leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#ea580c] mt-1.5 mr-2 shrink-0" />
                    <span>{driver}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Data Sources & Evidence */}
          {metric.sources && metric.sources.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-forest-deep flex items-center">
                <ShieldCheck size={14} className="mr-1.5 text-forest" /> Validated Data Sources & Evidence
              </h3>
              <div className="space-y-1.5">
                {metric.sources.map((src, i) => (
                  <div key={i} className="p-2.5 bg-[#fbfdfa] rounded-lg border border-[#e4eee6] text-xs font-medium text-forest-deep flex items-center">
                    <span className="w-2 h-2 rounded-full bg-[#16a34a] mr-2 shrink-0" />
                    <span>{src}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata Footer */}
          <div className="pt-4 border-t border-premium-border flex flex-wrap items-center justify-between text-[11px] text-ink-soft gap-2">
            <div className="flex items-center">
              <ShieldCheck size={13} className="mr-1 text-[#16a34a]" />
              <span>Confidence: <strong>{Math.round((metric.confidence || 0.85) * 100)}%</strong> (Deterministic Arithmetic)</span>
            </div>
            {metric.timestamp && (
              <div className="flex items-center">
                <Clock size={13} className="mr-1" />
                <span>Audited: {new Date(metric.timestamp).toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
