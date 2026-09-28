"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "@/routing";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useStore } from "@/lib/store";
import { ArrowRight } from "lucide-react";
import { motion } from "framer-motion";

export default function CapitalPage() {
  const router = useRouter();
  const state = useStore(); const { updateState } = state;
  // Start empty rather than pre-filled.
  //
  // The field used to be initialised to "50000", so a user who opened this step
  // and pressed the button declared ₹50,000 as their margin capital without
  // ever choosing it. That figure then propagated into the financial engine,
  // scheme eligibility and every viability gate, so an untouched form was
  // indistinguishable from a real declaration. The placeholder remains as a
  // visible formatting hint (a placeholder is not a value), and a capital the
  // user already declared in this session is restored.
  const [marginCapital, setMarginCapital] = useState(
    state.marginCapital != null ? String(state.marginCapital) : ""
  );

  useEffect(() => {
    if (!state.sessionId) {
      router.push("/");
    }
  }, [state.sessionId, router]);

  const handleContinue = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseInt(marginCapital, 10);
    if (!parsed || parsed <= 0) return;

    updateState({ marginCapital: parsed });
    router.push("/results");
  };

 return (
 <motion.div 
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 className="flex-1 flex flex-col items-center justify-center p-4"
 >
  <div className="w-full max-w-2xl mb-8">
  </div>


 <motion.div 
 initial={{ opacity: 0, scale: 0.95, y: 20 }}
 animate={{ opacity: 1, scale: 1, y: 0 }}
 transition={{ duration: 0.5, delay: 0.2 }}
 className="w-full max-w-lg"
 >
 <Card className="border-t-4 border-t-terminal-cyan">
 <CardHeader className="text-left pb-4 border-b border-warm-border mb-4">
 <CardTitle className="text-sm font-sans text-warm-muted">Input Parameter: Capital</CardTitle>
 </CardHeader>
 <CardContent>
 <p className="text-xs text-warm-text font-sans mb-6 uppercase tracking-wider">
 ENTER MARGIN CAPITAL TO INITIALIZE LOAN STRUCTURE SIMULATION
 </p>
 <form onSubmit={handleContinue} className="space-y-5">
 <div className="relative">
 <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-warm-primary font-bold text-lg">₹</span>
 <input
 type="number"
 className="w-full rounded-none border border-warm-border bg-warm-bg pl-10 pr-4 py-4 text-2xl font-sans text-warm-primary transition-all duration-100 focus:outline-none focus:border-warm-primary focus:ring-1 focus:ring-terminal-cyan"
  placeholder="e.g. 50000"
  value={marginCapital}
  onChange={(e) => setMarginCapital(e.target.value)}
  required
  />
  </div>
  {/* The previous "Min: ₹10,000 / Max: ₹5,00,000" line was removed: no backend
      constraint enforces either figure, so it stated a limit the system does
      not actually apply. The real scheme cap is published by /schemes. */}
 
 <Button type="submit" variant="secondary" className="w-full mt-6 py-4" disabled={!marginCapital}>
 Execute Market Analysis <ArrowRight size={16} className="ml-2" />
 </Button>
 </form>
 </CardContent>
 </Card>
 </motion.div>
 </motion.div>
 );
}
