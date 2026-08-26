import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Leaf, ShieldCheck, LogIn } from 'lucide-react';
import { useDemoAuth } from '../auth/DemoAuthContext';

const ROLES = ['AYUSH Clinician', 'Terminology Reviewer', 'System Administrator'];

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
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-main)', padding: 20,
    }}>
      <div className="card" style={{ width: '100%', maxWidth: 420 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <div className="sidebar-logo-icon"><Leaf size={20} /></div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>NAMASTE × ICD-11</div>
            <div style={{ fontSize: 10.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em' }}>
              Traditional Medicine Interoperability
            </div>
          </div>
        </div>

        <div className="demo-banner" style={{ margin: '14px 0', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
          <ShieldCheck size={16} style={{ flexShrink: 0, marginTop: 1 }} />
          <div>
            <strong>ABHA Demo Mode:</strong> this is not real ABHA OAuth2. No password is checked — enter
            any name to get a real, signed session token that gates write actions in this app
            (governance decisions, FHIR Bundle upload) exactly like a production auth layer would.
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
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
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
              Role
            </label>
            <select className="select" style={{ width: '100%' }} value={role} onChange={(e) => setRole(e.target.value)}>
              {ROLES.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          {error && (
            <div style={{ fontSize: 12.5, color: 'var(--danger)', marginBottom: 12 }}>{error}</div>
          )}

          <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
            <LogIn size={15} /> {loading ? 'Signing in…' : 'Continue (ABHA Demo)'}
          </button>
        </form>
      </div>
    </div>
  );
}
