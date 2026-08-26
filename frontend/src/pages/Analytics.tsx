import { useQuery } from '@tanstack/react-query';
import { BarChart3, ShieldCheck, ClipboardList, Globe, Activity, Info } from 'lucide-react';
import { getAnalyticsOverview, type TraditionCoverage } from '../api';
import { useLanguage } from '../i18n/LanguageContext';

function Stat({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="stat-card">
      <div className="stat-card-label">{label}</div>
      <div className="stat-card-value">{value}</div>
      {sub && <div className="stat-card-sub">{sub}</div>}
    </div>
  );
}

function CoverageBar({ pct, tone = 'accent' }: { pct: number | null; tone?: 'accent' | 'high' | 'medium' }) {
  const fillClass = tone === 'accent' ? '' : tone;
  return (
    <div className="confidence-bar">
      <div className="confidence-track">
        <div
          className={`confidence-fill ${fillClass}`}
          style={{ width: `${Math.min(100, Math.max(0, pct ?? 0))}%` }}
        />
      </div>
      <div className="confidence-pct">{pct === null ? '—' : `${pct}%`}</div>
    </div>
  );
}

function toneFor(pct: number | null): 'accent' | 'high' | 'medium' {
  if (pct === null) return 'accent';
  if (pct >= 50) return 'high';
  if (pct >= 10) return 'medium';
  return 'accent';
}

function TraditionRow({ t }: { t: TraditionCoverage }) {
  return (
    <tr>
      <td>
        <strong>{t.label}</strong>
        <div className="td-code" style={{ fontSize: 11 }}>{t.system}</div>
      </td>
      <td>{t.corpus_size.toLocaleString()}</td>
      <td>{t.mapped === null ? '—' : t.mapped.toLocaleString()}</td>
      <td>{t.unmapped === null ? '—' : t.unmapped.toLocaleString()}</td>
      <td style={{ minWidth: 160 }}>
        <CoverageBar pct={t.coverage_pct} tone={toneFor(t.coverage_pct)} />
      </td>
    </tr>
  );
}

export default function Analytics() {
  const { t } = useLanguage();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['analytics-overview'],
    queryFn: getAnalyticsOverview,
    refetchInterval: 60000,
  });

  if (isLoading) {
    return (
      <div className="grid-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="stat-card">
            <div className="skeleton skeleton-title" />
            <div className="skeleton skeleton-line" />
          </div>
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="empty-state">
        <div className="empty-state-title">Could not load analytics</div>
        <div className="empty-state-desc">Check that the backend is reachable and try again.</div>
      </div>
    );
  }

  const maxDay = Math.max(1, ...data.audit_activity.map((d) => d.n));

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">
          <BarChart3 size={20} style={{ verticalAlign: -3, marginRight: 6 }} />
          {t('page_analytics_title')}
        </h1>
        <p className="page-desc">
          A live, oversight-level view of the terminology bridge: corpus size and mapping coverage per
          AYUSH tradition, the human review backlog, WHO synchronisation posture, and real system
          activity. Every figure below is computed on the fly from this service's own tables.
        </p>
      </div>

      <div className="demo-banner" style={{ marginBottom: 18, alignItems: 'flex-start' }}>
        <Info size={14} style={{ flexShrink: 0, marginTop: 3 }} />
        <span>{data.data_honesty_note}</span>
      </div>

      <div className="grid-4" style={{ marginBottom: 18 }}>
        <Stat
          label="Curated mappings"
          value={data.mapping_registry.total_mappings.toLocaleString()}
          sub={`${data.mapping_registry.equivalent} equivalent · ${data.mapping_registry.related} related`}
        />
        <Stat
          label="Review queue backlog"
          value={data.review_queue.pending.toLocaleString()}
          sub={`${data.review_queue.approved} approved · ${data.review_queue.rejected} rejected all-time`}
        />
        <Stat
          label="WHO sync status"
          value={data.who_sync.mode.replace(/_/g, ' ')}
          sub={`${data.who_sync.release_sync_coverage_pct}% verified · ${data.who_sync.open_drift_items} open drift`}
        />
        <Stat
          label="AI-reviewed mappings"
          value={data.mapping_registry.ai_reviewed.toLocaleString()}
          sub={`vs ${data.mapping_registry.curated_rule_based} rule-based originals`}
        />
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <div className="section-header">
          <div>
            <div className="section-title">
              <ShieldCheck size={14} style={{ verticalAlign: -2, marginRight: 5 }} />
              Corpus &amp; mapping coverage by tradition
            </div>
            <div className="section-subtitle">
              Raw NAMASTE-family corpus size vs. how much of it has a curated ICD-11 mapping today.
            </div>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Tradition</th><th>Corpus size</th><th>Mapped</th><th>Unmapped</th><th>Coverage</th></tr>
            </thead>
            <tbody>
              {data.traditions.map((t) => <TraditionRow key={t.system} t={t} />)}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 18, gap: 16 }}>
        <div className="card">
          <div className="section-header">
            <div>
              <div className="section-title">
                <ClipboardList size={14} style={{ verticalAlign: -2, marginRight: 5 }} />
                Review queue composition
              </div>
              <div className="section-subtitle">Human-in-the-loop governance throughput.</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {(['pending', 'approved', 'rejected', 'needs_info'] as const).map((k) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{k.replace('_', ' ')}</span>
                <span style={{ fontWeight: 600 }}>{data.review_queue[k].toLocaleString()}</span>
              </div>
            ))}
            <div style={{ borderTop: '1px solid var(--border)', marginTop: 6, paddingTop: 10, display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span style={{ color: 'var(--text-secondary)' }}>Avg. review turnaround</span>
              <span style={{ fontWeight: 600 }}>
                {data.review_queue.avg_review_turnaround_hours === null
                  ? 'No decisions yet'
                  : `${data.review_queue.avg_review_turnaround_hours} hrs`}
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              {data.review_queue.legacy_reclassifications} of the pending items are legacy-reclassification
              flags from the one-time TM2/Biomedicine label audit, not fresh AI suggestions.
            </div>
          </div>
        </div>

        <div className="card">
          <div className="section-header">
            <div>
              <div className="section-title">
                <Globe size={14} style={{ verticalAlign: -2, marginRight: 5 }} />
                WHO synchronisation
              </div>
              <div className="section-subtitle">Live posture — see the WHO Sync page for detail.</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Snapshot release</span>
              <span style={{ fontWeight: 600 }}>{data.who_sync.snapshot_release}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Verified coverage</span>
              <span style={{ fontWeight: 600 }}>{data.who_sync.release_sync_coverage_pct}%</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Open drift items</span>
              <span className={`badge ${data.who_sync.open_drift_items > 0 ? 'badge-pending' : 'badge-equivalent'}`}>
                {data.who_sync.open_drift_items}
              </span>
            </div>
            {data.who_sync.last_release_sync && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                Last checked {new Date(data.who_sync.last_release_sync.run_at).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="section-header">
          <div>
            <div className="section-title">
              <Activity size={14} style={{ verticalAlign: -2, marginRight: 5 }} />
              Governance activity (last 30 days)
            </div>
            <div className="section-subtitle">Real audit-log volume — every bar is an actual recorded action.</div>
          </div>
        </div>

        {data.audit_activity.length ? (
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 90, marginBottom: 14 }}>
            {data.audit_activity.map((d) => (
              <div key={d.day} title={`${d.day}: ${d.n} events`} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', height: '100%' }}>
                <div
                  style={{
                    width: '100%',
                    maxWidth: 22,
                    height: `${Math.max(4, (d.n / maxDay) * 80)}px`,
                    background: 'var(--gradient-brand, var(--accent))',
                    borderRadius: 3,
                  }}
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-title">No audit activity yet</div>
            <div className="empty-state-desc">Approve a review item or run a WHO sync to see activity here.</div>
          </div>
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {data.audit_action_breakdown.map((a) => (
            <span key={a.action} className="badge badge-active" style={{ fontSize: 11 }}>
              {a.action.replace(/_/g, ' ')}: {a.n}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
