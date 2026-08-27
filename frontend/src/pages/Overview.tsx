import { useLanguage } from '../i18n/LanguageContext';
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getStats, getTerminologies, getUnmapped, getReviewQueue, getRecentAudit } from '../api';
import { BookOpen, GitMerge, CheckCircle, RefreshCw, Activity, Sparkles, ClipboardList } from 'lucide-react';

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

export default function Overview() {
  const { t } = useLanguage();
  const { data: stats, isLoading: statsLoading } = useQuery({ queryKey: ['stats'], queryFn: getStats });
  const { data: terminologies, isLoading: termsLoading } = useQuery({ queryKey: ['terminologies'], queryFn: getTerminologies });
  const { data: unmapped } = useQuery({
    queryKey: ['ai-unmapped-count'],
    queryFn: () => getUnmapped({ page: 1, page_size: 1 }),
    retry: false,
  });
  const { data: pendingReviews } = useQuery({
    queryKey: ['ai-pending-count'],
    queryFn: () => getReviewQueue({ status: 'pending', page: 1, page_size: 1 }),
    retry: false,
  });
  const { data: approvedReviews } = useQuery({
    queryKey: ['ai-approved-count'],
    queryFn: () => getReviewQueue({ status: 'approved', page: 1, page_size: 1 }),
    retry: false,
  });
  const { data: auditData, isLoading: auditLoading, isError: auditError } = useQuery({
    queryKey: ['audit-recent'],
    queryFn: () => getRecentAudit(6),
    retry: false,
  });

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">{t('page_overview_title')}</h1>
        <p className="page-desc">{t('page_overview_desc')}</p>
      </div>

      {/* Stats grid */}
      <div className="grid-4 mb-4">
        {statsLoading ? (
          [0,1,2,3].map(i => <div key={i} className="stat-card"><div className="skeleton skeleton-title" /><div className="skeleton skeleton-line" /></div>)
        ) : stats ? (
          <>
            <StatCard label="NAMASTE Concepts" value={stats.namaste_concepts.toLocaleString()} sub="Registry initialized" icon={BookOpen} />
            <StatCard label="ICD-11 Concepts (All Chapters)" value={stats.icd11_concepts.toLocaleString()} sub="TM2 + Biomedicine, see AI Lab for split" icon={BookOpen} iconColor="var(--info)" />
            <StatCard label="Validated Mappings" value={stats.validated_mappings.toLocaleString()} sub={`+${stats.related_mappings} related`} icon={CheckCircle} iconColor="var(--success)" />
            <StatCard label="Total Mappings" value={stats.total_mappings.toLocaleString()} sub={`${stats.mapped_namaste_codes} NAMASTE codes covered`} icon={GitMerge} iconColor="var(--warning)" />
          </>
        ) : null}
      </div>

      {/* AI / Governance stats — live from the ambiguity-aware mapping engine */}
      <div className="grid-4 mb-4">
        <StatCard
          label="Unmapped NAMASTE Codes"
          value={unmapped ? unmapped.total_unmapped.toLocaleString() : '—'}
          sub="Gap the AI engine targets"
          icon={Sparkles}
          iconColor="var(--warning)"
        />
        <StatCard
          label="AI Suggestions Pending Review"
          value={pendingReviews ? pendingReviews.total.toLocaleString() : '—'}
          sub="Awaiting human decision"
          icon={ClipboardList}
          iconColor="var(--info)"
        />
        <StatCard
          label="AI-Reviewed Mappings Added"
          value={approvedReviews ? approvedReviews.total.toLocaleString() : '—'}
          sub="Approved into the curated registry"
          icon={CheckCircle}
          iconColor="var(--success)"
        />
        <StatCard
          label="AI Engine"
          value={unmapped ? 'Ready' : 'Not built'}
          sub={unmapped ? 'Embeddings loaded' : 'Run build_embeddings.py'}
          icon={Activity}
          iconColor={unmapped ? 'var(--success)' : 'var(--danger)'}
        />
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
          ) : terminologies ? terminologies.map(term => (
            <div className="term-row" key={term.id}>
              <Activity size={15} color={term.status === 'active' ? 'var(--success)' : 'var(--warning)'} />
              <div>
                <div className="term-name">{term.name}</div>
                <div className="term-version">{term.version}</div>
              </div>
              <div className="term-sync">
                <span className={`badge badge-${term.status === 'active' ? 'active' : 'pending'}`}>
                  {term.status === 'active' ? '● Synchronized' : '● Syncing'}
                </span>
                <div style={{marginTop:3}}>{term.concept_count.toLocaleString()} concepts</div>
              </div>
            </div>
          )) : null}
        </div>

        {/* Audit Timeline — real, from GET /api/audit/recent, not hardcoded */}
        <div className="card">
          <div className="section-header">
            <div className="section-title">Gateway Audit & Activity Timeline</div>
          </div>
          <div style={{fontSize:12, lineHeight:1.6}}>
            {auditLoading ? (
              [0,1,2].map(i => <div key={i} className="skeleton skeleton-line mt-2" />)
            ) : auditError ? (
              <div style={{color:'var(--text-muted)', fontSize:12}}>Could not load audit trail.</div>
            ) : !auditData?.events.length ? (
              <div style={{color:'var(--text-muted)', fontSize:12}}>
                No events yet — approve/reject a review item or upload a FHIR Bundle to see real activity here.
              </div>
            ) : auditData.events.map((e, i) => (
              <div key={e.id} style={{display:'flex', gap:12, paddingBottom:12, borderBottom: i < auditData.events.length-1 ? '1px solid var(--border)' : 'none', marginBottom: i < auditData.events.length-1 ? 12 : 0}}>
                <div style={{width:8, height:8, borderRadius:'50%', background:'var(--accent)', marginTop:5, flexShrink:0}} />
                <div>
                  <div style={{color:'var(--text-muted)', fontSize:10.5, marginBottom:2}}>{new Date(e.created_at).toLocaleString()} · <strong style={{color:'var(--accent)', fontSize:10}}>{e.action}</strong></div>
                  <div style={{color:'var(--text-primary)', fontSize:12}}>{e.target}{e.details ? ` — ${e.details}` : ''}</div>
                  <div style={{color:'var(--text-muted)', fontSize:10.5, marginTop:2}}>Actor: {e.actor}</div>
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
