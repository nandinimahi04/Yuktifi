"use client";
import React, { useState } from 'react';
import { useStore } from '@/lib/store';
import { Card, CardContent } from '@/components/ui/card';
import { Globe, Bell, Lock, Save, Monitor } from 'lucide-react';
import { motion } from 'framer-motion';

export default function SettingsPage() {
 const { preferredLanguage, setLanguage, userMode } = useStore();
 const [notifications, setNotifications] = useState({
 email: true,
 sms: false,
 app: true
 });

 return (
 <div className="max-w-4xl mx-auto p-4 md:p-8 animate-in fade-in duration-500 font-sans text-warm-text">
 <div className="mb-8 mt-6 flex flex-col md:flex-row justify-between md:items-end">
 <div>
 <h1 className="text-3xl font-black tracking-widest text-warm-text uppercase mb-2">System Settings</h1>
 <p className="text-warm-muted text-sm">Preferences \ Localization \ Security</p>
 </div>
 <button className="mt-4 md:mt-0 flex items-center bg-warm-primary hover:bg-warm-primary/80 text-black px-6 py-2 text-xs font-bold transition-colors">
 <Save size={16} className="mr-2" /> Save Config
 </button>
 </div>

 <div className="space-y-6">
 {/* Language & Region */}
 <Card className="bg-warm-surface border-warm-border rounded-none shadow-xl">
 <CardContent className="p-6">
 <div className="flex items-center mb-6 border-b border-warm-border pb-4">
 <Globe className="text-orange-500 mr-3" size={24} />
 <h2 className="text-lg font-bold text-warm-text">Localization</h2>
 </div>
 
 <div className="space-y-4">
 <div>
 <label className="block text-xs font-bold text-warm-muted mb-2">Display Language</label>
 <div className="flex space-x-4">
 {(['EN', 'HI', 'MR'] as const).map(lang => (
 <button
 key={lang}
 onClick={() => setLanguage(lang)}
 className={`px-6 py-3 border text-sm font-bold transition-colors ${preferredLanguage === lang ? 'bg-warm-primary/20 border-warm-primary text-warm-primary' : 'bg-warm-bg border-warm-border text-warm-muted hover:border-warm-muted'}`}
 >
 {lang === 'EN' ? 'English' : lang === 'HI' ? 'हिंदी (Hindi)' : 'मराठी (Marathi)'}
 </button>
 ))}
 </div>
 <p className="text-xs text-zinc-600 mt-2">Changes apply immediately across the entire interface.</p>
 </div>
 </div>
 </CardContent>
 </Card>

 {/* Notifications */}
 <Card className="bg-warm-surface border-warm-border rounded-none shadow-xl">
 <CardContent className="p-6">
 <div className="flex items-center mb-6 border-b border-warm-border pb-4">
 <Bell className="text-orange-500 mr-3" size={24} />
 <h2 className="text-lg font-bold text-warm-text">Alerts & Notifications</h2>
 </div>
 
 <div className="space-y-4">
 <div className="flex items-center justify-between py-3 border-b border-warm-border/50">
 <div>
 <h4 className="font-bold text-warm-text">Email Updates</h4>
 <p className="text-xs text-warm-muted mt-1">Receive weekly summary reports and application status updates.</p>
 </div>
 <button 
 onClick={() => setNotifications(prev => ({...prev, email: !prev.email}))}
 className={`w-12 h-6 rounded-full relative transition-colors ${notifications.email ? 'bg-warm-primary' : 'bg-warm-surface'}`}
 >
 <motion.div 
 layout
 className={`w-4 h-4 bg-warm-bg rounded-full absolute top-1 ${notifications.email ? 'right-1' : 'left-1'}`}
 />
 </button>
 </div>
 <div className="flex items-center justify-between py-3 border-b border-warm-border/50">
 <div>
 <h4 className="font-bold text-warm-text">SMS Alerts</h4>
 <p className="text-xs text-warm-muted mt-1">Critical alerts for loan approvals or document requests.</p>
 </div>
 <button 
 onClick={() => setNotifications(prev => ({...prev, sms: !prev.sms}))}
 className={`w-12 h-6 rounded-full relative transition-colors ${notifications.sms ? 'bg-warm-primary' : 'bg-warm-surface'}`}
 >
 <motion.div 
 layout
 className={`w-4 h-4 bg-warm-bg rounded-full absolute top-1 ${notifications.sms ? 'right-1' : 'left-1'}`}
 />
 </button>
 </div>
 </div>
 </CardContent>
 </Card>

 {/* Display */}
 <Card className="bg-warm-surface border-warm-border rounded-none shadow-xl">
 <CardContent className="p-6">
 <div className="flex items-center mb-6 border-b border-warm-border pb-4">
 <Monitor className="text-orange-500 mr-3" size={24} />
 <h2 className="text-lg font-bold text-warm-text">Interface Theme</h2>
 </div>
 
 <div>
 <p className="text-sm text-warm-muted mb-4">The platform is currently operating in <span className="text-warm-primary font-bold">Terminal Data Mode</span>.</p>
 <div className="inline-flex items-center bg-warm-bg border border-warm-border px-4 py-2 opacity-50 cursor-not-allowed">
 <span className="text-xs">Light Mode (Disabled by Admin)</span>
 </div>
 </div>
 </CardContent>
 </Card>

 </div>
 </div>
 );
}
