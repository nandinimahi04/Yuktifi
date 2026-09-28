"use client";

import { useEffect, useState } from "react";
import { api, AdvisoryResponse } from "@/lib/api-client";
import { useStore } from "@/lib/store";
import { Loader2, ShieldCheck, AlertTriangle, XCircle, Database, MapPin } from "lucide-react";

const money = (n:any) => `₹${Number(n||0).toLocaleString("en-IN", {maximumFractionDigits:0})}`;

export default function AdvisoryPage() {
  const store = useStore();
  const [templates, setTemplates] = useState<any[]>([]);
  const [businessId, setBusinessId] = useState(store.categoryId || "dairy");
  const [location, setLocation] = useState(store.locationName || "Solapur, Maharashtra");
  const [margin, setMargin] = useState(Number(store.marginCapital || 100000));
  const [units, setUnits] = useState(727);
  const [price, setPrice] = useState(55);
  const [variable, setVariable] = useState(20);
  const [fixed, setFixed] = useState(15000);
  const [rate, setRate] = useState(12);
  const [tenure, setTenure] = useState(60);
  const [result, setResult] = useState<AdvisoryResponse|null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  /*
    Every financial input on this page arrives pre-filled: `units: 727`,
    `price: 55`, `variable: 20`, `fixed: 15000`, `rate: 12`, `tenure: 60`,
    `margin: 100000`, `businessId: "dairy"`, `location: "Solapur, Maharashtra"`.
    Nine numbers and two identities, none of them entered by the user.

    Two things followed from that, and both were wrong:

    - The request sent `use_demo_assumptions: false`. That flag tells the backend
      these are the applicant's declared figures, so every downstream record -
      the evidence trail, the source manifest, the input-quality block - would
      carry eight invented numbers as verified declarations.
    - The page subtitle read "No hidden financial defaults", directly above a
      form made almost entirely of defaults. They were not hidden, but the
      sentence claimed the opposite of the truth in the one place a user might
      have looked for it.

    A pre-filled planner is a reasonable pattern and is kept. What changed is the
    claim: a field is an example until the user edits it, the flag now reflects
    that, and the result is labelled as an illustration for as long as any
    financial input is still an example. The verdict is the product's most
    consequential output, so it must not read as a finding about the user when
    it is arithmetic on a seed.
  */
  const EXAMPLE_FIELDS = ["businessId","location","margin","units","price","variable","fixed","rate","tenure"] as const;
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const markTouched = (f: string) => setTouched(t => ({ ...t, [f]: true }));
  const examplesInUse = EXAMPLE_FIELDS.filter(f => !touched[f]);
  const inputsAreExample = examplesInUse.length > 0;

  useEffect(()=>{ api.getBusinessTemplates().then(r=>setTemplates(r.templates)).catch(()=>{}); },[]);
  useEffect(()=>{
    const t=templates.find(x=>x.id===businessId);
    if(t && !result){ setUnits(t.default_monthly_units ?? units); setPrice(t.default_price_per_unit ?? price); setVariable(t.default_variable_cost_per_unit ?? variable); setFixed(t.fixed_cost_monthly ?? fixed); }
  },[businessId, templates]);

  async function run() {
    setLoading(true); setError(""); setResult(null);
    try {
      const r=await api.runAdvisory({
        business_id: businessId,
        location: { query: location },
        promoter_margin: margin,
        monthly_units: units,
        price_per_unit: price,
        variable_cost_per_unit: variable,
        fixed_cost_monthly: fixed,
        annual_rate_pct: rate,
        tenure_months: tenure,
        use_demo_assumptions: inputsAreExample,
        profile: { social_category: "" }
      });
      setResult(r);
    } catch(e:any) { setError(e?.message || "Unable to run advisory"); }
    finally { setLoading(false); }
  }

  return <main className="max-w-6xl mx-auto p-5 md:p-10 text-ink">
    <div className="mb-8">
      <div className="flex items-center gap-2 text-sm text-ink-soft"><Database size={16}/> Evidence-grounded advisory</div>
      <h1 className="text-4xl font-bold mt-2">Business Feasibility Check</h1>
      <p className="text-ink-soft mt-2">Rules calculate. Evidence supports. AI explains. Every input below is shown, and nothing you did not enter is presented as yours.</p>
    </div>
    {inputsAreExample && (
      <div className="mb-5 flex items-start gap-3 bg-amber-50 border-2 border-amber-300 rounded-2xl p-4">
        <AlertTriangle size={18} className="text-amber-700 mt-0.5 shrink-0" />
        <div>
          <div className="text-sm font-bold text-ink">Example inputs — not your figures</div>
          <p className="text-xs text-ink-soft mt-1">
            {examplesInUse.length} of {EXAMPLE_FIELDS.length} inputs are still the
            seeded examples. The result below is an illustration of how the
            calculation behaves, not a finding about your business. Replace a
            field to mark it as yours.
          </p>
        </div>
      </div>
    )}
    <section className="bg-white border border-premium-border rounded-3xl p-6 grid md:grid-cols-2 gap-5 shadow-card">
      <label>Business<select value={businessId} onChange={e=>{setBusinessId(e.target.value); markTouched("businessId");}} className="field">{templates.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
      <label>Location<input value={location} onChange={e=>{setLocation(e.target.value); markTouched("location");}} className="field" placeholder="Village, Taluka, District, State"/></label>
      <label>Own capital / promoter margin<input type="number" value={margin} onChange={e=>{setMargin(+e.target.value); markTouched("margin");}} className="field"/></label>
      <label>Monthly units<input type="number" value={units} onChange={e=>{setUnits(+e.target.value); markTouched("units");}} className="field"/></label>
      <label>Price per unit<input type="number" value={price} onChange={e=>{setPrice(+e.target.value); markTouched("price");}} className="field"/></label>
      <label>Variable cost per unit<input type="number" value={variable} onChange={e=>{setVariable(+e.target.value); markTouched("variable");}} className="field"/></label>
      <label>Fixed monthly cost<input type="number" value={fixed} onChange={e=>{setFixed(+e.target.value); markTouched("fixed");}} className="field"/></label>
      <label>Interest rate %<input type="number" value={rate} onChange={e=>{setRate(+e.target.value); markTouched("rate");}} className="field"/></label>
      <label>Tenure (months)<input type="number" value={tenure} onChange={e=>{setTenure(+e.target.value); markTouched("tenure");}} className="field"/></label>
      <div className="md:col-span-2 flex justify-end"><button onClick={run} disabled={loading} className="px-7 py-3 rounded-xl bg-forest text-white font-bold flex items-center gap-2">{loading&&<Loader2 className="animate-spin" size={18}/>} Run YUKTIFI</button></div>
    </section>
    {error && <div className="mt-5 p-4 rounded-xl bg-red-50 text-red-700 border border-red-200">{error}</div>}
    {result && <section className="mt-8 space-y-5">
      {inputsAreExample && (
        <div className="flex items-start gap-3 bg-amber-50 border-2 border-amber-300 rounded-2xl p-4">
          <AlertTriangle size={18} className="text-amber-700 mt-0.5 shrink-0" />
          <p className="text-sm text-ink">
            <strong>Illustration, not a verdict on your business.</strong> This
            result was computed from {examplesInUse.length} seeded example
            input{examplesInUse.length === 1 ? "" : "s"} you have not replaced.
            The decision below describes those numbers, not your situation.
          </p>
        </div>
      )}
      <div className={`rounded-3xl p-7 border ${result.decision.decision==='GO'?'bg-green-50 border-green-200':result.decision.decision==='CONDITIONAL'?'bg-amber-50 border-amber-200':'bg-red-50 border-red-200'}`}>
        <div className="flex items-center gap-3"><MapPin size={20}/><span>{result.location.village || result.location.query || location}</span></div>
        <div className="flex items-center gap-4 mt-5"><DecisionIcon decision={result.decision.decision}/><div><div className="text-sm font-bold uppercase tracking-widest">Decision</div><div className="text-4xl font-black">{result.decision.decision}</div></div></div>
        <div className="grid md:grid-cols-4 gap-4 mt-7"><Metric title="Project cost" value={money(result.financial.project_cost)}/><Metric title="Loan" value={money(result.financial.loan_amount)}/><Metric title="EMI" value={money(result.financial.monthly_emi)}/><Metric title="DSCR" value={result.financial.dscr}/></div>
      </div>
      <div className="grid md:grid-cols-2 gap-5">
        <Card title="Market evidence"><p>Catchment: {result.market.catchment_km} km</p><p>Population anchor: {result.market.base_population ?? "Unavailable"}</p><p>Households: {result.market.base_households ?? "Unavailable"}</p><p>Modeled demand: {result.market.estimated_units_monthly ?? "Unavailable"} {result.business.sales_unit}/month</p><p>Confidence: {result.market.confidence}</p></Card>
        <Card title="Competition"><p>{result.competition.interpretation}</p><p>Mapped businesses: {result.competition.mapped_count}</p><p>Density: {result.competition.density_per_sq_km}/km²</p><p className="text-sm text-ink-soft mt-2">OSM mapping is not a complete census of businesses.</p></Card>
      </div>
      <Card title="Why this decision"><ul className="list-disc pl-5 space-y-2">{result.decision.why.map((x:string,i:number)=><li key={i}>{x}</li>)}</ul><h3 className="font-bold mt-5">What would change it</h3><ul className="list-disc pl-5 space-y-2 mt-2">{result.decision.what_would_change_it.map((x:string,i:number)=><li key={i}>{x}</li>)}</ul></Card>
      <Card title="Stress tests"><div className="grid md:grid-cols-3 gap-3">{result.risk.scenarios.map((s:any)=><div key={s.scenario} className="p-4 rounded-xl border border-premium-border"><div className="font-bold">{s.scenario}</div><div className="text-2xl font-black mt-1">{s.dscr}</div><div className="text-xs text-ink-soft">DSCR</div></div>)}</div></Card>
      <Card title="Evidence & limitations"><div className="space-y-3">{result.evidence.map((e:any,i:number)=><div key={i} className="p-3 rounded-xl bg-cream"><div className="font-bold">{e.metric}</div><div className="text-sm">{e.value ?? "Unavailable"} · {e.source}</div></div>)}</div><ul className="list-disc pl-5 mt-4 text-sm text-ink-soft">{result.limitations.map((x:string,i:number)=><li key={i}>{x}</li>)}</ul></Card>
    </section>}
    <style jsx>{`.field{display:block;width:100%;margin-top:8px;padding:11px 13px;border:1px solid #ddd;border-radius:12px;background:#fff}.field:focus{outline:2px solid #2f6b4f}`}</style>
  </main>
}
function Metric({title,value}:{title:string,value:any}){return <div className="bg-white/70 rounded-2xl p-4"><div className="text-xs uppercase tracking-widest text-ink-soft">{title}</div><div className="text-2xl font-black mt-1">{value}</div></div>}
function Card({title,children}:{title:string,children:any}){return <div className="bg-white rounded-3xl border border-premium-border p-6 shadow-card"><h2 className="text-xl font-bold mb-4">{title}</h2>{children}</div>}
function DecisionIcon({decision}:{decision:string}){return decision==='GO'?<ShieldCheck className="text-green-700" size={40}/>:decision==='CONDITIONAL'?<AlertTriangle className="text-amber-700" size={40}/>:<XCircle className="text-red-700" size={40}/>}
