"use client";
import React from 'react';
import { useStore } from '@/lib/store';
import { Card, CardContent } from '@/components/ui/card';
import { User, ShieldCheck, FileText, AlertCircle, Phone, Mail, Building, MapPin } from 'lucide-react';
import { YuktiFiInsight } from '@/components/YuktiFiInsight';

export default function ProfilePage() {
  const { categoryName, locationName, marginCapital, userMode } = useStore();

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8 animate-in fade-in duration-500 font-sans text-warm-text">
      <div className="mb-8 mt-6">
        <h1 className="text-3xl font-bold tracking-tight text-warm-text mb-2">Platform Profile</h1>
        <p className="text-warm-muted font-medium text-sm">Identity Verification & Core Details</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="bg-warm-surface border-warm-border rounded-2xl shadow-sm col-span-2 overflow-hidden">
          <CardContent className="p-6">
            <div className="flex items-start space-x-6">
              <div className="w-24 h-24 bg-warm-bg border-2 border-warm-border flex items-center justify-center text-warm-muted rounded-full relative shadow-sm">
                <User size={48} />
                <div className="absolute -bottom-1 -right-1 bg-emerald-500 text-warm-text p-1.5 rounded-full border-2 border-white shadow-sm" title="Identity Verified">
                  <ShieldCheck size={20} />
                </div>
              </div>
              <div className="flex-1">
                <h2 className="text-2xl font-bold text-warm-text tracking-tight mb-1">Rural Entrepreneur</h2>
                <div className="text-xs text-warm-primary font-bold tracking-wider mb-4 bg-orange-50 inline-block px-2 py-1 rounded-md border border-orange-100">UID: YK-492-771</div>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="flex items-center text-sm font-medium text-warm-muted">
                    <Phone size={16} className="mr-2 text-warm-primary" />
                    +91 98*** **341
                  </div>
                  <div className="flex items-center text-sm font-medium text-warm-muted">
                    <Mail size={16} className="mr-2 text-warm-primary" />
                    user@example.com
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-warm-surface border-warm-border rounded-2xl shadow-sm overflow-hidden">
          <CardContent className="p-6 flex flex-col justify-center h-full">
            <h3 className="text-xs text-warm-muted uppercase tracking-wider font-bold mb-4">Linked Accounts</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between bg-warm-bg border border-warm-border rounded-xl p-3 shadow-sm">
                <div className="flex items-center">
                  <FileText size={16} className="text-warm-primary mr-2" />
                  <span className="text-xs font-bold text-warm-text">Aadhaar (UIDAI)</span>
                </div>
                <ShieldCheck size={16} className="text-emerald-500" />
              </div>
              <div className="flex items-center justify-between bg-warm-bg border border-warm-border rounded-xl p-3 shadow-sm">
                <div className="flex items-center">
                  <FileText size={16} className="text-warm-primary mr-2" />
                  <span className="text-xs font-bold text-warm-text">PAN</span>
                </div>
                <AlertCircle size={16} className="text-amber-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <h2 className="text-xl font-bold text-warm-text mb-4 border-b border-warm-border pb-2">Business Intent</h2>
      
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-warm-surface border border-warm-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center text-warm-muted mb-2">
            <Building size={16} className="mr-2 text-warm-primary" />
            <span className="text-xs font-bold uppercase tracking-wider">Category</span>
          </div>
          <div className="text-lg text-warm-text font-bold">{categoryName || 'Not Set'}</div>
        </div>
        <div className="bg-warm-surface border border-warm-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center text-warm-muted mb-2">
            <MapPin size={16} className="mr-2 text-warm-primary" />
            <span className="text-xs font-bold uppercase tracking-wider">Location</span>
          </div>
          <div className="text-lg text-warm-text font-bold">{locationName || 'Not Set'}</div>
        </div>
        <div className="bg-warm-surface border border-warm-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center text-warm-muted mb-2">
            <ShieldCheck size={16} className="mr-2 text-warm-primary" />
            <span className="text-xs font-bold uppercase tracking-wider">Initial Capital</span>
          </div>
          <div className="text-lg text-warm-text font-bold">₹{marginCapital ? marginCapital.toLocaleString('en-IN') : '0'}</div>
        </div>
      </div>

      <YuktiFiInsight 
        type="info"
        title="UDYAM REGISTRATION PENDING"
        message="Your PAN verification is currently processing. Once completed, your Udyam Micro, Small and Medium Enterprises Registration will be automatically generated and linked to this profile."
        className="mb-8"
      />
    </div>
  );
}
