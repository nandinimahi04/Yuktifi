import React from 'react';
import { MapPinOff, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface Props {
  locationName: string;
  message: string;
}

export function LocationUnavailableState({ locationName, message }: Props) {
  return (
    <div className="flex flex-col items-center justify-center p-8 bg-white border border-premium-border rounded-3xl shadow-card max-w-2xl mx-auto mt-12 text-center">
      <div className="w-16 h-16 bg-orange-50 rounded-full flex items-center justify-center mb-6">
        <MapPinOff className="text-orange-500" size={32} />
      </div>
      <h2 className="text-2xl font-display font-bold text-forest-deep mb-2">
        Data Unavailable for {locationName}
      </h2>
      <p className="text-ink-soft mb-8 leading-relaxed max-w-md">
        {message || "We currently do not have detailed market intelligence for this location. We are continuously expanding our dataset."}
      </p>
      
      <Link href="/">
        <button className="px-6 py-3 bg-forest hover:bg-forest-deep text-white rounded-xl font-bold flex items-center transition-colors">
          <ArrowLeft size={18} className="mr-2" /> Try Another Location
        </button>
      </Link>
    </div>
  );
}
