"use client";

import { useEffect, useState } from "react";
import { FlaskConical, ShieldQuestion } from "lucide-react";
import { onDataModeChange } from "@/lib/api-client";

/**
 * Says whether the data on screen is live.
 *
 * `DEMO_MODE=true` switches off outbound network in the backend's provider
 * clients, so prices, competitor counts and population figures come from
 * bundled fixtures instead of being looked up. The flag is the right one to
 * have - a demo should not depend on someone else's API being up - but it was
 * completely invisible, and a demo run and a live run were indistinguishable on
 * screen. Someone reading a recommendation had no way to know whether the
 * competitor count behind it had been looked up.
 *
 * Rendered only when the mode is known and is `demo`. A production run shows
 * nothing, because the label is noise there. An *unknown* mode is deliberately
 * not treated as live: if the header never arrived, this says so rather than
 * staying quiet.
 */
export default function DataModeBanner() {
  const [mode, setMode] = useState<"live" | "demo" | null>(null);

  useEffect(() => onDataModeChange(setMode), []);

  if (mode !== "demo") return null;

  return (
    <div
      role="status"
      className="w-full bg-amber-50 border-b border-amber-300 px-4 py-2.5 flex items-start gap-2.5"
    >
      <FlaskConical className="text-amber-600 mt-0.5 shrink-0" size={16} />
      <div className="text-sm">
        <p className="font-bold text-amber-900">
          Demo data — not live
        </p>
        <p className="text-amber-800">
          The backend is running with <code className="font-mono">DEMO_MODE</code>,
          so external providers are not being called. Prices, competitor counts
          and population figures on this screen come from bundled sample data
          and were not looked up. The arithmetic and the financial model are
          real; the market inputs are not current.
        </p>
      </div>
    </div>
  );
}

/**
 * The "I could not tell" case, for the narrow window before the first response
 * lands. Used by screens that would otherwise render numbers during that window.
 */
export function DataModeUnknownNotice() {
  const [mode, setMode] = useState<"live" | "demo" | null>(null);
  useEffect(() => onDataModeChange(setMode), []);

  if (mode === "live") return null;

  return (
    <div className="flex items-center gap-2 text-xs text-ink-soft">
      <ShieldQuestion size={13} />
      Data freshness:{" "}
      {mode === "demo" ? (
        <span className="font-bold text-amber-700">demo data, not live</span>
      ) : (
        <span>unconfirmed — the server did not report whether this is live</span>
      )}
    </div>
  );
}
