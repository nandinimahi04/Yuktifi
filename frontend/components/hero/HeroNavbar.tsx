import React, { useState } from 'react';
import Link from 'next/link';
import { Menu, X, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';

export function HeroNavbar({ onGetStarted }: { onGetStarted: () => void }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const t = useTranslations('Navbar');

  const getDesktopLinkClass = (path: string) => {
    const isActive = pathname === path;
    return `font-medium text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron rounded ${
      isActive ? 'text-saffron font-bold' : 'text-ink-soft hover:text-ink'
    }`;
  };

  const getMobileLinkClass = (path: string) => {
    const isActive = pathname === path;
    return `block px-3 py-3 rounded-md text-base ${
      isActive ? 'font-bold text-saffron' : 'font-medium text-ink hover:bg-cream'
    }`;
  };

  return (
    <nav className="w-full absolute top-0 left-0 z-50 bg-white/95 backdrop-blur-md shadow-sm border-b border-premium-border/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-20">
          
          {/* Logo with Framer Motion Effects */}
          <Link href="/" className="flex-shrink-0 flex items-center group relative">
            <motion.div 
              className="absolute -inset-2 bg-gradient-to-r from-[#ea580c]/30 to-[#f97316]/30 rounded-full blur-xl opacity-0 transition-opacity duration-500 group-hover:opacity-100"
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ repeat: Infinity, duration: 3 }}
            />
            <motion.img
              src="/yukti-logo-transparent.png"
              alt="YuktiFi Logo"
              className="h-16 w-16 object-contain -mt-1 mr-3 relative z-10 drop-shadow-md"
              whileHover={{ 
                rotate: [0, -8, 8, -4, 0],
                scale: 1.05,
              }}
              transition={{ duration: 0.5, ease: "easeInOut" }}
            />
            <div className="flex flex-col justify-center relative z-10">
              <span className="font-display font-bold text-4xl text-forest-deep tracking-tight leading-none group-hover:text-[#ea580c] transition-colors duration-300">YuktiFi</span>
              <span className="text-xs font-bold text-ink-soft uppercase tracking-[0.2em] mt-1 group-hover:text-[#ea580c]/80 transition-colors duration-300">Initiative by Government of India</span>
            </div>
          </Link>

          {/* Desktop Center Nav */}
          <div className="hidden md:flex space-x-8">
            <Link href="/" className={getDesktopLinkClass('/')}>Home</Link>
            <Link href="/how-it-works" className={getDesktopLinkClass('/how-it-works')}>How It Works</Link>
            <Link href="/about" className={getDesktopLinkClass('/about')}>About</Link>
            <Link href="/support" className={getDesktopLinkClass('/support')}>Support</Link>
          </div>

          {/* Desktop Right Nav */}
          <div className="hidden md:flex items-center space-x-4">
            <LanguageSwitcher />
            
            <button 
              onClick={onGetStarted}
              className="bg-[#f97316] hover:bg-[#ea580c] text-white px-6 py-2.5 rounded-lg text-sm font-bold flex items-center shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-saffron"
            >
              {t('login')}
            </button>
          </div>

          {/* Mobile menu button */}
          <div className="flex md:hidden items-center">
            <button 
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="text-ink-soft hover:text-ink p-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron rounded-md"
              aria-expanded={isMobileMenuOpen}
            >
              <span className="sr-only">Open main menu</span>
              {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
            className="md:hidden absolute top-24 left-4 right-4 bg-white rounded-2xl border border-premium-border shadow-card z-40"
          >
            <div className="px-4 pt-2 pb-6 space-y-2 flex flex-col">
              <Link href="/" onClick={() => setIsMobileMenuOpen(false)} className={getMobileLinkClass('/')}>Home</Link>
              <Link href="/how-it-works" onClick={() => setIsMobileMenuOpen(false)} className={getMobileLinkClass('/how-it-works')}>How It Works</Link>
              <Link href="/about" onClick={() => setIsMobileMenuOpen(false)} className={getMobileLinkClass('/about')}>About</Link>
              <Link href="/support" onClick={() => setIsMobileMenuOpen(false)} className={getMobileLinkClass('/support')}>Support</Link>
              
              <div className="pt-4 mt-2 border-t border-premium-border-strong flex justify-between items-center px-3">
                <LanguageSwitcher />
                <button 
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    onGetStarted();
                  }}
                  className="bg-[#f97316] text-white px-5 py-2.5 rounded-lg text-sm font-bold flex items-center shadow-sm"
                >
                  {t('login')}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
