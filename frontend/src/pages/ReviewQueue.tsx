import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, XCircle, HelpCircle, ClipboardCheck } from 'lucide-react';
import { getReviewQueue, decideReviewItem, type ReviewQueueItem } from '../api';

const STATUS_TABS = [
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
];

function DecideRow({ item, onDone }: { item: ReviewQueueItem; onDone: () => void }) {
  const [note, setNote] = useState('');
  const [expanded, setExpanded] = useState(false);
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: (status: string) => decideReviewItem(item.id, { status, note: note || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-queue'] });
      onDone();
    },
  });

  return (
    <tr>
      <td>
        <span className="td-code">{item.source_code}</span>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{item.source_system}</div>
        {item.flag_type === 'legacy_reclassification' ? (
          <span className="badge badge-pending" style={{ marginTop: 4, fontSize: 10 }} title="A historical curated mapping was found mislabeled TM2/Biomedicine and relabeled automatically — this flags its match quality for confirmation, not the label.">
            Legacy Reclassification
          </span>
        ) : (
          <span className="badge badge-active" style={{ marginTop: 4, fontSize: 10 }}>AI Suggestion</span>
        )}
      </td>
      <td>
        <span className={`badge badge-${item.decision === 'NEEDS_CONTEXT' ? 'pending' : 'related'}`}>{item.decision}</span>
        {item.target_system && <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 3 }}>{item.target_system}</div>}
      </td>
      <td>{item.ai_suggested_title || '—'}<div className="td-code" style={{ fontSize: 11 }}>{item.ai_suggested_code}</div></td>
      <td>{item.confidence !== null ? `${Math.round(item.confidence * 100)}%` : '—'}</td>
      <td style={{ maxWidth: 260 }}>
        <button className="btn btn-ghost btn-sm" onClick={() => setExpanded((v) => !v)}>
          {expanded ? 'Hide rationale' : 'Rationale'}
        </button>
        {expanded && <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', marginTop: 6 }}>{item.rationale}</div>}
      </td>
      {item.status === 'pending' ? (
        <td>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              className="input"
              placeholder="Reviewer note…"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              style={{ width: 140, fontSize: 12 }}
            />
            <button className="btn btn-sm" style={{ background: '#16a34a', color: 'white' }} disabled={mutation.isPending} onClick={() => mutation.mutate('approved')}>
              <CheckCircle2 size={13} /> Approve
            </button>
            <button className="btn btn-sm" style={{ background: '#dc2626', color: 'white' }} disabled={mutation.isPending} onClick={() => mutation.mutate('rejected')}>
              <XCircle size={13} /> Reject
            </button>
            <button className="btn btn-outline btn-sm" disabled={mutation.isPending} onClick={() => mutation.mutate('needs_info')}>
              <HelpCircle size={13} /> Needs Info
            </button>
          </div>
        </td>
      ) : (
        <td>
          <span className={`badge badge-${item.status === 'approved' ? 'equivalent' : 'danger'}`}>{item.status}</span>
          {item.reviewer_note && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>"{item.reviewer_note}"</div>}
        </td>
      )}
    </tr>
  );
}

type FlagFilter = 'all' | 'ai_suggestion' | 'legacy_reclassification';

export default function ReviewQueue() {
  const [status, setStatus] = useState('pending');
  const [flagFilter, setFlagFilter] = useState<FlagFilter>('all');
  const [toast, setToast] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['review-queue', status],
    queryFn: () => getReviewQueue({ status, page: 1, page_size: 100 }),
  });

  const filteredItems = data?.items.filter((i) => flagFilter === 'all' || i.flag_type === flagFilter) ?? [];
  const legacyCount = data?.items.filter((i) => i.flag_type === 'legacy_reclassification').length ?? 0;

  function handleDone() {
    setToast('Decision recorded. If approved, it is now a curated mapping in the registry.');
    setTimeout(() => setToast(null), 4000);
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title"><ClipboardCheck size={20} style={{ verticalAlign: -3, marginRight: 6 }} />Expert Review Queue</h1>
        <p className="page-desc">
          Human-in-the-loop governance: AI suggestions that need context or expert review land here.
          Approving one writes a brand-new curated mapping — nothing is ever auto-approved.
        </p>
      </div>

      {legacyCount > 0 && (
        <div className="demo-banner" style={{ marginBottom: 12 }}>
          ⚠ {legacyCount} of these items are <strong>legacy reclassifications</strong>: a one-time data audit found
          historical curated mappings whose target_system was mislabeled TM2 when the code actually falls in a
          Biomedicine chapter. The label was corrected automatically (that's a fact, not a judgment call) — these
          items ask a human to confirm the underlying match itself is still correct, since it came from a fuzzy
          matching pass that was never precision-validated.
        </div>
      )}

      {toast && (
        <div className="card mb-4" style={{ background: 'rgba(22,163,74,0.1)', borderColor: '#16a34a', fontSize: 13 }}>
          ✅ {toast}
        </div>
      )}

      <div className="tabs mb-4">
        {STATUS_TABS.map((t) => (
          <button key={t.key} className={`tab${status === t.key ? ' active' : ''}`} onClick={() => setStatus(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        {([
          { key: 'all', label: 'All' },
          { key: 'ai_suggestion', label: 'AI Suggestions' },
          { key: 'legacy_reclassification', label: `Legacy Reclassifications${legacyCount ? ` (${legacyCount})` : ''}` },
        ] as { key: FlagFilter; label: string }[]).map((f) => (
          <button
            key={f.key}
            className={`btn btn-sm ${flagFilter === f.key ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setFlagFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="card">
        {isLoading ? (
          <div>{[0, 1, 2].map((i) => <div key={i} className="skeleton skeleton-line" style={{ marginBottom: 10 }} />)}</div>
        ) : isError ? (
          <div className="empty-state">
            <div className="empty-state-icon">⚠️</div>
            <div className="empty-state-title">Backend unavailable</div>
          </div>
        ) : !filteredItems.length ? (
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <div className="empty-state-title">No {status} items</div>
            <div className="empty-state-desc">Run some AI suggestions in the AI Mapping Lab to populate this queue.</div>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>NAMASTE Code</th><th>AI Decision</th><th>AI Suggested Target</th><th>Confidence</th><th>Rationale</th><th>{status === 'pending' ? 'Decide' : 'Outcome'}</th></tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <DecideRow key={item.id} item={item} onDone={handleDone} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
