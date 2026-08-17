import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Search, GitMerge, Star, Users, Activity,
  RefreshCw, Shield, Settings, Leaf
} from 'lucide-react';

const NAV = [
  { to: '/overview', icon: LayoutDashboard, label: 'Overview' },
  { to: '/terminology', icon: Search, label: 'Terminology Explorer' },
  { to: '/mapping', icon: GitMerge, label: 'Mapping Intelligence' },
  { to: '/fhir', icon: Activity, label: 'FHIR Workspace' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function AppShell() {
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
            <span className="status-dot" />
            <span>Platform Operational</span>
          </div>
          <div className="sidebar-status">
            <span className="status-dot syncing" />
            <span>Terminology Sync (Demo)</span>
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
              <div className="header-user-name">Dr. Ananya Mehta</div>
              <div className="header-user-role">AYUSH Terminology Expert</div>
            </div>
            <div className="header-avatar">AM</div>
          </div>
        </header>

        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
