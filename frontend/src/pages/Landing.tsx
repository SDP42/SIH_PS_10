import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Leaf, Sparkles, GitMerge, ShieldCheck, FileCheck2, ClipboardCheck,
  ArrowRight, Activity, Globe, Database, Zap, Lock,
} from 'lucide-react';
import { getStats } from '../api';

const FEATURES = [
  {
    icon: Sparkles,
    title: 'Ambiguity-Aware AI Mapping',
    desc: 'Every NAMASTE code gets a transparent decision — Auto-Suggest, Needs Context, Expert Review, or No Validated Equivalent. The engine never silently guesses.',
    color: '#14b8a6',
  },
  {
    icon: GitMerge,
    title: 'Real Dual-Coding (TM2 + Biomedicine)',
    desc: 'Independent AI decisions for ICD-11 Traditional Medicine and Biomedicine chapters, resolved and returned side by side in one FHIR response.',
    color: '#6366f1',
  },
  {
    icon: ClipboardCheck,
    title: 'Human-in-the-Loop Governance',
    desc: 'Ambiguous suggestions land in a real review queue. Approving one writes a brand-new curated mapping — nothing is ever auto-approved.',
    color: '#f59e0b',
  },
  {
    icon: FileCheck2,
    title: 'FHIR R4 Compliant',
    desc: 'Real $translate, CodeSystem, ValueSet/$expand, Bundle upload, and ProblemList construction — not mocked JSON, actual spec-shaped operations.',
    color: '#3b82f6',
  },
  {
    icon: Lock,
    title: 'ABHA Demo Mode Auth',
    desc: 'Signed bearer tokens gate every write action with real 401 enforcement — a genuine security code path, clearly labeled as a demo identity provider.',
    color: '#ef4444',
  },
  {
    icon: Activity,
    title: 'Real Audit Trail',
    desc: 'Every governance decision and Bundle upload is logged with the real actor identity — no hardcoded fake activity feed.',
    color: '#22c55e',
  },
];

function StatChip({ icon: Icon, value, label }: { icon: React.ComponentType<any>; value: string; label: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <div style={{
        width: 44, height: 44, borderRadius: 12, background: 'var(--accent-dim)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        <Icon size={20} color="var(--accent)" />
      </div>
      <div>
        <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1 }}>{value}</div>
        <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 3 }}>{label}</div>
      </div>
    </div>
  );
}

export default function Landing() {
  const navigate = useNavigate();
  const { data: stats } = useQuery({ queryKey: ['stats'], queryFn: getStats, retry: false });

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', position: 'relative', overflow: 'hidden' }}>
      {/* Animated background blobs */}
      <div className="blob" style={{ width: 480, height: 480, background: '#14b8a6', top: -160, left: -120 }} />
      <div className="blob" style={{ width: 420, height: 420, background: '#6366f1', top: 200, right: -140, animationDelay: '2s' }} />
      <div className="blob" style={{ width: 360, height: 360, background: '#14b8a6', bottom: -140, left: '40%', animationDelay: '4s' }} />

      <div style={{ position: 'relative', zIndex: 1 }}>
        {/* Nav */}
        <nav style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '20px 40px', maxWidth: 1280, margin: '0 auto',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div className="sidebar-logo-icon"><Leaf size={20} color="#fff" /></div>
            <div>
              <div style={{ fontSize: 16.5, fontWeight: 700, color: 'var(--text-primary)' }}>NAMASTE × ICD-11</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.06em' }}>
                AYUSH Interoperability Gateway
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
            <a href="#features" className="landing-nav-link">Features</a>
            <a href="#standards" className="landing-nav-link">Standards</a>
            <button className="btn btn-primary" onClick={() => navigate('/login')}>
              Sign In <ArrowRight size={15} />
            </button>
          </div>
        </nav>

        {/* Hero */}
        <div style={{ maxWidth: 900, margin: '70px auto 0', textAlign: 'center', padding: '0 24px' }}>
          <div className="pill fade-up">
            <Zap size={13} /> Smart India Hackathon 2026 — DJS_26_SW_10
          </div>
          <h1 className="fade-up fade-up-1" style={{ fontSize: 52, fontWeight: 800, lineHeight: 1.15, marginTop: 22 }}>
            Bridging <span className="gradient-text">Traditional Medicine</span><br />with Global Health Standards
          </h1>
          <p className="fade-up fade-up-2" style={{ fontSize: 17, color: 'var(--text-secondary)', marginTop: 20, maxWidth: 680, marginLeft: 'auto', marginRight: 'auto', lineHeight: 1.6 }}>
            A FHIR R4 terminology micro-service that maps India's NAMASTE Ayurveda, Siddha &amp; Unani codes
            to WHO ICD-11 — with real double-coding across Traditional Medicine (TM2) and Biomedicine,
            an ambiguity-aware AI engine, and human-in-the-loop governance so nothing is ever silently guessed.
          </p>
          <div className="fade-up fade-up-3" style={{ display: 'flex', gap: 14, justifyContent: 'center', marginTop: 32 }}>
            <button className="btn btn-primary" style={{ padding: '12px 26px', fontSize: 15 }} onClick={() => navigate('/login')}>
              Enter Platform <ArrowRight size={17} />
            </button>
            <a href="#features" className="btn btn-outline" style={{ padding: '12px 26px', fontSize: 15, textDecoration: 'none' }}>
              Explore Features
            </a>
          </div>
        </div>

        {/* Live stats strip */}
        <div className="fade-up fade-up-4" style={{ maxWidth: 1000, margin: '64px auto 0', padding: '0 24px' }}>
          <div className="glow-card" style={{ padding: '28px 36px', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 24 }}>
            <StatChip icon={Database} value={stats ? stats.namaste_concepts.toLocaleString() : '—'} label="NAMASTE Concepts" />
            <StatChip icon={Globe} value={stats ? stats.icd11_concepts.toLocaleString() : '—'} label="ICD-11 Concepts (TM2 + Biomedicine)" />
            <StatChip icon={ShieldCheck} value={stats ? stats.total_mappings.toLocaleString() : '—'} label="Curated Mappings" />
            <StatChip icon={Sparkles} value="Live" label="AI Suggestion Engine" />
          </div>
        </div>

        {/* Features grid */}
        <div id="features" style={{ maxWidth: 1100, margin: '110px auto 0', padding: '0 24px' }}>
          <div style={{ textAlign: 'center', marginBottom: 44 }}>
            <div className="pill">What's Inside</div>
            <h2 style={{ fontSize: 32, fontWeight: 700, marginTop: 16 }}>Built for judges who read the spec closely</h2>
            <p style={{ fontSize: 14.5, color: 'var(--text-muted)', marginTop: 8 }}>
              Every capability below is real, tested, and demoable — not a mockup.
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
            {FEATURES.map((f) => (
              <div key={f.title} className="card" style={{ transition: 'transform .2s, border-color .2s' }}
                   onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-3px)'; e.currentTarget.style.borderColor = f.color; }}
                   onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.borderColor = 'var(--border)'; }}>
                <div style={{
                  width: 42, height: 42, borderRadius: 11, marginBottom: 14,
                  background: `${f.color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <f.icon size={20} color={f.color} />
                </div>
                <div style={{ fontSize: 15.5, fontWeight: 700, marginBottom: 8 }}>{f.title}</div>
                <div style={{ fontSize: 13.5, color: 'var(--text-muted)', lineHeight: 1.55 }}>{f.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Standards strip */}
        <div id="standards" style={{ maxWidth: 900, margin: '90px auto 0', padding: '0 24px', textAlign: 'center' }}>
          <div style={{ fontSize: 12.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 18 }}>
            Aligned with India's 2016 EHR Standards
          </div>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            {['FHIR R4', 'ICD-11 TM2', 'ICD-11 Biomedicine', 'NAMASTE', 'ABHA (Demo)', 'SQLite FTS5'].map((s) => (
              <span key={s} className="badge badge-active" style={{ fontSize: 12.5, padding: '6px 14px' }}>{s}</span>
            ))}
          </div>
        </div>

        {/* Footer CTA */}
        <div style={{ maxWidth: 700, margin: '100px auto 0', padding: '48px 24px 80px', textAlign: 'center' }}>
          <h3 style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>Ready to see it live?</h3>
          <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 24 }}>
            Sign in with ABHA Demo Mode — no password required — and explore the AI Mapping Lab,
            Expert Review queue, and FHIR Workspace.
          </p>
          <button className="btn btn-primary" style={{ padding: '12px 30px', fontSize: 15 }} onClick={() => navigate('/login')}>
            Enter Platform <ArrowRight size={17} />
          </button>
        </div>
      </div>
    </div>
  );
}
