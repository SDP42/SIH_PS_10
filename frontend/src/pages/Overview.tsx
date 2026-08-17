import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getStats, getTerminologies } from '../api';
import { BookOpen, GitMerge, CheckCircle, Clock, RefreshCw, Activity } from 'lucide-react';

function StatCard({ label, value, sub, icon: Icon, iconColor = 'var(--accent)' }: {
  label: string; value: string | number; sub?: string;
  icon: React.ComponentType<any>; iconColor?: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-card-label">
        <Icon size={13} color={iconColor} />
        {label}
      </div>
      <div className="stat-card-value">{value}</div>
      {sub && <div className="stat-card-sub">{sub}</div>}
    </div>
  );
}

const AUDIT_EVENTS = [
  { time: '2026-08-16 12:15 PM', action: 'CREATE_MAPPING_PROPOSAL', detail: 'Proposed: Amapita → Gastro-oesophageal reflux disease (61% confidence)', user: 'AI Semantic Engine' },
  { time: '2026-08-16 11:53 AM', action: 'VALIDATE_MAPPING', detail: 'Confirmed: Cereva equivalent status', user: 'Dr. Satheeshtha K. (Siddha Panel)' },
  { time: '2026-08-16 09:30 AM', action: 'SYNC_NAMASTE_REGISTRY', detail: 'Downloaded patch v1.2.00; Imported 4 new traditional Siddha terms', user: 'Cron Job: SyncWorker_01' },
  { time: '2026-08-04 03:00 PM', action: 'GENERATE_FHIR_CONCEPTMAP', detail: 'Compiled 468 validated mappings into FHIR R4 JSON ConceptMap Resource', user: 'FHIR Converter service' },
];

export default function Overview() {
  const { data: stats, isLoading: statsLoading } = useQuery({ queryKey: ['stats'], queryFn: getStats });
  const { data: terminologies, isLoading: termsLoading } = useQuery({ queryKey: ['terminologies'], queryFn: getTerminologies });

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">AYUSH Interoperability Gateway</h1>
        <p className="page-desc">Intelligent gateway connecting traditional medicine terminology with globally interoperable digital health records.</p>
      </div>

      <div className="demo-banner">
        ⚠ <strong>Simulated Demo Environment:</strong> The terminology data is real (SQLite-backed), but cross-system audit features are in demo mode.
      </div>

      {/* Stats grid */}
      <div className="grid-4 mb-4">
        {statsLoading ? (
          [0,1,2,3].map(i => <div key={i} className="stat-card"><div className="skeleton skeleton-title" /><div className="skeleton skeleton-line" /></div>)
        ) : stats ? (
          <>
            <StatCard label="NAMASTE Concepts" value={stats.namaste_concepts.toLocaleString()} sub="Registry initialized" icon={BookOpen} />
            <StatCard label="ICD-11 TM2 Concepts" value={stats.icd11_concepts.toLocaleString()} sub="Terminology linked to TM2" icon={BookOpen} iconColor="var(--info)" />
            <StatCard label="Validated Mappings" value={stats.validated_mappings.toLocaleString()} sub={`+${stats.related_mappings} related`} icon={CheckCircle} iconColor="var(--success)" />
            <StatCard label="Total Mappings" value={stats.total_mappings.toLocaleString()} sub={`${stats.mapped_namaste_codes} NAMASTE codes covered`} icon={GitMerge} iconColor="var(--warning)" />
          </>
        ) : null}
      </div>

      <div className="grid-2">
        {/* Terminology System Health */}
        <div className="card">
          <div className="section-header">
            <div>
              <div className="section-title">Terminology System Health</div>
            </div>
            <button className="btn btn-ghost btn-sm"><RefreshCw size={13} /></button>
          </div>
          {termsLoading ? (
            [0,1].map(i => <div key={i} className="skeleton skeleton-line mt-2" />)
          ) : terminologies ? terminologies.map(t => (
            <div className="term-row" key={t.id}>
              <Activity size={15} color={t.status === 'active' ? 'var(--success)' : 'var(--warning)'} />
              <div>
                <div className="term-name">{t.name}</div>
                <div className="term-version">{t.version}</div>
              </div>
              <div className="term-sync">
                <span className={`badge badge-${t.status === 'active' ? 'active' : 'pending'}`}>
                  {t.status === 'active' ? '● Synchronized' : '● Syncing'}
                </span>
                <div style={{marginTop:3}}>{t.concept_count.toLocaleString()} concepts</div>
              </div>
            </div>
          )) : null}
        </div>

        {/* Audit Timeline */}
        <div className="card">
          <div className="section-header">
            <div className="section-title">Gateway Audit & Activity Timeline</div>
          </div>
          <div style={{fontSize:12, lineHeight:1.6}}>
            {AUDIT_EVENTS.map((e, i) => (
              <div key={i} style={{display:'flex', gap:12, paddingBottom:12, borderBottom: i < AUDIT_EVENTS.length-1 ? '1px solid var(--border)' : 'none', marginBottom: i < AUDIT_EVENTS.length-1 ? 12 : 0}}>
                <div style={{width:8, height:8, borderRadius:'50%', background:'var(--accent)', marginTop:5, flexShrink:0}} />
                <div>
                  <div style={{color:'var(--text-muted)', fontSize:10.5, marginBottom:2}}>{e.time} · <strong style={{color:'var(--accent)', fontSize:10}}>{e.action}</strong></div>
                  <div style={{color:'var(--text-primary)', fontSize:12}}>{e.detail}</div>
                  <div style={{color:'var(--text-muted)', fontSize:10.5, marginTop:2}}>Actor: {e.user}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Pipeline Architecture */}
      <div className="card mt-4">
        <div className="section-title" style={{marginBottom:12}}>Interoperability Pipeline Architecture</div>
        <p style={{fontSize:12, color:'var(--text-muted)', marginBottom:16}}>
          Bidirectional mapping path: Standardized Traditional Medicine records mapped and parsed into HL7 FHIR bundles.
        </p>
        <div style={{display:'flex', gap:0, alignItems:'center', fontSize:12}}>
          {['NAMASTE Registry','Mapping Engine','ICD-11 TM2','FHIR R4 ConceptMap','EMR Integration'].map((step, i, arr) => (
            <React.Fragment key={step}>
              <div style={{
                background:'var(--bg-input)', border:'1px solid var(--border-light)',
                borderRadius:'var(--radius)', padding:'10px 14px', textAlign:'center',
                color:'var(--text-secondary)', fontSize:12, fontWeight:500, flex:1
              }}>
                {step}
              </div>
              {i < arr.length - 1 && (
                <div style={{color:'var(--accent)', padding:'0 8px', fontSize:16}}>→</div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}
