import { getRequestConfig } from 'next-intl/server';
import enMessages from './messages/en.json';
import hiMessages from './messages/hi.json';

const messages: Record<string, any> = {
  en: enMessages,
  hi: hiMessages,
};

export default getRequestConfig(async ({ requestLocale }) => {
  let locale = await requestLocale;
  if (!locale || !['en', 'hi'].includes(locale as string)) {
    locale = 'en';
  }

  return {
    locale: locale as string,
    messages: messages[locale] || enMessages
  };
});

