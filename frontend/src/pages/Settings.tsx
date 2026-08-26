import { useQuery } from '@tanstack/react-query';
import { getStats, getTerminologies } from '../api';
import { User, Database, Key, Globe, ShieldCheck } from 'lucide-react';
import { useDemoAuth } from '../auth/DemoAuthContext';

export default function Settings() {
  const { data: stats } = useQuery({ queryKey: ['stats'], queryFn: getStats });
  const { data: terms } = useQuery({ queryKey: ['terminologies'], queryFn: getTerminologies });
  const { session, logout } = useDemoAuth();

  const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const expiresAt = session ? new Date(Date.now() + session.expires_in * 1000) : null;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-desc">Platform configuration and system information.</p>
      </div>

      <div style={{ display: 'grid', gap: 16, maxWidth: 720 }}>
        {/* Profile — real demo-session identity, not a hardcoded fake user */}
        <div className="card">
          <div className="section-header"><div className="section-title"><User size={15} style={{display:'inline',marginRight:8}} />Profile</div></div>
          {[
            { label: 'Name', value: session?.identity.name || '—' },
            { label: 'Role', value: session?.identity.role || '—' },
          ].map(f => (
            <div key={f.label} style={{ display: 'flex', padding: '10px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
              <div style={{ width: 160, color: 'var(--text-muted)', fontWeight: 500 }}>{f.label}</div>
              <div style={{ color: 'var(--text-primary)' }}>{f.value}</div>
            </div>
          ))}
        </div>

        {/* Authentication (ABHA Demo Mode) */}
        <div className="card">
          <div className="section-header"><div className="section-title"><ShieldCheck size={15} style={{display:'inline',marginRight:8}} />Authentication (ABHA Demo Mode)</div></div>
          <div style={{ display: 'flex', padding: '10px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
            <div style={{ width: 160, color: 'var(--text-muted)' }}>Mode</div>
            <div style={{ color: 'var(--text-primary)' }}>{session?.mode || '—'} <span style={{ color: 'var(--text-muted)', fontSize: 11.5 }}>(not real ABHA OAuth2)</span></div>
          </div>
          <div style={{ display: 'flex', padding: '10px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
            <div style={{ width: 160, color: 'var(--text-muted)' }}>Token expires (approx.)</div>
            <div style={{ color: 'var(--text-primary)' }}>{expiresAt ? expiresAt.toLocaleTimeString() : '—'}</div>
          </div>
          <div style={{ padding: '10px 0', fontSize: 12, color: 'var(--text-muted)' }}>{session?.disclaimer}</div>
          <button className="btn btn-outline btn-sm" onClick={logout} style={{ marginTop: 8 }}>Log out</button>
        </div>

        {/* API Config */}
        <div className="card">
          <div className="section-header"><div className="section-title"><Key size={15} style={{display:'inline',marginRight:8}} />API Configuration</div></div>
          <div style={{ display: 'flex', padding: '10px 0', borderBottom: '1px solid var(--border)', fontSize: 13, alignItems: 'center' }}>
            <div style={{ width: 160, color: 'var(--text-muted)' }}>Backend URL</div>
            <code style={{ background: 'var(--bg-input)', padding: '3px 10px', borderRadius: 4, fontSize: 12, color: 'var(--accent)', border: '1px solid var(--border)' }}>{apiBase}</code>
          </div>
          <div style={{ display: 'flex', padding: '10px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
            <div style={{ width: 160, color: 'var(--text-muted)' }}>API Version</div>
            <div style={{ color: 'var(--text-primary)' }}>0.1.0</div>
          </div>
          <div style={{ display: 'flex', padding: '10px 0', fontSize: 13 }}>
            <div style={{ width: 160, color: 'var(--text-muted)' }}>FHIR Standard</div>
            <div style={{ color: 'var(--text-primary)' }}>R4 / ConceptMap</div>
          </div>
        </div>

        {/* Terminology Systems */}
        <div className="card">
          <div className="section-header"><div className="section-title"><Database size={15} style={{display:'inline',marginRight:8}} />Connected Terminology Systems</div></div>
          {terms?.map(t => (
            <div key={t.id} style={{ display: 'flex', padding: '12px 0', borderBottom: '1px solid var(--border)', fontSize: 13, alignItems: 'center', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, marginBottom: 2 }}>{t.name} — {t.full_name}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 11.5 }}>{t.source} · {t.version}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span className="badge badge-active">{t.status}</span>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{t.concept_count?.toLocaleString()} concepts</div>
              </div>
            </div>
          ))}
        </div>

        {/* Stats summary */}
        {stats && (
          <div className="card">
            <div className="section-header"><div className="section-title"><Globe size={15} style={{display:'inline',marginRight:8}} />Database Summary</div></div>
            {[
              { label: 'Total Mappings', value: stats.total_mappings.toLocaleString() },
              { label: 'Equivalent Mappings', value: stats.validated_mappings.toLocaleString() },
              { label: 'Related Mappings', value: stats.related_mappings.toLocaleString() },
              { label: 'NAMASTE Codes Covered', value: stats.mapped_namaste_codes.toLocaleString() },
              { label: 'ICD-11 Codes Targeted', value: stats.mapped_icd11_codes.toLocaleString() },
            ].map(f => (
              <div key={f.label} style={{ display: 'flex', padding: '8px 0', borderBottom: '1px solid rgba(30,58,82,.4)', fontSize: 13 }}>
                <div style={{ flex: 1, color: 'var(--text-muted)' }}>{f.label}</div>
                <div style={{ fontWeight: 600, color: 'var(--accent)' }}>{f.value}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
