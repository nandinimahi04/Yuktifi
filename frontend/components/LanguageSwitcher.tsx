"use client";

import { useLocale } from 'next-intl';
import { useRouter, usePathname } from '@/routing';
import { Button } from '@/components/ui/button';
import { Languages } from 'lucide-react';

export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const toggleLanguage = () => {
    const nextLocale = locale === 'en' ? 'hi' : 'en';
    router.replace(pathname, { locale: nextLocale });
  };

  return (
    <Button 
      variant="ghost" 
      onClick={toggleLanguage}
      className="flex items-center gap-2 text-ink hover:text-warm-primary transition-colors"
    >
      <Languages size={18} />
      <span className="font-semibold text-sm">
        {locale === 'en' ? 'हिन्दी' : 'English'}
      </span>
    </Button>
  );
}
