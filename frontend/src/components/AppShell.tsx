import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard, Search, GitMerge, Activity,
  Settings, Leaf, Sparkles, ClipboardCheck, LogOut, Globe, BarChart3
} from 'lucide-react';
import { getStats } from '../api';
import { useDemoAuth } from '../auth/DemoAuthContext';

const NAV = [
  { to: '/overview', icon: LayoutDashboard, label: 'Overview' },
  { to: '/terminology', icon: Search, label: 'Terminology Explorer' },
  { to: '/mapping', icon: GitMerge, label: 'Mapping Intelligence' },
  { to: '/ai-lab', icon: Sparkles, label: 'AI Mapping Lab' },
  { to: '/review-queue', icon: ClipboardCheck, label: 'Expert Review' },
  { to: '/fhir', icon: Activity, label: 'FHIR Workspace' },
  { to: '/who-sync', icon: Globe, label: 'WHO Sync' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function AppShell() {
  const navigate = useNavigate();
  const { session, logout } = useDemoAuth();

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
            <div className="sidebar-logo-sub">Interoperability Platform</div>
          </div>
          <span className="sidebar-badge">β4</span>
        </div>

        <nav className="sidebar-nav">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-status">
            <span className={`status-dot${backendDown ? ' syncing' : ''}`} />
            <span>{backendDown ? 'Backend Unreachable' : backendUp ? 'Backend Connected' : 'Checking…'}</span>
          </div>
          <div className="sidebar-status">
            <span className="status-dot syncing" />
            <span>ABHA Demo Mode Auth</span>
          </div>
          <div className="sidebar-status">
            <span className="status-dot" />
            <span>FHIR R4 Gateway Ready</span>
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
            <div className="header-user">
              <div className="header-user-name">{session?.identity.name || 'Unknown'}</div>
              <div className="header-user-role">{session?.identity.role || ''}</div>
            </div>
            <div className="header-avatar" title="Log out" onClick={handleLogout} style={{ cursor: 'pointer' }}>
              {initials || <LogOut size={14} />}
            </div>
          </div>
        </header>

        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
