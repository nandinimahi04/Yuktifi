import React from "react";
import { ShieldCheck, AlertTriangle, XCircle, HelpCircle } from "lucide-react";

interface Props {
  verdict: string;
}

export function VerdictBanner({ verdict }: Props) {
  switch (verdict) {
    case "GO":
      return (
        <div className="flex items-start space-x-3 p-4 bg-emerald-900/40 border border-emerald-500/30 rounded-lg">
          <ShieldCheck className="text-emerald-400 mt-0.5 shrink-0" size={20} />
          <div>
            <h4 className="font-semibold text-emerald-400">Highly Recommended</h4>
            <p className="text-sm text-emerald-100/70 mt-1">
              Strong financial viability with good buffer against market fluctuations.
            </p>
          </div>
        </div>
      );
    case "CAUTION":
      return (
        <div className="flex items-start space-x-3 p-4 bg-amber-900/40 border border-amber-500/30 rounded-lg">
          <AlertTriangle className="text-amber-400 mt-0.5 shrink-0" size={20} />
          <div>
            <h4 className="font-semibold text-amber-400">Proceed with Caution</h4>
            <p className="text-sm text-amber-100/70 mt-1">
              Tight margins. The project is sensitive to revenue drops or cost increases.
            </p>
          </div>
        </div>
      );
    case "ALTERNATIVE":
      return (
        <div className="flex items-start space-x-3 p-4 bg-blue-900/40 border border-blue-500/30 rounded-lg">
          <HelpCircle className="text-blue-400 mt-0.5 shrink-0" size={20} />
          <div>
            <h4 className="font-semibold text-blue-400">Alternative Options Available</h4>
            <p className="text-sm text-blue-100/70 mt-1">
              Consider shifting business model or seeking higher margin categories.
            </p>
          </div>
        </div>
      );
    case "NOT_RECOMMENDED":
    default:
      return (
        <div className="flex items-start space-x-3 p-4 bg-red-900/40 border border-red-500/30 rounded-lg">
          <XCircle className="text-red-400 mt-0.5 shrink-0" size={20} />
          <div>
            <h4 className="font-semibold text-red-400">Not Recommended</h4>
            <p className="text-sm text-red-100/70 mt-1">
              High risk of defaulting on loans. Project does not cover its operational costs and Monthly Installment.
            </p>
          </div>
        </div>
      );
  }
}
