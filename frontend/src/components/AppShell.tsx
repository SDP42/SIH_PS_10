import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard, Search, GitMerge, Activity,
  Settings, Leaf, Sparkles, ClipboardCheck, LogOut, Globe, BarChart3, MessageSquareText, KeyRound, FlaskConical, GitCompareArrows, ShieldAlert
} from 'lucide-react';
import { getStats } from '../api';
import { useDemoAuth } from '../auth/DemoAuthContext';
import { useLanguage } from '../i18n/LanguageContext';
import LanguageSwitcher from './LanguageSwitcher';
import VoiceAssistant from './VoiceAssistant';

const NAV = [
  { to: '/overview', icon: LayoutDashboard, key: 'nav_overview' },
  { to: '/terminology', icon: Search, key: 'nav_terminology' },
  { to: '/mapping', icon: GitMerge, key: 'nav_mapping' },
  { to: '/ai-lab', icon: Sparkles, key: 'nav_ai_lab' },
  { to: '/clinical-text', icon: MessageSquareText, key: 'nav_clinical_text' },
  { to: '/review-queue', icon: ClipboardCheck, key: 'nav_review_queue' },
  { to: '/fhir', icon: Activity, key: 'nav_fhir' },
  { to: '/who-sync', icon: Globe, key: 'nav_who_sync' },
  { to: '/what-if-simulator', icon: GitCompareArrows, key: 'nav_what_if' },
  { to: '/terminology-firewall', icon: ShieldAlert, key: 'nav_firewall' },
  { to: '/analytics', icon: BarChart3, key: 'nav_analytics' },
  { to: '/population-demo', icon: FlaskConical, key: 'nav_population_demo' },
  { to: '/developer-portal', icon: KeyRound, key: 'nav_developer_portal' },
  { to: '/settings', icon: Settings, key: 'nav_settings' },
];

export default function AppShell() {
  const navigate = useNavigate();
  const { session, logout } = useDemoAuth();
  const { t } = useLanguage();

  // Real backend liveness check (not a hardcoded "Operational" dot) — any
  // successful real endpoint call proves the API is actually reachable.
  const { isSuccess: backendUp, isError: backendDown } = useQuery({
    queryKey: ['backend-health'],
    queryFn: getStats,
    refetchInterval: 30000,
    retry: 1,
  });

  const initials = (session?.identity.name || '?')
    .split(' ')
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon"><Leaf size={20} /></div>
          <div>
            <div className="sidebar-logo-text">AYUSH Nexus</div>
            <div className="sidebar-logo-sub">{t('sidebar_subtitle')}</div>
          </div>
          <span className="sidebar-badge">β4</span>
        </div>

        <nav className="sidebar-nav">
          {NAV.map(({ to, icon: Icon, key }) => (
            <NavLink key={to} to={to} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
              <Icon size={16} />
              <span>{t(key)}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-status">
            <span className={`status-dot${backendDown ? ' syncing' : ''}`} />
            <span>{backendDown ? t('status_backend_unreachable') : backendUp ? t('status_backend_connected') : t('status_checking')}</span>
          </div>
          <div className="sidebar-status">
            <span className="status-dot syncing" />
            <span>{t('status_abha_demo')}</span>
          </div>
          <div className="sidebar-status">
            <span className="status-dot" />
            <span>{t('status_fhir_ready')}</span>
          </div>
        </div>
      </aside>

      <div className="main-content">
        <header className="top-header">
          <div className="header-search">
            <svg className="header-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
            <input placeholder="Search across gateway registry…" />
          </div>
          <div className="header-right">
            <div className="header-context">
              <strong>NAMASTE v1.2</strong> / ICD-11 TM2 v2022.1
            </div>
            <LanguageSwitcher />
            <div className="header-user">
              <div className="header-user-name">{session?.identity.name || 'Unknown'}</div>
              <div className="header-user-role">{session?.identity.role || ''}</div>
            </div>
            <div className="header-avatar" title={t('action_log_out')} onClick={handleLogout} style={{ cursor: 'pointer' }}>
              {initials || <LogOut size={14} />}
            </div>
          </div>
        </header>

        <main className="page-content">
          <Outlet />
        </main>
      </div>

      {/* Floating on every page — voice and text are two inputs to one engine */}
      <VoiceAssistant />
    </div>
  );
}
