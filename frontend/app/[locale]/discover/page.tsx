"use client";
import React from 'react';
import { 
  Bell, ChevronDown, Search, ArrowRight, Clock
} from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';

// 1. Top Header with Global Search
const TopHeader = () => (
  <div className="flex justify-between items-center mb-8 pt-2">
    <div className="flex-1 max-w-xl relative">
      <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-faint" />
      <input 
        type="text" 
        placeholder="Search for business ideas..." 
        className="w-full bg-white border border-premium-border rounded-2xl py-2.5 pl-11 pr-4 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-saffron"
      />
    </div>
    <div className="flex items-center space-x-5">
      <button className="text-ink-soft hover:text-ink transition-colors">
        <Bell size={20} />
      </button>
      <button className="text-ink-soft hover:text-ink transition-colors">
        <Clock size={20} />
      </button>
      <button className="flex items-center px-3 py-1.5 bg-white border border-premium-border rounded-xl text-sm font-bold shadow-sm hover:border-premium-border-strong">
        EN <ChevronDown size={14} className="ml-1 text-ink-soft" />
      </button>
    </div>
  </div>
);

interface BusinessCardProps {
  id: string;
  name: string;
  category: string;
  score: number;
  demand: string;
  demandColor: string;
  competition: string;
  competitionColor: string;
  investment: string;
  image: string;
}

const BusinessCard = ({ name, category, score, demand, demandColor, competition, competitionColor, investment, image, id }: BusinessCardProps) => {
  const router = useRouter();
  const { updateState } = useStore();

  const handleViewDetails = () => {
    updateState({ categoryId: id });
    router.push(`/market-intelligence/${id}`);
  };

  return (
    <div className="bg-white border border-premium-border rounded-2xl p-6 shadow-sm hover:shadow-md hover:border-premium-border-strong transition-all flex flex-col h-full group">
      
      {/* Header: Image & Titles */}
      <div className="flex items-center mb-6">
        <div className="w-20 h-20 rounded-xl overflow-hidden shrink-0 mr-4 bg-cream shadow-sm relative">
          <Image src={image} alt={name} fill className="object-cover" />
        </div>
        <div className="flex flex-col">
          <h3 className="font-bold text-ink text-lg leading-tight mb-1">{name}</h3>
          <p className="text-xs font-medium text-ink-soft">{category}</p>
        </div>
      </div>

      {/* YuktiFi Score */}
      <div className="mb-6 ml-24">
        <div className="text-[10px] font-bold text-ink-soft uppercase tracking-wider mb-1">YuktiFi Score</div>
        <div className="flex items-baseline">
          <span className="text-3xl font-bold text-forest-deep">{score}</span>
          <span className="text-sm font-bold text-ink-soft">/100</span>
        </div>
      </div>

      {/* Badges */}
      <div className="flex items-center space-x-3 mb-8">
        <div className={`px-3 py-1 rounded-full text-[10px] font-bold flex items-center shadow-sm ${demandColor}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5 opacity-70"></span>
          {demand}
        </div>
        <div className={`px-3 py-1 rounded-full text-[10px] font-bold flex items-center shadow-sm ${competitionColor}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5 opacity-70"></span>
          {competition}
        </div>
      </div>

      {/* Footer: Investment & Action */}
      <div className="mt-auto flex justify-between items-end">
        <div>
          <div className="text-[10px] font-bold text-ink-soft uppercase tracking-wider mb-1">Investment</div>
          <div className="font-bold text-ink">{investment}</div>
        </div>
        <button onClick={handleViewDetails} className="px-5 py-2.5 bg-[#ea580c] hover:bg-[#c2410c] text-white rounded-xl text-sm font-bold shadow-sm transition-colors flex items-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#ea580c]">
          View Details <ArrowRight size={14} className="ml-1.5" />
        </button>
      </div>

    </div>
  );
};

export default function DiscoverPage() {
  const [activeFilter, setActiveFilter] = React.useState('recommended');
  
  const baseBusinesses = [
    {
      id: "e-rickshaw",
      name: "E-Rickshaw",
      category: "Transport & Logistics",
      score: 91,
      demand: "High Demand",
      demandColor: "bg-emerald-100 text-emerald-700 border border-emerald-200",
      competition: "Medium Competition",
      competitionColor: "bg-orange-100 text-orange-700 border border-orange-200",
      investment: "₹9.5L - ₹10L",
      image: "https://images.unsplash.com/photo-1593955681577-c9de066928e4?q=80&w=400&auto=format&fit=crop"
    },
    {
      id: "grocery-store",
      name: "Grocery Store",
      category: "Retail & Trading",
      score: 76,
      demand: "High Demand",
      demandColor: "bg-orange-100 text-orange-700 border border-orange-200", // Matches screenshot
      competition: "High Competition",
      competitionColor: "bg-orange-100 text-orange-700 border border-orange-200",
      investment: "₹5L - ₹8L",
      image: "https://images.unsplash.com/photo-1578916171728-46686eac8d58?q=80&w=400&auto=format&fit=crop"
    },
    {
      id: "mobile-repair",
      name: "Mobile Repair Shop",
      category: "Repair & Services",
      score: 82,
      demand: "Medium Demand",
      demandColor: "bg-emerald-100 text-emerald-700 border border-emerald-200",
      competition: "Low Competition",
      competitionColor: "bg-emerald-100 text-emerald-700 border border-emerald-200",
      investment: "₹2L - ₹4L",
      image: "https://images.unsplash.com/photo-1581092160562-40aa08e78837?q=80&w=400&auto=format&fit=crop"
    },
    {
      id: "dairy-farming",
      name: "Dairy Farming",
      category: "Dairy & Livestock",
      score: 78,
      demand: "High Demand",
      demandColor: "bg-amber-100 text-amber-700 border border-amber-200",
      competition: "Medium Competition",
      competitionColor: "bg-amber-100 text-amber-700 border border-amber-200",
      investment: "₹4L - ₹7L",
      image: "https://images.unsplash.com/photo-1570042225831-d98fa7577f1e?q=80&w=400&auto=format&fit=crop"
    },
    {
      id: "tailoring-unit",
      name: "Tailoring Unit",
      category: "Manufacturing",
      score: 69,
      demand: "Medium Demand",
      demandColor: "bg-orange-100 text-orange-700 border border-orange-200",
      competition: "Medium Competition",
      competitionColor: "bg-orange-100 text-orange-700 border border-orange-200",
      investment: "₹3L - ₹6L",
      image: "https://images.unsplash.com/photo-1556228578-8d89b6acd8fa?q=80&w=400&auto=format&fit=crop"
    },
    {
      id: "organic-farming",
      name: "Organic Farming",
      category: "Agriculture & Allied",
      score: 74,
      demand: "High Demand",
      demandColor: "bg-emerald-100 text-emerald-700 border border-emerald-200",
      competition: "Low Competition",
      competitionColor: "bg-emerald-100 text-emerald-700 border border-emerald-200",
      investment: "₹2L - ₹5L",
      image: "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?q=80&w=400&auto=format&fit=crop"
    }
  ];

  const allBusinesses = [
    ...baseBusinesses,
    ...baseBusinesses.map(b => ({ ...b, id: b.id + '-all', score: b.score - 10 }))
  ];

  const displayedBusinesses = activeFilter === 'recommended' ? baseBusinesses : allBusinesses;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 py-6 pb-20 animate-in fade-in duration-500 bg-[#fcfbf8] min-h-screen">
      <TopHeader />
      
      <div className="mb-6 border-b border-premium-border pb-6">
        <h1 className="text-[32px] font-bold text-forest-deep tracking-tight mb-2">
          Find Your Opportunity
        </h1>
        <p className="text-sm font-medium text-ink-soft">
          Businesses ranked for your location, capital and profile.
        </p>
      </div>

      {/* Toggles */}
      <div className="flex space-x-3 mb-8">
        <button 
          onClick={() => setActiveFilter('recommended')}
          className={`px-6 py-2.5 rounded-xl text-sm font-bold shadow-sm transition-colors ${activeFilter === 'recommended' ? 'bg-[#ea580c] text-white' : 'bg-white border border-premium-border text-ink-soft hover:text-ink'}`}
        >
          Recommended for you
        </button>
        <button 
          onClick={() => setActiveFilter('all')}
          className={`px-6 py-2.5 rounded-xl text-sm font-bold shadow-sm transition-colors ${activeFilter === 'all' ? 'bg-[#ea580c] text-white' : 'bg-white border border-premium-border text-ink-soft hover:text-ink'}`}
        >
          Browse All
        </button>
      </div>

      {/* Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {displayedBusinesses.map((biz) => (
          <BusinessCard key={biz.id} {...biz} />
        ))}
      </div>
      
    </div>
  );
}
