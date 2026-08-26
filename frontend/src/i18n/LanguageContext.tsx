import React, { createContext, useContext, useMemo, useState } from 'react';
import { type LanguageCode, translate } from './translations';

const STORAGE_KEY = 'namaste_icd11_language';

interface LanguageContextValue {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextValue | undefined>(undefined);

function readStoredLanguage(): LanguageCode {
  if (typeof window === 'undefined') return 'en';
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return (stored === 'en' || stored === 'hi' || stored === 'mr' || stored === 'gu') ? stored : 'en';
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<LanguageCode>(readStoredLanguage);

  function setLanguage(lang: LanguageCode) {
    setLanguageState(lang);
    window.localStorage.setItem(STORAGE_KEY, lang);
  }

  const value = useMemo<LanguageContextValue>(() => ({
    language,
    setLanguage,
    t: (key: string) => translate(key, language),
  }), [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within a LanguageProvider');
  return ctx;
}
