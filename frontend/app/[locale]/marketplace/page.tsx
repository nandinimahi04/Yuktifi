"use client";
import React, { useState } from 'react';
import { useStore } from '@/lib/store';
import { Card, CardContent } from '@/components/ui/card';
import { Search, MapPin, ShieldCheck, Truck, Star, Phone, ArrowRight, Package, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';

const DUMMY_VENDORS = [
  {
    id: 1,
    name: "Mahindra Automotives (Authorized)",
    category: "Heavy Machinery",
    location: "Nagpur MIDC (12 km away)",
    rating: 4.8,
    reviews: 124,
    verified: true,
    products: ["Commercial Tractors", "Delivery Vans", "Loading Tempos"],
    deliveryTime: "3-5 Days",
    estCost: "₹5.5L - ₹12L"
  },
  {
    id: 2,
    name: "Shree Ganesh Textiles & Looms",
    category: "Manufacturing",
    location: "Solapur East (4 km away)",
    rating: 4.5,
    reviews: 89,
    verified: true,
    products: ["Industrial Sewing Machines", "Cotton Processing Units", "Fabric Cutters"],
    deliveryTime: "7-10 Days",
    estCost: "₹45k - ₹2.5L"
  },
  {
    id: 3,
    name: "TechVision Retail Solutions",
    category: "Electronics",
    location: "Pune Central (Dispatch Only)",
    rating: 4.2,
    reviews: 56,
    verified: false,
    products: ["POS Systems", "Barcode Scanners", "Billing Printers"],
    deliveryTime: "1-2 Days",
    estCost: "₹15k - ₹50k"
  }
];

export default function Marketplace() {
  const { categoryName, locationName } = useStore();
  const [search, setSearch] = useState("");

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8 text-warm-text animate-in fade-in duration-500">
      
      <div className="mb-8 mt-6 flex flex-col md:flex-row justify-between md:items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Vendor & Equipment Hub</h1>
          <p className="text-warm-muted mt-2">Browse sample supplier listings for your {categoryName || 'Business'}.</p>
        </div>
      </div>

      {/*
        Removed: an insight panel titled "NSFDC SUBSIDY APPLICABLE" reading
        "Vendors with the green 'Verified' badge are pre-approved by the
        government. Purchasing from them automatically qualifies you for a 5% GST
        rebate on heavy machinery."

        Three separate fabrications in two sentences, each of which a user could
        act on with money:

        - "pre-approved by the government" - the `verified` flag is a literal on
          hardcoded sample vendors. No vendor is checked against any register.
        - "automatically qualifies you for" - no purchase here is connected to
          any eligibility engine. `/match-scheme` routes on declared project cost
          and contribution; it does not look at a vendor list, and it states that
          it has assessed no eligibility criteria.
        - "a 5% GST rebate on heavy machinery" - a tax claim with no basis in
          this repository, attached to a government subsidy panel.

        A user who buys machinery on the strength of that sentence has been told
        to expect a subsidy that will not arrive. The list below is retained as
        sample content and labelled as such.
      */}
      <div className="mb-8 flex items-start gap-3 bg-amber-50 border-2 border-amber-300 rounded-xl p-4">
        <AlertTriangle size={18} className="text-amber-700 mt-0.5 shrink-0" />
        <div>
          <div className="text-sm font-bold text-warm-text">
            Sample vendor listings — not a verified network
          </div>
          <p className="text-xs text-warm-muted mt-1">
            These suppliers are placeholders, not screened against any register.
            No purchase here affects government scheme eligibility, and no rebate
            is applied automatically. Check any subsidy claim with the agency
            directly.
          </p>
        </div>
      </div>

      <div className="flex flex-col md:flex-row space-y-4 md:space-y-0 md:space-x-4 mb-8">
        <div className="flex-1 relative">
          <Search size={20} className="absolute left-4 top-1/2 transform -translate-y-1/2 text-warm-muted" />
          <input 
            type="text" 
            placeholder="Search equipment (e.g. Sewing Machine, POS...)"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-4 rounded-xl border border-warm-border focus:outline-none focus:ring-2 focus:ring-warm-primary/50 transition-shadow bg-warm-surface"
          />
        </div>
        <select className="px-6 py-4 rounded-xl border border-warm-border focus:outline-none bg-warm-surface text-warm-text font-medium cursor-pointer">
          <option>Sort by: Recommended</option>
          <option>Distance: Nearest</option>
          <option>Price: Low to High</option>
          <option>Rating: Highest</option>
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {DUMMY_VENDORS.map((vendor, idx) => (
          <motion.div 
            key={vendor.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
          >
            <Card className="bg-warm-surface border-warm-border shadow-sm hover:shadow-md transition-shadow h-full flex flex-col overflow-hidden group">
              <div className="h-2 w-full bg-warm-bg group-hover:bg-warm-primary transition-colors"></div>
              <CardContent className="p-6 flex flex-col flex-1">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-bold text-lg leading-tight mb-1">{vendor.name}</h3>
                    <div className="flex items-center text-xs text-warm-muted">
                      <MapPin size={12} className="mr-1" /> {vendor.location}
                    </div>
                  </div>
                  {/* The badge is gone rather than relabelled. A green shield
                      captioned "NSFDC Verified Vendor" on a hardcoded list told
                      the reader the agency had vetted this supplier; no such
                      check exists, and the shield is the part that carried the
                      claim. */}
                  <div className="bg-amber-50 text-amber-700 p-1.5 rounded-full" title="Sample listing, not screened against any register">
                    <ShieldCheck size={18} />
                  </div>
                </div>

                <div className="flex items-center space-x-1 mb-6">
                  <Star size={14} className="text-amber-500 fill-amber-500" />
                  <span className="text-sm font-bold">{vendor.rating}</span>
                  <span className="text-xs text-warm-muted">({vendor.reviews} reviews)</span>
                </div>

                <div className="space-y-3 mb-6 flex-1">
                  <h4 className="text-xs font-bold text-warm-muted uppercase tracking-wider">Top Equipment</h4>
                  <ul className="space-y-2">
                    {vendor.products.map((p, i) => (
                      <li key={i} className="flex items-start text-sm">
                        <Package size={14} className="mr-2 mt-0.5 text-warm-primary/70" />
                        <span>{p}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="pt-4 border-t border-warm-border mb-6">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs text-warm-muted">Estimated Cost:</span>
                    <span className="font-bold text-warm-primary">{vendor.estCost}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-warm-muted">Delivery:</span>
                    <span className="text-sm flex items-center"><Truck size={14} className="mr-1 text-warm-muted" /> {vendor.deliveryTime}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-auto">
                  <button className="flex items-center justify-center py-2 px-4 border border-warm-border rounded-lg hover:bg-warm-bg transition-colors text-sm font-medium">
                    <Phone size={16} className="mr-2 text-warm-muted" /> Call
                  </button>
                  <button className="flex items-center justify-center py-2 px-4 bg-warm-primary hover:bg-warm-primary/90 text-warm-text rounded-lg transition-colors text-sm font-medium">
                    Request Quote
                  </button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
