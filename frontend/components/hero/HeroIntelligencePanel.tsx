"use client";

import React, { useRef, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Zap } from 'lucide-react';

const CITIES = [
  { id: 'mumbai',    name: 'Mumbai',    x: 24, y: 61, demand: 'High',     sector: 'Retail',    delay: 0    },
  { id: 'delhi',     name: 'Delhi',     x: 37, y: 23, demand: 'High',     sector: 'Tech',      delay: 0.3  },
  { id: 'bengaluru', name: 'Bengaluru', x: 36, y: 74, demand: 'Very High',sector: 'Agri',      delay: 0.6  },
  { id: 'hyderabad', name: 'Hyderabad', x: 41, y: 65, demand: 'Medium',   sector: 'Food',      delay: 0.9  },
  { id: 'kolkata',   name: 'Kolkata',   x: 64, y: 45, demand: 'High',     sector: 'Textile',   delay: 1.2  },
  { id: 'jaipur',    name: 'Jaipur',    x: 32, y: 32, demand: 'Medium',   sector: 'Tourism',   delay: 1.5  },
  { id: 'pune',      name: 'Pune',      x: 28, y: 64, demand: 'High',     sector: 'Mfg',       delay: 1.8  },
  { id: 'ahmedabad', name: 'Ahmedabad', x: 20, y: 47, demand: 'Very High',sector: 'Textile',   delay: 2.1  },
  { id: 'surat',     name: 'Surat',     x: 20, y: 55, demand: 'High',     sector: 'Diamonds',  delay: 2.4  },
  { id: 'jodhpur',   name: 'Jodhpur',   x: 24, y: 37, demand: 'Medium',   sector: 'Handicraft',delay: 2.7  },
  { id: 'nagpur',    name: 'Nagpur',    x: 40, y: 56, demand: 'Medium',   sector: 'Orange Farm',delay: 3.0 },
];

const demandColor: Record<string, string> = {
  'Very High': '#ea580c',
  'High':      '#d97706',
  'Medium':    '#166534',
};

export function HeroIntelligencePanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [spotlight, setSpotlight] = useState<{ x: number; y: number } | null>(null);
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setSpotlight({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  }, []);

  const handleMouseEnter = () => setIsHovered(true);
  const handleMouseLeave = () => {
    setIsHovered(false);
    setSpotlight(null);
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="relative w-full max-w-lg mx-auto lg:ml-auto h-[380px] sm:h-[460px] flex items-center justify-center z-10 pt-4 lg:pt-0 select-none"
    >
      {/* India Map background */}
      <motion.div
        className="absolute inset-0 bg-contain bg-center bg-no-repeat drop-shadow-2xl"
        style={{ backgroundImage: `url('/india-map.svg')` }}
        animate={{ scale: isHovered ? 1.03 : 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      />

      {/* Spotlight / cursor glow overlay */}
      {spotlight && (
        <div
          className="absolute inset-0 pointer-events-none z-20"
          style={{
            background: `radial-gradient(circle 140px at ${spotlight.x}px ${spotlight.y}px, rgba(234,88,12,0.18) 0%, rgba(234,88,12,0.07) 45%, transparent 75%)`,
            transition: 'background 0.05s linear',
          }}
        />
      )}



      {/* City hotspot pins */}
      {CITIES.map((city) => (
        <motion.div
          key={city.id}
          className="absolute"
          style={{ left: `${city.x}%`, top: `${city.y}%` }}
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', delay: city.delay, stiffness: 200, damping: 12 }}
        >
          {/* Pulsing ring */}
          <motion.div
            className="absolute rounded-full"
            style={{
              width: 28, height: 28,
              top: -6, left: -6,
              border: `2px solid ${demandColor[city.demand]}`,
              opacity: 0.5,
            }}
            animate={{ scale: [1, 1.8, 1], opacity: [0.5, 0, 0.5] }}
            transition={{ duration: 2.5, repeat: Infinity, delay: city.delay }}
          />

          {/* Dot */}
          <div
            className="relative w-4 h-4 rounded-full shadow-lg border-2 border-white cursor-pointer group z-30"
            style={{ backgroundColor: demandColor[city.demand] }}
          >
            {/* Tooltip */}
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 hidden group-hover:flex flex-col items-center z-50 pointer-events-none">
              <div className="bg-white rounded-xl shadow-xl px-3 py-2 text-left border border-premium-border min-w-[130px]">
                <p className="font-bold text-ink text-xs">{city.name}</p>
                <p className="text-[10px] text-ink-soft">{city.sector}</p>
                <span
                  className="inline-block mt-1 text-[9px] font-bold px-1.5 py-0.5 rounded-full text-white"
                  style={{ backgroundColor: demandColor[city.demand] }}
                >
                  {city.demand} Demand
                </span>
              </div>
              <div className="w-2 h-2 bg-white border-r border-b border-premium-border rotate-45 -mt-1" />
            </div>
          </div>
        </motion.div>
      ))}

      {/* Top-right stat card */}
      <motion.div
        initial={{ opacity: 0, x: 30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.5, duration: 0.6 }}
        className="absolute top-[8%] right-0 bg-white/90 backdrop-blur-md rounded-2xl shadow-xl border border-premium-border px-4 py-3 flex items-center gap-3 min-w-[170px] z-30"
      >
        <div className="bg-[#ea580c]/10 p-2 rounded-full">
          <Zap className="w-4 h-4 text-[#ea580c]" />
        </div>
        <div>
          <p className="font-bold text-ink text-lg leading-none">2,400+</p>
          <p className="text-[10px] text-ink-soft font-semibold uppercase tracking-wider mt-0.5">Active Opportunities</p>
        </div>
      </motion.div>

      {/* Bottom-right stat card */}
      <motion.div
        initial={{ opacity: 0, x: 30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.8, duration: 0.6 }}
        className="absolute bottom-[8%] right-0 bg-white/90 backdrop-blur-md rounded-2xl shadow-xl border border-premium-border px-4 py-3 flex items-center gap-3 min-w-[170px] z-30"
      >
        <div className="bg-forest/10 p-2 rounded-full">
          <TrendingUp className="w-4 h-4 text-forest" />
        </div>
        <div>
          <p className="font-bold text-ink text-lg leading-none">583</p>
          <p className="text-[10px] text-ink-soft font-semibold uppercase tracking-wider mt-0.5">Districts Covered</p>
        </div>
      </motion.div>

      {/* Legend */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.2, duration: 0.5 }}
        className="absolute bottom-[5%] left-0 bg-white/90 backdrop-blur-md rounded-xl shadow-lg border border-premium-border px-3 py-2 flex flex-col gap-1 z-30"
      >
        {Object.entries(demandColor).map(([label, color]) => (
          <div key={label} className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
            <span className="text-[9px] font-semibold text-ink-soft uppercase tracking-wide">{label} Demand</span>
          </div>
        ))}
      </motion.div>
    </div>
  );
}
