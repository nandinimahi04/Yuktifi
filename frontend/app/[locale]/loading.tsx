import React from 'react';
import { Loader2 } from 'lucide-react';
import Image from 'next/image';

export default function Loading() {
  return (
    <div className="min-h-screen bg-[#fdfbf6] flex flex-col items-center justify-center p-4 font-sans relative overflow-hidden">
      {/* Decorative Background */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-20">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-[#ea580c] blur-3xl opacity-20"></div>
        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] rounded-full bg-[#166534] blur-3xl opacity-10"></div>
      </div>
      
      <div className="relative z-10 flex flex-col items-center bg-white/60 backdrop-blur-md border border-[#E7DCC7] p-8 rounded-[2rem] shadow-sm">
        <div className="flex items-center gap-3 mb-6 relative">
           <Image
              src="/india-emblem.png"
              alt="Government of India"
              width={40}
              height={40}
              className="object-contain"
            />
            <div className="flex flex-col justify-center">
              <span className="font-display font-bold text-2xl text-[#294C38] tracking-tight leading-none">YuktiFi</span>
            </div>
        </div>
        
        <Loader2 className="w-10 h-10 text-[#ea580c] animate-spin mb-4" />
        <h2 className="text-[#221D17] font-bold text-lg">Loading...</h2>
        <p className="text-[#55503F] text-sm mt-2 text-center max-w-xs">
          Fetching data and preparing your workspace. Please wait a moment.
        </p>
      </div>
    </div>
  );
}
