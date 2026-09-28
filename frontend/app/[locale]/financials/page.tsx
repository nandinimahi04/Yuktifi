"use client";
import React, { useEffect, useState } from "react";
import { useStore } from "@/lib/store";
import { api, FinanceResponse } from "@/lib/api-client";
import dynamic from "next/dynamic";
import {
  IndianRupee, TrendingUp, TrendingDown, AlertTriangle, Loader2,
  CheckCircle, CreditCard, BarChart3, CalendarDays, Target,
  ShieldAlert, Wallet, Clock, ArrowRight, Info, FileSearch, HelpCircle, Edit2, Save, X
} from "lucide-react";

// Lazy-load standalone chart components — keeping Recharts internal subcomponents
// statically imported within each component preserves Recharts internal type-matching.
const CashFlowChart = dynamic(() => import("@/components/financials/CashFlowChart"), {
  ssr: false,
  loading: () => <div className="w-full h-80 bg-gray-50 rounded-2xl animate-pulse flex items-center justify-center text-xs text-ink-soft">Loading Charts...</div>
});

const SeasonalChart = dynamic(() => import("@/components/financials/SeasonalChart"), {
  ssr: false,
  loading: () => <div className="w-full h-72 bg-gray-50 rounded-2xl animate-pulse flex items-center justify-center text-xs text-ink-soft">Loading Chart...</div>
});



// ─── Helpers ───────────────────────────────────────────────────────────────

// Null-safe formatters. These were declared `(n: number)`, but every value they
// are called with comes from the API and can legitimately be null: an undeclared
// rate, an undeclared tenure, a break-even that could not be computed. With a
// number-only signature, `fmt(null)` reached `Math.round(null)` and rendered
// "₹NaN" - a figure that looks like a corrupted display rather than an honest
// "not available", which is the failure mode the whole page is trying to avoid.
const NA = "—";

const fmt = (n: number | null | undefined) =>
  n == null || Number.isNaN(n)
    ? NA
    : n >= 100000
      ? `₹${(n / 100000).toFixed(1)}L`
      : `₹${Math.round(n).toLocaleString("en-IN")}`;

const fmtFull = (n: number | null | undefined) =>
  n == null || Number.isNaN(n) ? NA : `₹${Math.round(n).toLocaleString("en-IN")}`;

// Flip the sign of a financial deduction for display, preserving "unknown".
// `- null` is 0, which would print a cost line that was never computed as if it
// had been measured at zero.
const negate = (n: number | null | undefined) => (n == null ? null : -n);

// Render a signed amount, or say plainly that it is not available. A missing
// figure must never be coerced: `null >= 0` is false, so the old comparison
// below would have printed every null as "- ₹0", a measured nil cost.
const fmtSigned = (n: number | null | undefined) => {
  if (n == null || Number.isNaN(n)) return NA;
  return n < 0 ? `- ${fmtFull(Math.abs(n))}` : fmtFull(n);
};

// A percentage, or a dash. The cards below used to concatenate `%` onto a value
// that could be undefined, printing "undefined%".
const fmtPct = (n: number | null | undefined) =>
  n == null || Number.isNaN(n) ? NA : `${n}%`;

const TABS = [
  { key: "overview",    label: "Overview",       icon: BarChart3 },
  { key: "cashflow",    label: "Cash Flow",       icon: TrendingUp },
  { key: "pnl",         label: "P&L",             icon: IndianRupee },
  { key: "breakeven",   label: "Break-Even",      icon: Target },
  { key: "loan",        label: "Loan & Monthly Installment",      icon: CreditCard },
  { key: "working",     label: "Working Capital", icon: Wallet },
  { key: "scenarios",   label: "Scenarios",       icon: ShieldAlert },
  { key: "seasonal",    label: "Seasonal",        icon: CalendarDays },
  { key: "evidence",    label: "Evidence & Gaps", icon: FileSearch },
];

// ─── Summary Card ────────────────────────────────────────────────────────────

const SummaryCard = ({ label, value, sub, color = "text-ink", icon: Icon }: any) => (
  <div className="bg-white rounded-2xl p-5 border border-premium-border shadow-sm flex flex-col gap-2">
    <div className="flex items-center justify-between">
      <span className="text-xs font-bold text-ink-soft uppercase tracking-wide">{label}</span>
      <Icon size={16} className="text-ink-faint" />
    </div>
    <div className={`text-2xl font-bold font-display ${color}`}>{value}</div>
    {sub && <div className="text-xs font-medium text-ink-soft">{sub}</div>}
  </div>
);

const EditableSummaryCard = ({ label, value, fieldName, originalValue, sub, color = "text-ink", icon: Icon, onSave, isRecalculating }: any) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");

  const handleEdit = () => {
    setEditValue(originalValue != null ? originalValue.toString() : "");
    setIsEditing(true);
  };

  const handleSave = () => {
    if (editValue && !isNaN(Number(editValue))) {
      onSave(fieldName, Number(editValue));
    }
    setIsEditing(false);
  };

  return (
    <div className="bg-white rounded-2xl p-5 border border-amber-200 shadow-sm flex flex-col gap-2 group relative">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-amber-600 uppercase tracking-wide flex items-center gap-1">
          {label} {isRecalculating && <Loader2 size={12} className="animate-spin" />}
        </span>
        <Icon size={16} className="text-amber-500" />
      </div>
      {!isEditing ? (
        <div className="flex items-center justify-between">
          <div className={`text-2xl font-bold font-display ${color} ${isRecalculating ? 'opacity-50' : ''}`}>{value}</div>
          <button onClick={handleEdit} className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-amber-50 rounded text-amber-600 transition-opacity" disabled={isRecalculating}>
            <Edit2 size={14} />
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <input 
            type="number" 
            className={`text-lg font-bold font-display ${color} border border-amber-300 rounded px-2 py-1 w-full outline-none focus:border-amber-500`} 
            value={editValue} 
            onChange={(e) => setEditValue(e.target.value)} 
            autoFocus
            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
          />
          <button onClick={handleSave} className="p-1 text-green-600 hover:bg-green-50 rounded"><Save size={16}/></button>
          <button onClick={() => setIsEditing(false)} className="p-1 text-red-500 hover:bg-red-50 rounded"><X size={16}/></button>
        </div>
      )}
      {sub && <div className="text-xs font-medium text-amber-600/80">{sub}</div>}
    </div>
  );
};

// ─── Overview Tab ────────────────────────────────────────────────────────────

const OverviewTab = ({ data }: { data: FinanceResponse }) => {
  const scheme = data.scheme as any;
  const schemeName = scheme?.scheme_name || "Standard Bank Loan";
  const { analysisResult, updateState, sessionId } = useStore();
  const [isRecalculating, setIsRecalculating] = useState(false);

  const handleOverride = async (fieldName: string, value: number) => {
    if (!sessionId) return;
    setIsRecalculating(true);
    try {
      const overrides = { [fieldName]: value };
      const newFinancials = await api.calculateFinance({ session_id: sessionId, overrides });
      if (analysisResult) {
        useStore.setState({
          analysisResult: {
            ...analysisResult,
            financials: newFinancials
          }
        });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsRecalculating(false);
    }
  };

  return (
    <div className="animate-in fade-in duration-300">
      <h2 className="text-xl font-bold text-forest-deep mb-6">Financial Overview</h2>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
        <EditableSummaryCard label="Project Cost" value={fmt(data.project_cost)} originalValue={data.project_cost} fieldName="project_cost" onSave={handleOverride} isRecalculating={isRecalculating} sub="Total capital required" icon={Wallet} color="text-ink" />
        <EditableSummaryCard label="Loan Amount" value={fmt(data.loan_amount)} originalValue={data.loan_amount} fieldName="loan_amount" onSave={handleOverride} isRecalculating={isRecalculating} sub={data.rate != null ? `@ ${data.rate}% p.a.` : "Rate not declared"} icon={CreditCard} color="text-[#2563eb]" />
        <EditableSummaryCard
          label="Your Contribution"
          value={fmt(data.beneficiary_contribution)}
          originalValue={data.beneficiary_contribution}
          fieldName="own_capital"
          onSave={handleOverride}
          isRecalculating={isRecalculating}
          sub={data.project_cost > 0
            ? `${((data.beneficiary_contribution / data.project_cost) * 100).toFixed(0)}% of project cost`
            : "Own margin"}
          icon={IndianRupee}
          color="text-[#16a34a]"
        />
        <SummaryCard label="Monthly Installment" value={fmtFull(data.emi)} sub={data.tenure_months != null ? `Over ${data.tenure_months} months` : "Tenure not declared"} icon={Clock} color="text-[#ea580c]" />
        <EditableSummaryCard label="Monthly Revenue" value={fmt(data.monthly_revenue)} originalValue={data.monthly_revenue} fieldName="monthly_revenue" onSave={handleOverride} isRecalculating={isRecalculating} sub="Expected earnings" icon={TrendingUp} color="text-[#16a34a]" />
        <EditableSummaryCard label="Monthly Expenses" value={fmt(data.monthly_opex)} originalValue={data.monthly_opex} fieldName="monthly_expenses" onSave={handleOverride} isRecalculating={isRecalculating} sub="OPEX + Variable" icon={TrendingDown} color="text-red-500" />
        <SummaryCard
          label="Net Profit / Month"
          value={fmt(data.net_profit)}
          sub="After depreciation, interest & tax"
          icon={Target}
          color={data.net_profit >= 0 ? "text-[#16a34a]" : "text-red-500"}
        />
        <SummaryCard
          label="Annual Return on Project"
          value={`${data.roi}%`}
          sub={
            data.roi_on_owner_equity_pct != null
              ? `${data.roi_on_owner_equity_pct}% on your ${fmt(data.beneficiary_contribution)}`
              : "On total project cost"
          }
          icon={BarChart3}
          color={data.roi >= 15 ? "text-[#16a34a]" : "text-[#ea580c]"}
        />
      </div>

      <h3 className="text-lg font-bold text-forest-deep mt-8 mb-4">Underlying Assumptions</h3>
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-8">
        <EditableSummaryCard label="Selling Price" value={fmt(data.pnl_statement?.revenue ? data.pnl_statement.revenue / (data.monthly_revenue ? 1 : 1) : 0)} originalValue={0} fieldName="selling_price" onSave={handleOverride} isRecalculating={isRecalculating} sub="Per Unit" icon={IndianRupee} color="text-ink" />
        <EditableSummaryCard label="Units / Day" value={"-"} originalValue={0} fieldName="units_per_day" onSave={handleOverride} isRecalculating={isRecalculating} sub="Expected" icon={TrendingUp} color="text-ink" />
        <EditableSummaryCard label="Operating Days" value={data.operating_days_per_month ?? "-"} originalValue={data.operating_days_per_month ?? 30} fieldName="operating_days" onSave={handleOverride} isRecalculating={isRecalculating} sub="Per Month" icon={CalendarDays} color="text-ink" />
        <EditableSummaryCard label="Interest Rate" value={`${data.rate ?? 0}%`} originalValue={data.rate ?? 9} fieldName="interest_rate" onSave={handleOverride} isRecalculating={isRecalculating} sub="Annual %" icon={TrendingDown} color="text-ink" />
        <EditableSummaryCard label="Loan Tenure" value={`${data.tenure_months ?? 0} mo`} originalValue={data.tenure_months ?? 60} fieldName="loan_tenure" onSave={handleOverride} isRecalculating={isRecalculating} sub="Months" icon={Clock} color="text-ink" />
      </div>

      {data.financial_status?.value === "INSUFFICIENT_INPUT" ? (
         <div className="bg-red-50 border border-red-200 rounded-xl p-10 text-center text-red-600 animate-in fade-in">
           <AlertTriangle size={48} className="mx-auto mb-4 opacity-80" />
           <h3 className="text-lg font-bold mb-2">Detailed Projections Blocked</h3>
           <p>Please provide Project Cost and Monthly Revenue to generate the full financial model.</p>
         </div>
      ) : (
        <>
          {/* Scheme Info - Highlighted */}
          <div className="relative bg-gradient-to-br from-[#16a34a] to-[#14532d] rounded-2xl p-6 text-white mb-6 shadow-[0_0_20px_rgba(22,163,74,0.3)] border border-[#22c55e]/30 overflow-hidden transform transition-transform hover:scale-[1.01]">
            <div className="absolute top-0 right-0 bg-[#fde047] text-[#854d0e] text-xs font-bold px-3 py-1 rounded-bl-xl z-10 flex items-center">
              <CheckCircle size={12} className="mr-1" /> Best Match
            </div>
            <div className="absolute -right-4 -top-4 w-24 h-24 bg-white/5 rounded-full blur-xl"></div>
            <div className="absolute -right-2 -bottom-2 w-32 h-32 bg-[#22c55e]/20 rounded-full blur-2xl"></div>
            <div className="relative z-10 flex flex-col md:flex-row items-start justify-between gap-6">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#fde047] opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-[#fde047]"></span>
                  </span>
                  <p className="text-sm font-bold text-[#fde047]">Eligible Government Scheme</p>
                </div>
                <h3 className="text-2xl font-bold mb-3 drop-shadow-sm">{schemeName}</h3>
                <div className="inline-flex flex-wrap gap-4 bg-black/20 rounded-lg px-4 py-2 backdrop-blur-sm mb-4">
                  <p className="text-sm text-white/90">
                    Interest: <span className="font-bold text-white text-base">{data.rate}%</span>
                  </p>
                  <div className="hidden sm:block w-px bg-white/20"></div>
                  <p className="text-sm text-white/90">
                    Tenure: <span className="font-bold text-white text-base">{data.tenure_months != null ? `${Math.round(data.tenure_months / 12)} yrs` : "not declared"}</span>
                  </p>
                  {data.moratorium_months > 0 && (
                    <>
                      <div className="hidden sm:block w-px bg-white/20"></div>
                      <p className="text-sm text-white/90">
                        Moratorium: <span className="font-bold text-white text-base">{data.moratorium_months} mos</span>
                      </p>
                    </>
                  )}
                </div>
                {scheme?.explanation && (
                  <p className="text-sm text-white/80 leading-relaxed mb-4 max-w-2xl">
                    {scheme.explanation}
                  </p>
                )}
                {scheme?.source_url && (
                  <a 
                    href={scheme.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-5 py-2.5 bg-white text-forest-deep rounded-xl font-bold text-sm hover:bg-[#fcfbf8] transition-colors shadow-sm"
                  >
                    Apply for this Scheme <ArrowRight size={16} className="ml-2" />
                  </a>
                )}
              </div>
            </div>
          </div>

          {/* Loan Repayment Capacity */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white rounded-2xl p-5 border border-premium-border shadow-sm">
              <p className="text-xs font-bold text-ink-soft uppercase mb-1">Loan Repayment Capacity</p>
              <div className={`text-3xl font-bold font-display mb-1 ${
                data.dscr == null
                  ? "text-ink-soft"
                  : data.dscr >= 1.5
                    ? "text-[#16a34a]"
                    : data.dscr >= 1.0
                      ? "text-[#ea580c]"
                      : "text-red-500"
              }`}>{data.dscr == null ? "N/A" : `${data.dscr}x`}</div>
              <p className="text-sm text-ink-soft">
                {data.dscr == null
                  ? "No debt is assumed for this plan, so repayment coverage does not apply."
                  : data.dscr >= 1.5
                    ? "✅ Strong repayment ability"
                    : data.dscr >= 1.0
                      ? "⚠️ Adequate — manage costs tightly"
                      : "🔴 Weak — reconsider the capital plan"}
              </p>
            </div>
            <div className="bg-white rounded-2xl p-5 border border-premium-border shadow-sm">
              <p className="text-xs font-bold text-ink-soft uppercase mb-1">Break-Even Units / Month</p>
              <div className="text-3xl font-bold font-display text-[#6366f1] mb-1">
                {data.break_even_units == null ? "N/A" : `${Math.round(data.break_even_units)} units`}
              </div>
              <p className="text-sm text-ink-soft">
                {data.break_even_units == null
                  ? "Break-even cannot be stated because contribution per unit is not positive."
                  : data.operating_days_per_month == null
                    ? "Break-even is stated per month. The working days per month were not declared, so a per-day figure is not available."
                    : `You need to sell ${Math.round(data.break_even_units / data.operating_days_per_month)} units per working day to cover all costs.`}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// ─── Cash Flow Tab ────────────────────────────────────────────────────────────

const CashFlowTab = ({ data }: { data: FinanceResponse }) => {
  const cf = data.cashflow_projection;
  const breakEvenMonth = cf.find(m => m.cumulative >= 0);

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-forest-deep">12-Month Cash Flow Projection</h2>
          <p className="text-sm text-ink-soft mt-1">Revenue vs Expenses (seasonal variations applied)</p>
        </div>
        {breakEvenMonth && (
          <div className="bg-[#f0fdf4] border border-[#bbf7d0] rounded-xl px-4 py-2 text-right">
            <p className="text-xs font-bold text-[#16a34a]">BREAK-EVEN MONTH</p>
            <p className="font-bold text-[#16a34a]">{breakEvenMonth.month} (Month {breakEvenMonth.month_num})</p>
          </div>
        )}
      </div>

      <CashFlowChart data={cf} />
    </div>
  );
};

// ─── P&L Tab ─────────────────────────────────────────────────────────────────

const PnlTab = ({ data }: { data: FinanceResponse }) => {
  const pnl = data.pnl_statement;
  if (!pnl) return <p className="text-ink-soft">P&L data not available.</p>;

  // The full waterfall the engine actually computes, in the engine's order.
  // This previously jumped from gross profit straight to "EBIT (Earnings before
  // Tax)" - naming EBIT as earnings before tax, which is not what EBIT is - and
  // then printed an income tax line fed by a hardcoded 0.
  const rows: {
    label: string;
    value: number | null;
    bold?: boolean;
    highlight?: boolean;
    color?: string;
    note?: string | null;
  }[] = [
    { label: "Revenue (Gross Sales)", value: pnl.revenue, bold: true, color: "text-[#16a34a]" },
    { label: "(-) Cost of Goods Sold (COGS)", value: negate(pnl.cogs), color: "text-red-500" },
    { label: "= Gross Profit", value: pnl.gross_profit, bold: true, highlight: true },
    { label: "(-) Operating Expenses (OPEX)", value: negate(pnl.operating_expenses), color: "text-red-500" },
    { label: "= EBITDA", value: pnl.ebitda, bold: true },
    { label: "(-) Depreciation", value: negate(pnl.depreciation), color: "text-red-500" },
    { label: "= EBIT (Earnings Before Interest and Tax)", value: pnl.ebit, bold: true },
    { label: "(-) Interest", value: negate(pnl.interest), color: "text-red-500" },
    { label: "(-) Income Tax", value: negate(pnl.tax), color: "text-red-500", note: pnl.tax_status },
  ];
  const pnlNetProfit = pnl.net_profit;
  const patRow: (typeof rows)[number] = {
    label: "= Net Profit (PAT)",
    value: pnlNetProfit,
    bold: true,
    highlight: true,
    color: typeof pnlNetProfit === "number" && pnlNetProfit >= 0 ? "text-[#16a34a]" : "text-red-500",
  };
  const allRows = [...rows, patRow];

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-forest-deep">Monthly P&L Statement</h2>
          <p className="text-sm text-ink-soft mt-1">Projected monthly income statement for your business</p>
        </div>
        <div className="text-right">
          <p className="text-xs font-bold text-ink-soft">Gross Margin</p>
          <p className="text-2xl font-bold text-[#16a34a]">{fmtPct(pnl.gross_margin_pct)}</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-premium-border shadow-sm overflow-hidden mb-6">
        <div className="px-6 py-3 bg-[#f9f8f5] border-b border-premium-border flex justify-between">
          <span className="text-xs font-bold text-ink-soft uppercase">Line Item</span>
          <span className="text-xs font-bold text-ink-soft uppercase">Monthly Amount</span>
        </div>
        {allRows.map((row, i) => (
          <div
            key={i}
            className={`px-6 py-4 flex justify-between items-center border-b border-premium-border/50 last:border-0 ${row.highlight ? "bg-[#f0fdf4]" : ""}`}
          >
            <span className={`text-sm ${row.bold ? "font-bold text-ink" : "font-medium text-ink-soft"}`}>
              {row.label}
              {row.note ? (
                <span className="ml-2 text-[11px] font-normal uppercase tracking-wide text-ink-soft">
                  ({row.note.toLowerCase().replace(/_/g, " ")})
                </span>
              ) : null}
            </span>
            <span
              className={`text-sm font-bold font-display ${
                row.color ||
                (typeof row.value === "number" && row.value < 0 ? "text-red-500" : "text-ink")
              }`}
            >
              {fmtSigned(row.value)}
            </span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#f0fdf4] rounded-2xl border border-[#bbf7d0] p-5">
          <p className="text-xs font-bold text-[#16a34a] mb-1">Gross Margin</p>
          <p className="text-2xl font-bold text-[#16a34a]">{fmtPct(pnl.gross_margin_pct)}</p>
        </div>
        {/* Colour this on the number, and say nothing about performance when the
            number is absent. The old `pnl.net_margin_pct >= 10` test is false for
            null, so an uncomputed margin was rendered as a red warning badge. */}
        <div
          className={`rounded-2xl border p-5 ${
            pnl.net_margin_pct == null
              ? "bg-white border-premium-border"
              : pnl.net_margin_pct >= 10
                ? "bg-[#f0fdf4] border-[#bbf7d0]"
                : "bg-[#fff7ed] border-[#fed7aa]"
          }`}
        >
          <p
            className={`text-xs font-bold mb-1 ${
              pnl.net_margin_pct == null
                ? "text-ink-soft"
                : pnl.net_margin_pct >= 10
                  ? "text-[#16a34a]"
                  : "text-[#ea580c]"
            }`}
          >
            Net Margin
          </p>
          <p
            className={`text-2xl font-bold ${
              pnl.net_margin_pct == null
                ? "text-ink-soft"
                : pnl.net_margin_pct >= 10
                  ? "text-[#16a34a]"
                  : "text-[#ea580c]"
            }`}
          >
            {fmtPct(pnl.net_margin_pct)}
          </p>
        </div>
        <div className="bg-white rounded-2xl border border-premium-border p-5">
          <p className="text-xs font-bold text-ink-soft mb-1">Annual Net Profit</p>
          <p className="text-2xl font-bold text-ink">
            {pnl.net_profit == null ? NA : fmt(pnl.net_profit * 12)}
          </p>
        </div>
      </div>
    </div>
  );
};

// ─── Break-Even Tab ───────────────────────────────────────────────────────────

const BreakEvenTab = ({ data }: { data: FinanceResponse }) => {
  const breakEven = data.break_even_units;
  const days = data.operating_days_per_month ?? null;
  // Per working day, using the days the plan actually declares. The 26 that was
  // hardcoded here is one particular month; a stall open six days a week for
  // four weeks and one open seven days a month produce different daily
  // break-evens from the same monthly figure.
  const dailyUnits =
    breakEven == null || days == null || days <= 0 ? null : Math.ceil(breakEven / days);

  // The engine's margin of safety. This used to be a "capacity utilisation"
  // bar computed as break-even divided by monthly revenue divided by 100, i.e.
  // a ratio that assumed every business sells something at ₹100. It moved with
  // the price the customer happened to charge, and had no meaning at all.
  const safety = data.margin_of_safety_pct;
  const safetyWidth =
    safety == null ? null : Math.max(0, Math.min(100, Math.round(safety)));

  if (breakEven == null) {
    return (
      <div className="animate-in fade-in duration-300">
        <h2 className="text-xl font-bold text-forest-deep mb-6">Break-Even Analysis</h2>
        <div className="bg-white border border-premium-border rounded-2xl p-8">
          <p className="text-sm text-ink-soft leading-relaxed">
            Break-even cannot be stated for this plan because contribution per unit is
            not positive &mdash; every additional sale would lose money. Review the
            pricing and unit cost assumptions before proceeding.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in duration-300">
      <h2 className="text-xl font-bold text-forest-deep mb-6">Break-Even Analysis</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="col-span-1 md:col-span-2 bg-white rounded-2xl border border-premium-border p-8 shadow-sm flex flex-col items-center justify-center text-center">
          <p className="text-sm font-bold text-ink-soft mb-2">Monthly Break-Even Units</p>
          <p className="text-6xl font-bold font-display text-[#6366f1] mb-2">{Math.round(breakEven)}</p>
          <p className="text-sm text-ink-soft mb-6">units / customers per month</p>
          <div className="w-full bg-gray-100 rounded-full h-4 mb-2">
            <div
              className="bg-[#6366f1] h-4 rounded-full transition-all"
              style={{ width: `${safetyWidth ?? 0}%` }}
            />
          </div>
          <p className="text-xs text-ink-soft">
            {safetyWidth == null
              ? "Margin of safety is not available for this plan."
              : `${safetyWidth}% of current revenue is the headroom above break-even`}
          </p>
        </div>
        <div className="flex flex-col gap-4">
          <div className="bg-[#eff6ff] border border-[#bfdbfe] rounded-2xl p-5">
            <p className="text-xs font-bold text-[#2563eb] mb-1">Per Working Day</p>
            <p className="text-3xl font-bold text-[#2563eb]">
              {dailyUnits == null ? "N/A" : dailyUnits}
            </p>
            <p className="text-xs text-ink-soft mt-1">
              {days == null
                ? "units/customers/day — working days not declared"
                : "units/customers/day"}
            </p>
          </div>
          <div className="bg-white border border-premium-border rounded-2xl p-5">
            <p className="text-xs font-bold text-ink-soft mb-1">Monthly Operating Cost</p>
            <p className="text-2xl font-bold text-ink">{fmt(data.monthly_opex)}</p>
            <p className="text-xs text-ink-soft mt-1">as reported by the engine</p>
          </div>
        </div>
      </div>
      <div className="bg-[#f9f8f5] border border-premium-border rounded-2xl p-5">
        <div className="flex items-start">
          <Info size={16} className="text-[#6366f1] mr-2 mt-0.5 shrink-0" />
          <p className="text-sm text-ink-soft leading-relaxed">
            Once you cross <strong className="text-ink">{Math.round(breakEven)} units/month</strong>, every additional sale becomes pure profit.
            Focus your first 3 months on reaching this milestone through local marketing and word-of-mouth.
          </p>
        </div>
      </div>
    </div>
  );
};

// ─── Loan & Monthly Installment Tab ───────────────────────────────────────────────────────────

const LoanTab = ({ data }: { data: FinanceResponse }) => {
  const scheme = data.scheme as any;
  // Total repayable and total interest are the engine's own totals from its
  // amortisation schedule. This used to be `emi * (tenure - moratorium)`, which
  // multiplies a level payment by the post-moratorium count: it ignores that a
  // moratorium is interest-only, and it cannot know that the final instalment is
  // smaller than the rest. Reading the schedule's own totals is the difference
  // between a number that ties to the table below it and one that does not.
  const totalPayable = data.total_repayment ?? null;
  const totalInterest = data.total_interest_paid ?? null;

  // Render the engine's own reducing-balance schedule. Recomputing it here
  // would let the table disagree with every other financial surface.
  const amortRows = (data.loan_schedule ?? []).slice(0, 6);

  return (
    <div className="animate-in fade-in duration-300">
      <h2 className="text-xl font-bold text-forest-deep mb-6">Loan & Monthly Installment Details</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <SummaryCard label="Loan Amount" value={fmt(data.loan_amount)} icon={CreditCard} color="text-[#2563eb]" />
        <SummaryCard label="Interest Rate" value={data.rate != null ? `${data.rate}%` : "Not declared"} sub="Per annum" icon={TrendingUp} color="text-[#ea580c]" />
        <SummaryCard label="Monthly Monthly Installment" value={fmtFull(data.emi)} sub={data.tenure_months != null ? `For ${data.tenure_months - data.moratorium_months} months` : "Tenure not declared"} icon={Clock} color="text-ink" />
        <SummaryCard label="Total Interest" value={fmt(totalInterest)} sub="Total cost of credit" icon={IndianRupee} color="text-red-500" />
      </div>

      <div className="bg-white rounded-2xl border border-premium-border shadow-sm overflow-hidden">
        <div className="px-6 py-4 bg-[#f9f8f5] border-b border-premium-border">
          <h3 className="font-bold text-forest-deep">Monthly Installment Amortization (First 6 Months)</h3>
        </div>
        <div className="overflow-x-auto">
        <table className="w-full text-sm">
            <thead className="bg-[#f9f8f5]">
              <tr className="text-xs font-bold text-ink-soft border-b border-premium-border">
                <th className="px-4 py-3 text-left">Period</th>
                <th className="px-4 py-3 text-right">Monthly Installment</th>
                <th className="px-4 py-3 text-right hidden sm:table-cell">Interest</th>
                <th className="px-4 py-3 text-right hidden sm:table-cell">Principal</th>
                <th className="px-4 py-3 text-right">Balance</th>
              </tr>
            </thead>
            <tbody>
              {amortRows.map((row) => (
                <tr key={row.month} className="border-b border-premium-border/50 hover:bg-[#f9f8f5]">
                  <td className="px-4 py-3 font-medium text-xs">Month {row.month}</td>
                  <td className="px-4 py-3 text-right font-bold text-ink">{fmtFull(row.payment)}</td>
                  <td className="px-4 py-3 text-right text-red-500 hidden sm:table-cell">{fmtFull(row.interest)}</td>
                  <td className="px-4 py-3 text-right text-[#16a34a] hidden sm:table-cell">{fmtFull(row.principal_repaid)}</td>
                  <td className="px-4 py-3 text-right text-ink-soft">{fmtFull(row.closing_balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-6 py-3 text-xs text-ink-soft bg-[#f9f8f5] border-t border-premium-border">
          {data.moratorium_months > 0 && `⏸ Moratorium period: ${data.moratorium_months} months (no Monthly Installment). `}
          Monthly Installment payments start from Month {data.moratorium_months + 1}.
        </div>
      </div>
    </div>
  );
};

// ─── Working Capital Tab ──────────────────────────────────────────────────────

const WorkingCapitalTab = ({ data }: { data: FinanceResponse }) => {
  const wc = data.working_capital;
  if (!wc) return <p className="text-ink-soft">Working capital data not available.</p>;

  // Whether the entrepreneur's contribution covers the working-capital need is
  // only answerable when both figures exist. With an unknown requirement the
  // screen says so rather than reporting a shortfall against a number nobody
  // computed.
  const monthlyWc = wc.monthly_working_capital;
  const canJudgeBuffer =
    typeof data.beneficiary_contribution === "number" && typeof monthlyWc === "number";
  const isBufferOk = canJudgeBuffer ? data.beneficiary_contribution >= monthlyWc : null;

  // A cycle day count that was not declared must not be printed as "0 days of
  // stock", which reads as an instant-turnover inventory nobody holds.
  const daysLabel = (n: number | null, unit: string) =>
    n == null ? `${unit} not declared` : `${n} days`;

  return (
    <div className="animate-in fade-in duration-300">
      <h2 className="text-xl font-bold text-forest-deep mb-6">Working Capital Requirement</h2>
      
      <div className={`rounded-2xl border p-5 mb-6 flex items-start gap-4 ${isBufferOk === true ? "bg-[#f0fdf4] border-[#bbf7d0]" : isBufferOk === false ? "bg-[#fff7ed] border-[#fed7aa]" : "bg-white border-premium-border"}`}>
        {isBufferOk === true ? <CheckCircle className="text-[#16a34a] shrink-0 mt-0.5" size={20} /> : isBufferOk === false ? <AlertTriangle className="text-[#ea580c] shrink-0 mt-0.5" size={20} /> : <Info className="text-ink-soft shrink-0 mt-0.5" size={20} />}
        <div>
          <p className={`font-bold mb-1 ${isBufferOk === true ? "text-[#16a34a]" : isBufferOk === false ? "text-[#ea580c]" : "text-ink"}`}>
            {isBufferOk === true
              ? "Working Capital is Sufficient"
              : isBufferOk === false
                ? "Working Capital Warning"
                : "Working Capital not assessed"}
          </p>
          <p className="text-sm text-ink-soft">
            {isBufferOk === true
              ? `Your contribution (${fmt(data.beneficiary_contribution)}) comfortably covers the monthly working capital need (${fmt(wc.monthly_working_capital)}).`
              : isBufferOk === false
                ? `Your contribution (${fmt(data.beneficiary_contribution)}) may not fully cover working capital needs (${fmt(wc.monthly_working_capital)}). Consider negotiating extended payment terms with suppliers.`
                : "The working-capital requirement was not computed, so this plan's contribution cannot be compared against it."}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <SummaryCard label="Daily Cash Needed" value={fmtFull(wc.daily_cash_needed)} sub="Operating float" icon={IndianRupee} color="text-ink" />
        <SummaryCard label="Weekly Cash Needed" value={fmtFull(wc.weekly_cash_needed)} sub="Weekly float" icon={IndianRupee} color="text-ink" />
        <SummaryCard label="Net Working Capital" value={fmt(wc.monthly_working_capital)} sub="Monthly WC requirement" icon={Wallet} color="text-[#2563eb]" />
        <SummaryCard label="Inventory Held" value={fmt(wc.inventory_requirement)} sub={daysLabel(wc.inventory_days, "Stock cycle")} icon={BarChart3} color="text-ink" />
        <SummaryCard label="Receivables" value={fmt(wc.receivables)} sub={wc.receivable_days == null ? "Collection cycle not declared" : `Collect within ${wc.receivable_days} days`} icon={TrendingUp} color="text-[#ea580c]" />
        <SummaryCard label="Payables" value={fmt(wc.payables)} sub={wc.payable_days == null ? "Payment cycle not declared" : `Pay within ${wc.payable_days} days`} icon={TrendingDown} color="text-[#16a34a]" />
      </div>

      <div className="bg-white rounded-2xl border border-premium-border p-5 shadow-sm">
        <div className="flex items-center mb-3">
          <Info size={16} className="text-[#6366f1] mr-2" />
          <h3 className="font-bold text-ink">Recommended Safety Buffer</h3>
        </div>
        <div className="text-3xl font-bold text-[#6366f1] mb-2">{fmt(wc.recommended_buffer)}</div>
        <p className="text-sm text-ink-soft">Keep this as emergency working capital reserve. Do not invest it all in stock on Day 1.</p>
      </div>
    </div>
  );
};

// ─── Revenue Scenarios Tab ────────────────────────────────────────────────────

const ScenariosTab = ({ data }: { data: FinanceResponse }) => {
  const s = data.revenue_scenarios;
  if (!s || !s.pessimistic) return <p className="text-ink-soft">Scenario data not available.</p>;

  const scenarios = [
    { key: "pessimistic", label: "Pessimistic", desc: "60% capacity utilization — slow start, low demand", color: "text-red-500", bg: "bg-[#fff1f2]", border: "border-[#fecdd3]", icon: TrendingDown },
    { key: "realistic",   label: "Realistic",   desc: "100% capacity — steady, expected performance",  color: "text-[#ea580c]", bg: "bg-[#fff7ed]", border: "border-[#fed7aa]", icon: Target },
    { key: "optimistic",  label: "Optimistic",  desc: "130% capacity — strong demand, effective marketing", color: "text-[#16a34a]", bg: "bg-[#f0fdf4]", border: "border-[#bbf7d0]", icon: TrendingUp },
  ];

  return (
    <div className="animate-in fade-in duration-300">
      <h2 className="text-xl font-bold text-forest-deep mb-2">Revenue Scenarios</h2>
      <p className="text-sm text-ink-soft mb-6">Three projections based on different market capture rates.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {scenarios.map(({ key, label, desc, color, bg, border, icon: Icon }) => {
          const sc = (s as any)[key];
          return (
            <div key={key} className={`${bg} border ${border} rounded-2xl p-6`}>
              <div className="flex items-center mb-3">
                <Icon size={18} className={`${color} mr-2`} />
                <h3 className={`font-bold ${color}`}>{label}</h3>
              </div>
              <p className="text-xs text-ink-soft mb-4 leading-relaxed">{desc}</p>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-xs text-ink-soft">Monthly Revenue</span>
                  <span className="text-sm font-bold text-ink">{fmt(sc.monthly_revenue)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-ink-soft">Monthly Expenses</span>
                  <span className="text-sm font-bold text-ink">{fmt(sc.monthly_opex)}</span>
                </div>
                <div className="flex justify-between border-t border-black/10 pt-2">
                  <span className="text-xs font-bold text-ink-soft">Net Profit / Month</span>
                  <span className={`text-sm font-bold ${sc.monthly_net_profit >= 0 ? color : "text-red-500"}`}>{fmt(sc.monthly_net_profit)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-ink-soft">Annual Net Profit</span>
                  <span className={`text-sm font-bold ${color}`}>{fmt(sc.annual_net_profit)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-ink-soft">Return on Investment</span>
                  <span className={`text-sm font-bold ${color}`}>{sc.roi_pct}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-ink-soft">Payback Period</span>
                  <span className="text-sm font-bold text-ink">{sc.payback_months ? `${sc.payback_months} months` : "N/A"}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {data.payback_period && (
        <div className="bg-gradient-to-br from-[#6366f1] to-[#4f46e5] text-white rounded-2xl p-6">
          <p className="text-sm font-bold text-white/70 mb-1">Realistic Payback Period</p>
          <p className="text-4xl font-bold font-display mb-2">
            {data.payback_period.payback_months ? `${data.payback_period.payback_months} months` : "50+ months"}
          </p>
          <p className="text-sm text-white/80">{data.payback_period.note}</p>
        </div>
      )}
    </div>
  );
};

// ─── Seasonal Forecast Tab ────────────────────────────────────────────────────

const SeasonalTab = ({ data }: { data: FinanceResponse }) => {
  const seasonal = data.seasonal_revenue;
  if (!seasonal || seasonal.length === 0) return <p className="text-ink-soft">Seasonal data not available.</p>;

  const maxRev = Math.max(...seasonal.map(m => m.revenue));
  const minRev = Math.min(...seasonal.map(m => m.revenue));

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-forest-deep">Seasonal Revenue Forecast</h2>
          <p className="text-sm text-ink-soft mt-1">12-month demand variation based on your business category</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-ink-soft">Peak Revenue</p>
          <p className="font-bold text-[#16a34a]">{fmt(maxRev)}</p>
          <p className="text-xs text-ink-soft mt-1">Lowest Revenue</p>
          <p className="font-bold text-[#ea580c]">{fmt(minRev)}</p>
        </div>
      </div>

      <SeasonalChart data={seasonal} maxRev={maxRev} minRev={minRev} />

      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
        {seasonal.map((m) => (
          <div
            key={m.month}
            className={`rounded-xl p-3 text-center border ${m.revenue === maxRev ? "bg-[#f0fdf4] border-[#bbf7d0]" : m.revenue === minRev ? "bg-[#fff1f2] border-[#fecdd3]" : "bg-white border-premium-border"}`}
          >
            <p className="text-xs font-bold text-ink-soft">{m.month}</p>
            <p className="text-sm font-bold text-ink mt-1">{fmt(m.revenue)}</p>
            <p className={`text-xs font-bold mt-0.5 ${m.index >= 1.1 ? "text-[#16a34a]" : m.index <= 0.9 ? "text-red-500" : "text-ink-soft"}`}>
              {m.index >= 1.0 ? "+" : ""}{Math.round((m.index - 1) * 100)}%
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

// ─── Evidence & Gaps Tab ──────────────────────────────────────────────────────

// The engine has always computed the provenance of every figure, the list of
// gates it could not evaluate, and the reason any given number is unavailable.
// None of it was rendered. A founder could not tell which figures they had
// told the system and which it had inferred, and had no way to see what it
// still needed - which means a missing number read as a zero and a modelled
// number read as a declared one.
//
// This tab is where that distinction becomes visible. It states what is known,
// what is assumed, and what is outstanding, and it never renders a gate as
// failed because the input for it was never supplied.
const ProvenanceTable = ({ title, rows }: { title: string; rows: any[] | null | undefined }) => {
  if (!rows || rows.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-premium-border p-5">
        <h3 className="font-bold text-ink text-sm mb-2">{title}</h3>
        <p className="text-ink-soft text-sm">
          No provenance was recorded. This means the source of these figures
          could not be established — treat them as unverified rather than as
          confirmed.
        </p>
      </div>
    );
  }
  // An unknown source is itself a finding, not a formatting problem.
  const isKnown = (s: unknown) =>
    s === "DECLARED" || s === "OBSERVED" || s === "DERIVED" || s === "DEFAULTED";
  return (
    <div className="bg-white rounded-2xl border border-premium-border p-5">
      <h3 className="font-bold text-ink text-sm mb-3">{title}</h3>
      <div className="space-y-1.5">
        {rows.map((r, i) => (
          <div key={i} className="flex items-center justify-between gap-3 text-sm">
            <span className="text-ink-soft font-mono text-xs truncate">{r.name}</span>
            <span className="flex items-center gap-2 shrink-0">
              <span className="text-ink font-semibold max-w-[9rem] truncate">
                {typeof r.value === "number" ? fmt(r.value) : String(r.value ?? NA)}
              </span>
              <span
                className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                  !isKnown(r.source)
                    ? "bg-amber-50 text-amber-700"
                    : r.source === "OBSERVED"
                      ? "bg-[#f0fdf4] text-[#16a34a]"
                      : r.source === "DECLARED"
                        ? "bg-blue-50 text-blue-700"
                        : "bg-slate-50 text-ink-soft"
                }`}
              >
                {r.source ?? "UNKNOWN"}
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

const EvidenceTab = ({ data }: { data: FinanceResponse }) => {
  const unknowns = data.assessability_unknowns ?? [];
  const failures = data.viability_reasons ?? [];
  const confidence = data.financial_confidence as any;
  const status = data.financial_status as any;

  // Unavailable figures carry a reason from the engine. Rendering them together
  // is the point: a null with a stated cause is information, a null without one
  // looks like a bug.
  const unavailable: { label: string; note: string | null | undefined }[] = [
    { label: "DSCR (debt service coverage)", note: data.dscr_status },
    { label: "Profit after tax", note: data.tax_status },
    { label: "Payback period", note: data.payback_status ?? data.payback_undetermined_reason },
    { label: "Contribution per unit", note: data.unit_metrics_note },
  ].filter((r) => r.note && r.note !== "MODELLED" && r.note !== "ACHIEVED");

  return (
    <div className="animate-in fade-in duration-300 space-y-6">

      {/* What the system knows, and how well it knows it */}
      <div className="bg-gradient-to-br from-[#f0fdf4] to-white rounded-2xl border border-[#bbf7d0] p-6">
        <div className="flex items-start gap-3">
          <Info className="text-[#16a34a] mt-0.5 shrink-0" size={20} />
          <div className="flex-1">
            <h2 className="text-lg font-bold text-forest-deep">How much of this is evidence</h2>
            <p className="text-sm text-ink-soft mt-1">
              Confidence describes the evidence behind these numbers. It is
              independent of performance: a well-evidenced business that loses
              money is high confidence, and a profitable projection built on
              assumptions is low confidence.
            </p>
            <div className="flex flex-wrap gap-3 mt-4">
              <div className="bg-white rounded-xl border border-premium-border px-4 py-2">
                <p className="text-[10px] uppercase font-bold text-ink-soft">Confidence</p>
                <p className="font-bold text-ink">{confidence?.band ?? NA}</p>
              </div>
              {confidence?.score != null && (
                <div className="bg-white rounded-xl border border-premium-border px-4 py-2">
                  <p className="text-[10px] uppercase font-bold text-ink-soft">Score</p>
                  <p className="font-bold text-ink">{confidence.score}</p>
                </div>
              )}
              <div className="bg-white rounded-xl border border-premium-border px-4 py-2">
                <p className="text-[10px] uppercase font-bold text-ink-soft">Verdict</p>
                <p className="font-bold text-ink">{status?.value ?? NA}</p>
              </div>
            </div>
            {Array.isArray(confidence?.basis) && confidence.basis.length > 0 && (
              <ul className="mt-4 space-y-1.5">
                {confidence.basis.map((b: string, i: number) => (
                  <li key={i} className="text-sm text-ink-soft flex items-start gap-2">
                    <span className="text-ink-soft">•</span>{b}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Gaps. A gate with no input is unknown, not failed. */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-2xl border border-amber-200 p-5">
          <div className="flex items-center gap-2 mb-3">
            <HelpCircle className="text-amber-500" size={18} />
            <h3 className="font-bold text-ink text-sm">What is still unknown</h3>
          </div>
          {unknowns.length === 0 ? (
            <p className="text-sm text-ink-soft">
              Every gate could be evaluated. Nothing material is outstanding.
            </p>
          ) : (
            <>
              <p className="text-sm text-ink-soft mb-3">
                These could not be assessed. An unassessable gate is not a
                failed one — no conclusion has been drawn about them.
              </p>
              <ul className="space-y-1.5">
                {unknowns.map((u, i) => (
                  <li key={i} className="text-sm text-ink flex items-start gap-2">
                    <span className="text-amber-500 font-bold">?</span>{u}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <div className="bg-white rounded-2xl border border-red-200 p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="text-red-500" size={18} />
            <h3 className="font-bold text-ink text-sm">What failed</h3>
          </div>
          {failures.length === 0 ? (
            <p className="text-sm text-ink-soft">No gate failed on declared data.</p>
          ) : (
            <ul className="space-y-1.5">
              {failures.map((f, i) => (
                <li key={i} className="text-sm text-ink flex items-start gap-2">
                  <span className="text-red-500 font-bold">×</span>{f}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Figures that are unavailable, and the reason for each */}
      {unavailable.length > 0 && (
        <div className="bg-white rounded-2xl border border-premium-border p-5">
          <h3 className="font-bold text-ink text-sm mb-1">Figures shown as unavailable</h3>
          <p className="text-sm text-ink-soft mb-3">
            Each of these is genuinely absent, not zero. The reason is the
            engine&apos;s, not a display convention.
          </p>
          <div className="space-y-2">
            {unavailable.map((r) => (
              <div key={r.label} className="flex items-start justify-between gap-4 text-sm border-b border-premium-border pb-2 last:border-0">
                <span className="text-ink font-medium">{r.label}</span>
                <span className="text-ink-soft text-right text-xs">{r.note}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Where the numbers came from */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ProvenanceTable title="Your figures — where each came from" rows={data.input_provenance} />
        <ProvenanceTable title="Engine assumptions" rows={data.assumptions_provenance} />
      </div>

      <p className="text-xs text-ink-soft leading-relaxed">
        <strong className="text-ink-soft">DECLARED</strong> you supplied it.
        {" "}<strong className="text-ink-soft">OBSERVED</strong> it came from a
        recorded source. {" "}<strong className="text-ink-soft">DERIVED</strong>{" "}
        it was computed from the above. {" "}
        <strong className="text-ink-soft">DEFAULTED</strong> the engine supplied
        it and you did not.
      </p>
    </div>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function FinancialsPage() {
  const { analysisResult } = useStore();
  const [activeTab, setActiveTab] = useState("overview");

  if (!analysisResult || !analysisResult.financials) {
    return (
      <div className="min-h-screen bg-[#fcfbf8] flex flex-col items-center justify-center p-8 text-center">
        <AlertTriangle className="text-red-500 mb-4" size={48} />
        <h2 className="text-xl font-bold text-ink mb-2">Financial Analysis Not Found</h2>
        <p className="text-ink-soft mb-6">No session data found. Please complete onboarding first.</p>
        <a href="/" className="px-5 py-2.5 bg-forest text-white rounded-xl font-bold flex items-center gap-2">
          Start Over <ArrowRight size={16} />
        </a>
      </div>
    );
  }

  // Extract financial properties directly from the unified analysis response
  // We need to shape it to match what the UI expects, since UI expects FinanceResponse format
  const { financials } = analysisResult;
  
  // Transform or provide fallbacks if unified response differs from legacy FinanceResponse
  //
  // Removed: `interest_rate_pct || 10`, `tenure_months || 60`, and a
  // `break_even_units ... : 500` fallback. Each of those displayed an invented
  // number to a user making a borrowing decision, and each was load-bearing -
  // the interest rate and tenure feed the loan summary, the amortization table
  // and `totalPayable`, all of which were therefore computed on a 10%/60-month
  // loan that the user never declared and the engine never issued.
  //
  // The break-even fallback was the worst of the three: it derived units by
  // dividing monthly revenue by 100, i.e. assuming a ₹100 unit price, and then
  // substituted a flat 500 when that was unavailable. The components below
  // already render a null break-even as "N/A", so the honest value costs
  // nothing.
  //
  // Everything below is READ from the engine's result. This block used to
  // reconstruct the P&L and the working-capital position from a gross margin
  // percentage and a monthly opex figure, and each reconstruction was a second
  // opinion about numbers the engine had already computed exactly:
  //
  //   * COGS was `revenue x (1 - gross_margin/100)`, so it was the gross margin
  //     run backwards through a rounded percentage. Revenue, COGS and gross
  //     profit on screen did not add up.
  //   * EBIT was `net_profit + emi`, which treats an EMI (principal AND
  //     interest) as if it were interest, and so overstated EBIT by the whole
  //     principal repayment.
  //   * Tax was a literal 0, shown next to a Net Profit figure as though tax had
  //     been computed and found to be nil.
  //   * Net margin was a division with `|| 0`, which turns "we could not
  //     compute it" into "0%".
  //   * Daily and weekly cash were opex/30 and opex/4, with inventory,
  //     receivables and payables all shown as 0 and a buffer invented as
  //     `opex x 2`.
  //
  // None of those agree with the model, and the ones a user would act on -
  // break-even, margin, cash float - are exactly the ones that were wrong.
  const canonical = financials as any;

  // Null means not computed. It is never coerced to 0, because a zero here reads
  // as a measured answer to a question nobody answered.
  const num = (v: unknown): number | null =>
    typeof v === "number" && Number.isFinite(v) ? v : null;

  const monthlyRevenue = num(canonical.monthly_revenue) ?? num(canonical.monthly_revenue_target);
  const engineWc = canonical.working_capital ?? {};

  const data: any = {
    project_cost: financials.project_cost,
    loan_amount: financials.loan_amount,
    beneficiary_contribution: financials.user_capital,
    emi: financials.emi,
    rate: financials.interest_rate_pct ?? null,
    tenure_months: financials.tenure_months ?? null,
    moratorium_months: financials.moratorium_months ?? 0,
    monthly_revenue: monthlyRevenue,
    monthly_opex: financials.monthly_opex,
    net_profit: financials.net_profit,
    roi: financials.roi_pct,
    dscr: financials.dscr,
    dscr_status: financials.dscr_status ?? null,
    break_even_units: financials.break_even_units ?? null,
    // The engine's declared working days, used to express break-even per day.
    // The 26 that used to be hardcoded here assumed a particular month and
    // ignored whatever the plan actually declared.
    operating_days_per_month: canonical.operating_days_per_month ?? null,
    margin_of_safety_pct: num(canonical.margin_of_safety_pct),
    total_repayment: num(canonical.total_repayment),
    total_interest_paid: num(canonical.total_interest_paid),
    loan_schedule: canonical.loan_schedule || [],
    scheme: typeof financials.scheme === "string"
      ? {
          scheme_name: financials.scheme,
          // Was: "Matched government loan scheme based on project cost and
          // eligibility." The engine does not decide eligibility. It routes a
          // project cost to a scheme band and states that no document has been
          // checked, so a description asserting a match overstates what happened.
          explanation:
            "Routed to this scheme by project-cost band. Eligibility has not been assessed and no document has been checked; confirm with the agency.",
          source_url: "",
        }
      : (financials.scheme || { scheme_name: "Standard Business Loan", explanation: "General SME financing based on typical market rates.", source_url: "" }),
    cashflow_projection: financials.cashflow_projection || [],
    pnl_statement: {
      revenue: monthlyRevenue,
      cogs: num(canonical.monthly_cogs) ?? num(canonical.monthly_variable_cost),
      gross_profit: num(canonical.monthly_gross_profit),
      operating_expenses: num(canonical.monthly_opex),
      ebitda: num(canonical.monthly_ebitda),
      depreciation: num(canonical.monthly_depreciation),
      ebit: num(canonical.monthly_ebit),
      interest: num(canonical.monthly_interest),
      tax: num(canonical.monthly_tax),
      tax_status: canonical.tax_status ?? null,
      net_profit: num(financials.net_profit),
      gross_margin_pct: num(financials.gross_margin_pct),
      net_margin_pct: num(canonical.net_margin_pct),
    },
    // The engine's own working-capital block, including the cycle days it used.
    // inventory_requirement/receivables/payables are no longer hardcoded to 0,
    // and the buffer is the engine's rather than `opex x 2`.
    working_capital: {
      monthly_working_capital: num(engineWc.monthly_working_capital) ?? num(canonical.net_working_capital),
      net_working_capital: num(engineWc.net_working_capital) ?? num(canonical.net_working_capital),
      daily_cash_needed: num(engineWc.daily_cash_needed),
      weekly_cash_needed: num(engineWc.weekly_cash_needed),
      inventory_requirement: num(engineWc.inventory_requirement),
      inventory_days: num(engineWc.inventory_days),
      receivables: num(engineWc.receivables),
      receivable_days: num(engineWc.receivable_days),
      payables: num(engineWc.payables),
      payable_days: num(engineWc.payable_days),
      recommended_buffer: num(engineWc.recommended_buffer),
    },
    revenue_scenarios: financials.revenue_scenarios || null,
    seasonal_revenue: financials.seasonal_revenue || [],
    payback_period: financials.payback_period || null,
    // The engine's verdict and its working, passed through for display.
    financial_status: canonical.financial_status ?? null,
    decision_gates: canonical.decision_gates || [],
    financial_confidence: canonical.financial_confidence ?? null,
    monthly_forecast: canonical.monthly_forecast || [],
    stress_scenarios: canonical.stress_scenarios || {},
    validation_issues: canonical.validation_issues || [],
    explainability: canonical.explainability || null,
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 py-6 pb-24 bg-[#fcfbf8] min-h-screen">
      {/* Page Header */}
      <div className="mb-8 border-b border-premium-border pb-6">
        <h1 className="text-[32px] font-bold text-forest-deep tracking-tight mb-1">Financial Analysis</h1>
        <p className="text-ink-soft font-medium">
          Complete financial model for your business — projections, Monthly Installment, P&L, and more.
        </p>
      </div>

      {/* Tab Bar — wraps to two rows on smaller screens */}
      <div className="flex flex-wrap gap-1 border-b border-premium-border mb-8 pb-0">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-bold whitespace-nowrap rounded-t-lg border-b-2 transition-all mb-[-1px] ${
              activeTab === key
                ? "border-[#ea580c] text-[#ea580c] bg-[#fff5f0]"
                : "border-transparent text-ink-soft hover:text-ink hover:bg-black/5"
            }`}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === "overview"  && <OverviewTab data={data} />}
        {data.financial_status?.value === "INSUFFICIENT_INPUT" && activeTab !== "overview" && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-10 mt-6 text-center text-red-600 animate-in fade-in">
            <AlertTriangle size={48} className="mx-auto mb-4 opacity-80" />
            <h3 className="text-lg font-bold mb-2">Detailed Projections Blocked</h3>
            <p>Please return to the Overview tab and provide Project Cost and Monthly Revenue to unlock the model.</p>
          </div>
        )}
        {data.financial_status?.value !== "INSUFFICIENT_INPUT" && (
          <>
            {activeTab === "cashflow"  && <CashFlowTab data={data} />}
            {activeTab === "pnl"       && <PnlTab data={data} />}
            {activeTab === "breakeven" && <BreakEvenTab data={data} />}
            {activeTab === "loan"      && <LoanTab data={data} />}
            {activeTab === "working"   && <WorkingCapitalTab data={data} />}
            {activeTab === "scenarios" && <ScenariosTab data={data} />}
            {activeTab === "seasonal"  && <SeasonalTab data={data} />}
            {activeTab === "evidence"  && <EvidenceTab data={data} />}
          </>
        )}
      </div>
    </div>
  );
}
