"use client";
import React, { useState } from 'react';
import { useStore } from '@/lib/store';
import { 
  Search, LayoutDashboard, BarChart3, Calculator, Target, Activity, 
  FileText, CheckSquare, Folder, HelpCircle, MapPin, ChevronDown, User, 
  BarChart, ListOrdered, FileArchive, Menu, PanelLeftClose
} from 'lucide-react';
import Image from 'next/image';
import { Link, usePathname } from '@/routing';
import { useTranslations } from 'next-intl';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';

export function Sidebar() {
  const { userMode, categoryId, profileName } = useStore();
  const [isOpen, setIsOpen] = useState(true);
  const pathname = usePathname();
  const t = useTranslations('navigation');
  
  const publicPages = ['/', '/onboarding', '/how-it-works', '/about', '/support'];
  // The pathname from next/navigation will include the locale if not default,
  // but next-intl's usePathname from routing.ts strips it. So we should use the routing.ts usePathname!
  // Wait, I imported it from next/navigation above. I should import from @/routing.
  // Actually, I will use `usePathname` from @/routing instead of next/navigation.
  
  if (publicPages.includes(pathname)) return null;

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)} 
        className="fixed top-4 left-4 z-50 p-2 bg-white border border-premium-border rounded-md shadow-sm text-ink hover:bg-cream hidden md:flex items-center justify-center transition-colors"
      >
        <Menu size={20} className="text-forest" />
      </button>
    );
  }

  const NavLink = ({ href, icon: Icon, label, isActive = false, className = "" }: { href: string, icon: any, label: string, isActive?: boolean, className?: string }) => {
    return (
      <Link 
        href={href} 
        className={`flex items-center px-4 py-3 rounded-2xl mb-1 transition-all font-medium text-sm ${
          isActive 
            ? 'bg-[#fff5f0] text-[#ea580c] font-bold shadow-sm ring-1 ring-black/5' 
            : 'text-ink-soft hover:bg-black/5 hover:text-ink'
        } ${className}`}
      >
        <Icon size={18} className={`mr-4 ${isActive ? 'text-[#ea580c]' : 'text-ink-soft'}`} />
        {label}
      </Link>
    );
  };

  return (
    <aside className="w-[280px] bg-[#fcfbf8] text-ink hidden md:flex flex-col border-r border-premium-border/50 shadow-sm shrink-0 h-screen overflow-hidden">
      
      <div className="p-6 pt-8 flex items-center mb-6">
        <Link href="/" className="flex items-center space-x-3 group">
          <Image
            src="/yukti-logo-transparent.png"
            alt="YuktiFi Logo"
            width={64}
            height={64}
            className="object-contain -mt-1 transition-transform group-hover:scale-105 drop-shadow-[0_2px_4px_rgba(0,0,0,0.15)]"
            priority
          />
          <div className="flex flex-col justify-center">
            <span className="font-display font-bold text-4xl text-forest-deep tracking-tight leading-none group-hover:text-[#ea580c] transition-colors">YuktiFi</span>
            <span className="text-xs font-bold text-ink-soft uppercase tracking-[0.2em] mt-1">Government of India Initiative</span>
          </div>
        </Link>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-4 py-2 custom-scrollbar">
        {userMode === 'entrepreneur' ? (
          <>
            <NavLink href="/dashboard" icon={LayoutDashboard} label={t('dashboard')} isActive={pathname === '/dashboard'} />
            <NavLink href="/discover" icon={Search} label={t('discover')} isActive={pathname === '/discover'} />
            <NavLink href={`/market-intelligence/${categoryId || 'demo'}`} icon={BarChart3} label={t('marketIntelligence')} isActive={pathname.includes('/market-intelligence')} />
            <NavLink href="/financials" className="text-sm" icon={Calculator} label={t('financials')} isActive={pathname === '/financials'} />
            <NavLink href="/score/demo" icon={Target} label={t('score')} isActive={pathname.includes('/score')} />
            <NavLink href="/simulator" icon={Activity} label={t('simulator')} isActive={pathname === '/simulator'} />
            <NavLink href="/plans" icon={FileText} label={t('plans')} isActive={pathname === '/plans'} />
            <NavLink href="/action-plan" icon={CheckSquare} label={t('actionPlan')} isActive={pathname === '/action-plan'} />
            <NavLink href="/documents" icon={Folder} label={t('documents')} isActive={pathname === '/documents'} />
            <NavLink href="/ask" icon={HelpCircle} label={t('ask')} isActive={pathname === '/ask'} />
          </>
        ) : (
          <>
            <NavLink href="/advisor/analytics" icon={BarChart} label={t('analytics')} isActive={pathname === '/advisor/analytics'} />
            <NavLink href="/advisor/applications" icon={ListOrdered} label={t('reviewQueue')} isActive={pathname === '/advisor/applications'} />
            <NavLink href="/advisor/reports" icon={FileArchive} label={t('regionalReports')} isActive={pathname === '/advisor/reports'} />
          </>
        )}
      </nav>

      {/* Footer */}
      <div className="p-4 mt-auto">
        <LanguageSwitcher />

        <div className="flex items-center px-3 py-2">
          <div className="w-10 h-10 rounded-full bg-[#fde68a] mr-3 overflow-hidden border border-premium-border flex items-center justify-center shrink-0">
            <User size={20} className="text-[#b45309]" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold text-ink">{profileName}</span>
            <div className="flex text-xs font-medium text-ink-soft mt-0.5 space-x-1">
              <Link href="/profile" className="hover:text-ink">Profile</Link>
              <span>·</span>
              <Link href="/settings" className="hover:text-ink">Settings</Link>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
