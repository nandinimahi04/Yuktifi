import React, { useState } from "react";
import { Info } from "lucide-react";

interface Props {
  source: string;
  confidence: string;
}

export function SourceTooltip({ source, confidence }: Props) {
  const [show, setShow] = useState(false);
  
  const getConfidenceColor = (level: string) => {
    switch (level.toLowerCase()) {
      case "high": return "text-warm-secondary";
      case "medium": return "text-orange-500";
      case "low": return "text-red-600";
      default: return "text-warm-primary";
    }
  };

  return (
    <div className="relative inline-block" onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      <Info size={14} className="text-warm-muted hover:text-warm-primary transition-colors cursor-help inline ml-1" />
      {show && (
        <div className="absolute z-50 w-64 p-3 mt-2 bg-warm-bg border border-warm-border shadow-[0_0_15px_rgba(0,0,0,0.5)] text-[10px] right-0 sm:left-1/2 sm:-translate-x-1/2 font-sans uppercase tracking-widest leading-relaxed">
          <div className="flex flex-col space-y-2">
            <div>
              <span className="text-warm-muted block mb-0.5">DATA_SOURCE_ORIGIN</span>
              <span className="text-warm-text">{source}</span>
            </div>
            <div className="pt-2 border-t border-warm-border">
              <span className="text-warm-muted block mb-0.5">CONFIDENCE_LEVEL</span>
              <span className={`font-bold ${getConfidenceColor(confidence)}`}>[{confidence}]</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
