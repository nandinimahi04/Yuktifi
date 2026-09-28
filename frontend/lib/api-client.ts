/**
 * API client to communicate with the FastAPI backend.
 * - Centralized base URL from environment variable
 * - AbortController-based timeouts (15s standard, 60s for AI)
 * - Structured error handling
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STANDARD_TIMEOUT_MS = 15000;
const AI_TIMEOUT_MS = 120000; // Increased to 120s to allow multiple slow third-party API queries

class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status?: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Whether the data behind the current screen is live.
 *
 * The backend sets `X-YuktiFi-Data-Mode: demo` on every response while
 * `DEMO_MODE` is on, which switches off outbound network in the provider
 * clients. Nothing was reading it, so a demo run and a live run looked
 * identical: the same prices, the same competitor counts, the same
 * recommendation, with nothing on screen saying the numbers had not been looked
 * up. A figure that is not live has to be labelled as not live.
 *
 * `null` until the first response arrives, and if a client is served from a
 * cache or a proxy that strips the header. It is deliberately not initialised
 * to `"live"` - the safe reading of an absent label is "unknown", not "live".
 */
let dataMode: "live" | "demo" | null = null;
const dataModeListeners = new Set<(m: "live" | "demo" | null) => void>();

export const getDataMode = () => dataMode;

export const onDataModeChange = (fn: (m: "live" | "demo" | null) => void) => {
  dataModeListeners.add(fn);
  fn(dataMode);
  return () => {
    dataModeListeners.delete(fn);
  };
};

async function fetchWithTimeout<T>(
  endpoint: string,
  options: RequestInit,
  timeoutMs: number,
  externalSignal?: AbortSignal
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  // If the caller passes their own signal (e.g. from useEffect cleanup),
  // wire it up so aborting that signal also aborts this fetch.
  if (externalSignal) {
    if (externalSignal.aborted) {
      clearTimeout(timer);
      throw new ApiError("REQUEST_CANCELLED", "Request was cancelled.");
    }
    externalSignal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  try {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      signal: controller.signal,
    });

    // Read the disclosure on every response. An absent header leaves the mode
    // unknown rather than assuming live.
    const reported = res.headers?.get?.("X-YuktiFi-Data-Mode");
    if (reported === "live" || reported === "demo") {
      if (reported !== dataMode) {
        dataMode = reported;
        dataModeListeners.forEach((fn) => fn(dataMode));
      }
    }

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new ApiError(
        errorData.code || `HTTP_${res.status}`,
        errorData.detail || `Request failed with status ${res.status}`,
        res.status
      );
    }

    return res.json();
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      // Distinguish between timeout and user-initiated cancellation
      const reason = externalSignal?.aborted ? "REQUEST_CANCELLED" : "REQUEST_TIMEOUT";
      const msg = reason === "REQUEST_CANCELLED"
        ? "Request was cancelled."
        : "The request timed out. Please try again.";
      throw new ApiError(reason, msg);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export { ApiError };

export class ApiClient {
  static async post<T>(endpoint: string, body: unknown, timeoutMs = STANDARD_TIMEOUT_MS, signal?: AbortSignal): Promise<T> {
    return fetchWithTimeout<T>(
      endpoint,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
      timeoutMs,
      signal
    );
  }

  static async get<T>(endpoint: string, timeoutMs = STANDARD_TIMEOUT_MS, signal?: AbortSignal): Promise<T> {
    return fetchWithTimeout<T>(
      endpoint,
      { method: "GET" },
      timeoutMs,
      signal
    );
  }
}

// ─── Typed API shapes ────────────────────────────────────────────────────────

export interface ProfileResponse {
  user_id: string;
  location_id: string;
  location_name: string;
  state: string;
  lat: number;
  lng: number;
  data_richness: string;
}

export interface RankResponse {
  session_id: string;
  scheme_matched: boolean;
  scheme_name?: string;
  rankings: Array<{
    category_id: string;
    category_name: string;
    yukti_score: number;
    verdict: string;
    confidence: string;
    dscr?: number;
    roi?: number;
    emi?: number;
    net_profit?: number;
    highlights: string[];
    note: string;
  }>;
}

export interface MarketResponse {
  category_name: string;
  location_id: string;
  overall_confidence: string;
  market_reach: { value: { consumer_base: number } | null; provenance: Record<string, string> };
  competitors: { value: { count: number; records: Array<{ name: string; latitude: number; longitude: number }> } | null; provenance: Record<string, string> };
  opportunity_gaps: { value: { assessment: string } | null; provenance: Record<string, string> };
  pricing: { value: { low: number; high: number; unit: string } | null; provenance: Record<string, string> };
}

export interface CashflowMonth {
  month: string;
  month_num: number;
  revenue: number;
  expenses: number;
  emi_payment: number;
  net_cash: number;
  cumulative: number;
}

// The engine returns null for anything it could not compute rather than 0, and
// these types reflect that. Declaring every field as a plain `number` is what
// allowed a null to reach JSX arithmetic (`null >= 10`, `null * 12`) and render
// as a confident zero.
export interface PnlStatement {
  revenue: number | null;
  cogs: number | null;
  gross_profit: number | null;
  gross_margin_pct: number | null;
  operating_expenses: number | null;
  ebitda: number | null;
  depreciation: number | null;
  ebit: number | null;
  interest: number | null;
  tax: number | null;
  // e.g. "NOT_MODELED" or "MODELLED": distinguishes a tax of zero from a tax
  // that was never calculated.
  tax_status: string | null;
  net_profit: number | null;
  net_margin_pct: number | null;
}

export interface WorkingCapital {
  daily_cash_needed: number | null;
  weekly_cash_needed: number | null;
  monthly_working_capital: number | null;
  net_working_capital: number | null;
  inventory_requirement: number | null;
  receivables: number | null;
  payables: number | null;
  recommended_buffer: number | null;
  receivable_days: number | null;
  payable_days: number | null;
  inventory_days: number | null;
}

export interface RevenueScenario {
  monthly_revenue: number;
  monthly_opex: number;
  monthly_net_profit: number;
  annual_net_profit: number;
  roi_pct: number;
  payback_months: number | null;
}

export interface PaybackPeriod {
  payback_months: number | null;
  payback_achieved: boolean;
  total_investment: number;
  note: string;
}

export interface SeasonalMonth {
  month: string;
  revenue: number;
  index: number;
}

export interface LoanScheduleMonth {
  month: number;
  opening_balance: number;
  interest: number;
  principal_repaid: number;
  payment: number;
  closing_balance: number;
}

export interface FinanceResponse {
  project_cost: number;
  loan_amount: number;
  beneficiary_contribution: number;
  scheme: Record<string, unknown>;
  emi: number;
  rate: number;
  tenure_months: number;
  moratorium_months: number;
  monthly_revenue: number;
  monthly_opex: number;
  net_profit: number;
  dscr: number | null;
  break_even_units: number | null;
  roi: number;
  roi_on_total_project_pct: number;
  roi_on_owner_equity_pct: number;
  capital_turnover_ratio: number | null;
  revenue_source: string | null;
  cost_confidence: string;
  // Extended
  cashflow_projection: CashflowMonth[];
  loan_schedule: LoanScheduleMonth[];
  other_funding: number;
  financing_gap: number;
  financing_reconciled: boolean;
  viability: string | null;
  viability_reasons: string[];
  pnl_statement: PnlStatement | null;
  working_capital: WorkingCapital | null;
  revenue_scenarios: { pessimistic: RevenueScenario; realistic: RevenueScenario; optimistic: RevenueScenario };
  seasonal_revenue: SeasonalMonth[];
  payback_period: PaybackPeriod | null;
  // Canonical engine results, consumed directly rather than recomputed on the
  // client. See run_financial_engine() in backend/app/engines/financial_engine.py
  dscr_status: string | null;
  // Declared working days per month. Null when the plan never declared them,
  // which is why a per-day break-even may legitimately be unavailable.
  operating_days_per_month: number | null;
  // Revenue above break-even, as a percentage. Null when there is no positive
  // revenue to measure the headroom against.
  margin_of_safety_pct: number | null;
  // Totals taken from the engine's own amortisation schedule, so the headline
  // figures always tie to the schedule printed beneath them.
  total_repayment: number | null;
  total_interest_paid: number | null;
  monthly_gross_profit: number | null;
  monthly_cogs: number | null;
  monthly_ebitda: number | null;
  monthly_depreciation: number | null;
  monthly_interest: number | null;
  monthly_tax: number | null;
  tax_status: string | null;
  // Contribution per unit, only present when genuine per-unit inputs (price and
  // variable cost per unit) were declared - not when a single aggregate sales
  // line was reported.
  contribution_per_unit: number | null;
  financial_status: { value: string; label?: string; reasons?: string[] } | null;
  decision_gates: unknown[];
  financial_confidence: unknown;
  monthly_forecast: unknown[];
  stress_scenarios: Record<string, unknown>;
  validation_issues: unknown[];
  explainability: unknown;

  // ── Evidence and gaps ─────────────────────────────────────────────────────
  // The engine already produced all of this; nothing on the page was reading
  // it, so the provenance of every figure and the list of what is still
  // missing were computed server-side and then discarded.

  /** Where each figure came from: declared by the user, observed in the
   *  dataset, derived from those, or defaulted. This is what separates "you
   *  told us" from "we worked it out". */
  input_provenance: ProvenanceEntry[] | null;
  /** The same, for the engine's own assumptions. */
  assumptions_provenance: ProvenanceEntry[] | null;
  /** Gates that could not be evaluated because an input was never declared.
   *  This is the honest form of "we do not know" - not a failure. */
  assessability_unknowns: string[] | null;
  /** The thresholds each gate was measured against. */
  gate_benchmarks: GateBenchmarks | null;
  /** Why a per-unit figure is unavailable, in the engine's own words. */
  unit_metrics_note: string | null;
  /** Whether payback was reached, and why not if it was not. Distinct from a
   *  payback figure of null, which means "not computable". */
  payback_status: string | null;
  payback_undetermined_reason?: string | null;
}

export interface ProvenanceEntry {
  name: string;
  value: unknown;
  source: string;
}

export interface GateBenchmarks {
  min_dscr?: number;
  min_contribution_margin_pct?: number;
  min_ebitda_margin_pct?: number;
  min_roi_on_project_pct?: number;
  max_payback_months?: number;
  min_cash_buffer_months?: number;
  require_financing_reconciled?: boolean;
  min_cash_balance?: number;
}

export interface RecommendResponse {
  session_id: string;
  yukti_score: number;
  raw_score: number;
  confidence_multiplier: number;
  verdict: string;
  dimension_scores: {
    financial_viability: number;
    repayment_capacity: number;
    market_opportunity: number;
    capital_efficiency: number;
    risk_exposure: number;
  };
  dscr: number | null;
  roi: number;
  next_steps: string[];
  confidence: string;
}

export interface SimulateResponse {
  emi: number;
  dscr: number | null;
  dscr_status: string;
  break_even_units: number | null;
  verdict: string;
  net_profit: number;
  simulated_roi: number;
  // Tri-state: true covers the debt service, false does not, null means there
  // was no debt service to cover. Reading this as a plain boolean reported every
  // debtless business as failing the stress test.
  survives_stress: boolean | null;
  survives_stress_applicable: boolean;
  // Which levers moved, and what each was before and after. A caller that
  // changed its capital or its tenor had no way to confirm the request had been
  // honoured without this.
  adjustments: Record<string, number>;
  applied_adjustments: AppliedAdjustment[];
}

export interface AppliedAdjustment {
  lever: string;
  previous: number;
  applied: number;
  change: number;
}

/** The original two-shock request, still accepted. */
export interface WhatIfShockRequest {
  session_id: string;
  revenue_delta_pct?: number;
  cost_delta_pct?: number;
  tenure_override_years?: number;
}

/**
 * The canonical levers. Percentages are percentage points, `units_multiplier`
 * is a factor. `revenue_delta_pct` remains a *volume* shock, not a price move.
 */
export interface WhatIfRequest extends WhatIfShockRequest {
  units_multiplier?: number;
  price_delta_pct?: number;
  variable_cost_delta_pct?: number;
  fixed_cost_delta_pct?: number;
  interest_rate_annual_pct?: number;
  tenure_months?: number;
  own_capital?: number;
  debt_amount?: number;
  other_funding?: number;
  tax_rate_pct?: number;
  operating_days_per_month?: number;
  annual_price_growth_pct?: number;
  working_capital_days_scale?: number;
}

export interface ExplainResponse {
  explanation: string;
  data_source: string;
}

export interface CopilotChatResponse {
  reply: string;
}

export interface CopilotExplainResponse {
  explanation: string;
}

export interface ReportResponse {
  session_id: string;
  html_content: string;
  generated_at: string;
}


export interface AdvisoryResponse {
  run_id: string;
  generated_at: string;
  engine_version: string;
  business: any;
  location: any;
  market: any;
  competition: any;
  financial: any;
  risk: any;
  schemes: any[];
  decision: any;
  evidence: any[];
  source_manifest: Record<string,string>;
  explanation: any;
  limitations: string[];
  input_quality: any;
}

export interface AnalysisResponse {
  status: string;
  data_available: boolean;
  matched_business: {
    matched_category_id: string;
    matched_subcategory: string;
    confidence: number;
    reason: string;
  };
  market: any;
  financials: any;
  scores: {
    overall: number;
    dimensions: any;
  };
  ai_insights: {
    rationale: string;
    recommendations: string[];
  };
}

export interface SchemeRule {
  scheme_name: string;
  rule_id: string;
  rule_version: string;
  effective_from: string | null;
  effective_date_state: string;
  source_url: string;
  implemented: boolean;
  evaluation_status: string;
  not_evaluated_reason: string | null;
  max_loan: number | null;
  min_loan: number | null;
  min_loan_verified: boolean;
  rate: number | null;
  rate_verified: boolean;
  tenure_years: number | null;
  tenure_verified: boolean;
  moratorium_months: number | null;
  rule_verification: {
    status: string;
    reviewed_on: string | null;
    note: string;
  };
}

export interface SchemeListResponse {
  schemes: SchemeRule[];
  verification: {
    status: string;
    note: string;
  };
  disclaimer: string;
}

// ─── API methods ─────────────────────────────────────────────────────────────

export const api = {
  /**
   * The disclosed scheme rule table. Fetched rather than hardcoded: the previous
   * version of the market-intelligence schemes tab asserted official loan caps
   * and subsidy percentages from JSX constants, which the backend had already
   * marked UNVERIFIED. Anything this tab shows about a scheme must come from
   * here, or it is not a term this build knows anything about.
   */
  getSchemes: (signal?: AbortSignal) =>
    ApiClient.get<SchemeListResponse>("/schemes", undefined, signal),

  generateAnalysis: (data: any, signal?: AbortSignal) =>
    ApiClient.post<AnalysisResponse>("/api/analysis/generate", data, AI_TIMEOUT_MS, signal),

  createProfile: (data: { name: string; location_input: string; language: string }, signal?: AbortSignal) =>
    ApiClient.post<ProfileResponse>("/profile", data, undefined, signal),

  rankOpportunities: (data: { session_id: string; location_id: string; margin_capital: number }, signal?: AbortSignal) =>
    ApiClient.post<RankResponse>("/rank-opportunities", data, undefined, signal),

  analyzeMarket: (data: { session_id: string; location_id: string; category_id: string; category_name?: string; budget?: number; experience?: string; idea_details?: string }, signal?: AbortSignal) =>
    ApiClient.post<MarketResponse>("/analyze-market", data, AI_TIMEOUT_MS, signal),

  calculateFinance: (data: { session_id: string; overrides?: any }, signal?: AbortSignal) =>
    ApiClient.post<FinanceResponse>("/calculate-finance", data, undefined, signal),

  getRecommendation: (data: { session_id: string }, signal?: AbortSignal) =>
    ApiClient.post<RecommendResponse>("/recommend", data, undefined, signal),

  simulate: (data: WhatIfRequest, signal?: AbortSignal) => ApiClient.post<SimulateResponse>("/simulate", data, undefined, signal),

  copilotChat: (data: { message: string; location_id: string; category_id: string; market_data?: any; financial_data?: any; score_data?: any }) =>
    ApiClient.post<CopilotChatResponse>("/api/copilot/chat", data, AI_TIMEOUT_MS),

  copilotExplain: (data: { question: string; location_id: string; category_id: string; market_data?: any; financial_data?: any; score_data?: any }) =>
    ApiClient.post<CopilotExplainResponse>("/api/copilot/explain", data, AI_TIMEOUT_MS),

  generateReport: (data: { session_id: string; format?: string }) =>
    ApiClient.post<ReportResponse>("/report", data, AI_TIMEOUT_MS),

  generateBusinessPlan: (data: { location: string; category: string; market_data?: any; financial_data?: any; risk_data?: any }) =>
    ApiClient.post<any>("/api/business-plan/generate", data, AI_TIMEOUT_MS),

  generateMarketingStrategy: (data: { location: string; category: string; market_data?: any; financial_data?: any; risk_data?: any }) =>
    ApiClient.post<any>("/api/marketing/generate", data, AI_TIMEOUT_MS),

  analyzeCompetitors: (data: { competitors: any[] }) =>
    ApiClient.post<any>("/api/competitor/analyze", data, AI_TIMEOUT_MS),

  simulateDynamic: (data: { month: number; cash_balance: number; active_events: string[]; decision: string; scenario_parameters: any }) =>
    ApiClient.post<any>("/api/simulate/dynamic", data, AI_TIMEOUT_MS),
  getFinancialAssumptions: (projectId: string, signal?: AbortSignal) =>
    ApiClient.get<any>(`/api/financials/${projectId}`, undefined, signal),

  recalculateFinancials: (data: { session_id: string; assumptions: any; changed_by?: string }, signal?: AbortSignal) =>
    ApiClient.post<any>("/api/financials/recalculate", data, undefined, signal),

  getOpportunityAnalytics: (params?: { project_id?: string; session_id?: string; category_id?: string; district?: string }, signal?: AbortSignal) => {
    const query = new URLSearchParams();
    if (params?.project_id) query.append("project_id", params.project_id);
    if (params?.session_id) query.append("session_id", params.session_id);
    if (params?.category_id) query.append("category_id", params.category_id);
    if (params?.district) query.append("district", params.district);
    const qs = query.toString();
    return ApiClient.get<any>(`/api/analytics/opportunity${qs ? `?${qs}` : ''}`, undefined, signal);
  },

  getBusinessTemplates: () => ApiClient.get<{templates:any[]}>("/api/v3/business-templates"),
  runAdvisory: (data: any, signal?: AbortSignal) => ApiClient.post<AdvisoryResponse>("/api/v3/advisory", data, STANDARD_TIMEOUT_MS, signal),
  getAdvisoryRun: (runId: string) => ApiClient.get<AdvisoryResponse>(`/api/v3/advisory/${runId}`),
  listAdvisoryRuns: (limit = 20) => ApiClient.get<{runs:any[]}>(`/api/v3/advisory-runs?limit=${limit}`),
};
