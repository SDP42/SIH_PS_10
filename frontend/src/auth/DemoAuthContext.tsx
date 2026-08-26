import React, { createContext, useContext, useEffect, useState } from 'react';
import { demoLogin, type DemoAuthSession } from '../api';
import { DEMO_AUTH_STORAGE_KEY } from '../api/client';

interface DemoAuthState {
  session: DemoAuthSession | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (name: string, role: string) => Promise<void>;
  logout: () => void;
}

const DemoAuthContext = createContext<DemoAuthState | undefined>(undefined);

function loadStoredSession(): DemoAuthSession | null {
  const raw = localStorage.getItem(DEMO_AUTH_STORAGE_KEY);
  if (!raw) return null;
  try {
    const session: DemoAuthSession = JSON.parse(raw);
    // Tokens are short-lived (4h) — a stale session past its issued time is
    // still sent to the backend, which will 401 and the app should re-prompt.
    return session;
  } catch {
    return null;
  }
}

export function DemoAuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<DemoAuthSession | null>(() => loadStoredSession());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (session) {
      localStorage.setItem(DEMO_AUTH_STORAGE_KEY, JSON.stringify(session));
    } else {
      localStorage.removeItem(DEMO_AUTH_STORAGE_KEY);
    }
  }, [session]);

  async function login(name: string, role: string) {
    setLoading(true);
    try {
      const result = await demoLogin(name, role);
      setSession(result);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    setSession(null);
  }

  return (
    <DemoAuthContext.Provider value={{ session, isAuthenticated: !!session, loading, login, logout }}>
      {children}
    </DemoAuthContext.Provider>
  );
}

export function useDemoAuth(): DemoAuthState {
  const ctx = useContext(DemoAuthContext);
  if (!ctx) throw new Error('useDemoAuth must be used within DemoAuthProvider');
  return ctx;
}
