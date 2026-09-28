"use client";
import React, { useState } from "react";
import dynamic from "next/dynamic";

// Dynamically import the wrapper component that statically imports react-leaflet
const MapComponent = dynamic(() => import("./MapComponent"), { 
  ssr: false,
  loading: () => <div className="w-full h-64 bg-warm-bg border border-warm-border animate-pulse rounded-none flex items-center justify-center text-warm-muted font-sans text-xs uppercase tracking-widest">Loading Map...</div>
});

interface Competitor {
  name: string;
  distance_km: number;
}

interface MapProps {
  lat: number;
  lng: number;
  radiusKm: number;
  competitors?: Competitor[];
}

export function MapRadiusOverlay({ lat, lng, radiusKm, competitors = [] }: MapProps) {
  const [showCompetitors, setShowCompetitors] = useState(true);
  const [showZones, setShowZones] = useState(true);

  return (
    <div className="w-full h-full rounded-2xl overflow-hidden border border-warm-border z-0 relative">
      
      {/* Interactive Layer Toggles */}
      <div className="absolute top-3 right-3 z-[400] flex flex-col gap-1.5">
        <button 
          onClick={() => setShowCompetitors(!showCompetitors)}
          className={`px-3 py-1.5 rounded-lg text-[11px] font-medium tracking-wide border shadow-sm backdrop-blur-sm transition-all ${
            showCompetitors 
              ? 'bg-red-50/95 border-red-400 text-red-700 font-semibold' 
              : 'bg-white/90 border-slate-300 text-slate-600 hover:bg-white'
          }`}
        >
          {showCompetitors ? 'Hide Competitors' : 'Show Competitors'}
        </button>
        <button 
          onClick={() => setShowZones(!showZones)}
          className={`px-3 py-1.5 rounded-lg text-[11px] font-medium tracking-wide border shadow-sm backdrop-blur-sm transition-all ${
            showZones 
              ? 'bg-emerald-50/95 border-emerald-500 text-emerald-700 font-semibold' 
              : 'bg-white/90 border-slate-300 text-slate-600 hover:bg-white'
          }`}
        >
          {showZones ? 'Hide Opp. Zones' : 'Show Opp. Zones'}
        </button>
      </div>

      <MapComponent 
        lat={lat} 
        lng={lng} 
        radiusKm={radiusKm} 
        showCompetitors={showCompetitors} 
        showZones={showZones} 
        competitors={competitors} 
      />
    </div>
  );
}
