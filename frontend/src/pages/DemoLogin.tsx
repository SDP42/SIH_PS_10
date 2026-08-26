import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Leaf, ShieldCheck, LogIn, Sparkles, GitMerge, ClipboardCheck } from 'lucide-react';
import { useDemoAuth } from '../auth/DemoAuthContext';

const ROLES = ['AYUSH Clinician', 'Terminology Reviewer', 'System Administrator'];

const HERO_POINTS = [
  { icon: Sparkles, text: 'Ambiguity-aware AI suggestions for every unmapped NAMASTE code' },
  { icon: GitMerge, text: 'Real double-coding across ICD-11 TM2 and Biomedicine' },
  { icon: ClipboardCheck, text: 'Human-in-the-loop governance — nothing auto-approved' },
];

export default function DemoLogin() {
  const { login, loading } = useDemoAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [role, setRole] = useState(ROLES[0]);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError('Enter a name to continue.');
      return;
    }
    setError(null);
    try {
      await login(name.trim(), role);
      navigate('/overview', { replace: true });
    } catch {
      setError('Could not reach the backend. Is it running at the configured API base URL?');
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '1.1fr 1fr', background: 'var(--bg-main)' }}>
      {/* Left: brand hero panel */}
      <div style={{
        position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column',
        justifyContent: 'space-between', padding: '48px 56px', background: 'var(--sidebar-bg)',
      }}>
        <div className="blob" style={{ width: 380, height: 380, background: '#14b8a6', top: -100, left: -100 }} />
        <div className="blob" style={{ width: 320, height: 320, background: '#6366f1', bottom: -80, right: -80, animationDelay: '3s' }} />

        <div style={{ position: 'relative', zIndex: 1 }}>
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
            <div className="sidebar-logo-icon"><Leaf size={20} color="#fff" /></div>
            <div>
              <div style={{ fontSize: 16.5, fontWeight: 700, color: 'var(--text-primary)' }}>NAMASTE × ICD-11</div>
              <div style={{ fontSize: 10, color: 'var(--sidebar-text)', textTransform: 'uppercase', letterSpacing: '.06em' }}>
                AYUSH Interoperability Gateway
              </div>
            </div>
          </Link>
        </div>

        <div style={{ position: 'relative', zIndex: 1 }}>
          <h1 style={{ fontSize: 34, fontWeight: 800, lineHeight: 1.25, color: 'var(--text-primary)', marginBottom: 28 }}>
            Where traditional medicine<br /> meets <span className="gradient-text">global standards</span>.
          </h1>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {HERO_POINTS.map((p) => (
              <div key={p.text} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{
                  width: 34, height: 34, borderRadius: 9, background: 'var(--accent-dim)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <p.icon size={16} color="var(--accent)" />
                </div>
                <div style={{ fontSize: 14, color: 'var(--sidebar-text-active)' }}>{p.text}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ position: 'relative', zIndex: 1, fontSize: 11.5, color: 'var(--sidebar-text)' }}>
          Smart India Hackathon 2026 · DJS_26_SW_10
        </div>
      </div>

      {/* Right: login form */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32 }}>
        <div style={{ width: '100%', maxWidth: 400 }}>
          <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 6 }}>Welcome back</h2>
          <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 24 }}>Sign in to continue to the gateway.</p>

          <div className="demo-banner" style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
            <ShieldCheck size={16} style={{ flexShrink: 0, marginTop: 1 }} />
            <div>
              <strong>ABHA Demo Mode:</strong> not real ABHA OAuth2. No password is checked — enter
              any name to get a real, signed session token that gates write actions in this app
              (governance decisions, FHIR Bundle upload) exactly like a production auth layer would.
            </div>
          </div>

          <form onSubmit={handleSubmit} style={{ marginTop: 20 }}>
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                Name
              </label>
              <input
                className="input"
                style={{ width: '100%' }}
                placeholder="Dr. Your Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>
            <div style={{ marginBottom: 18 }}>
              <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                Role
              </label>
              <select className="select" style={{ width: '100%' }} value={role} onChange={(e) => setRole(e.target.value)}>
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>

            {error && (
              <div style={{ fontSize: 13, color: 'var(--danger)', marginBottom: 14 }}>{error}</div>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '11px 0' }} disabled={loading}>
              <LogIn size={16} /> {loading ? 'Signing in…' : 'Continue (ABHA Demo)'}
            </button>
          </form>

          <div style={{ marginTop: 20, textAlign: 'center' }}>
            <Link to="/" style={{ fontSize: 12.5, color: 'var(--text-muted)', textDecoration: 'none' }}>← Back to home</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
