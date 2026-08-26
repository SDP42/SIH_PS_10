import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Globe, RefreshCw, AlertTriangle, CheckCircle2, CloudOff, ExternalLink, Search } from 'lucide-react';
import {
  getWhoStatus, getWhoReleases, getWhoDrift, getWhoHistory, runWhoSync, lookupWhoCode,
  type WhoCodeLookup, type WhoProvenance,
} from '../api';

const PROVENANCE_LABEL: Record<WhoProvenance, { text: string; badge: string; hint: string }> = {
  WHO_LIVE: {
    text: 'Live from WHO',
    badge: 'badge-equivalent',
    hint: 'Fetched from the WHO ICD-API just now.',
  },
  WHO_CACHE: {
    text: 'WHO (cached)',
    badge: 'badge-related',
    hint: 'A previous live WHO response, still within its cache window.',
  },
  LOCAL_SNAPSHOT: {
    text: 'Offline snapshot',
    badge: 'badge-pending',
    hint: 'WHO was not reachable or not configured — served from the local ICD-11 snapshot.',
  },
};

const COMPARISON_BADGE: Record<string, string> = {
  CONFIRMED: 'badge-equivalent',
  TITLE_DRIFT: 'badge-pending',
  NOT_IN_WHO_RELEASE: 'badge-danger',
  LOCAL_ONLY: 'badge-active',
  FETCH_ERROR: 'badge-danger',
};

function Stat({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="stat-card">
      <div className="stat-card-label">{label}</div>
      <div className="stat-card-value">{value}</div>
      {sub && <div className="stat-card-sub">{sub}</div>}
    </div>
  );
}

function CodeLookup() {
  const [code, setCode] = useState('');
  const [result, setResult] = useState<WhoCodeLookup | null>(null);

  const mutation = useMutation({
    mutationFn: (c: string) => lookupWhoCode(c, { force: true }),
    onSuccess: setResult,
  });

  const prov = result ? PROVENANCE_LABEL[result.provenance] : null;

  return (
    <div className="card">
      <div className="section-header">
        <div>
          <div className="section-title">Resolve a code against WHO</div>
          <div className="section-subtitle">
            Ask the WHO ICD-API for one code right now, and compare its answer to our snapshot.
          </div>
        </div>
      </div>

      <div className="filter-row" style={{ marginBottom: 14 }}>
        <div className="input-with-icon" style={{ flex: 1, minWidth: 220 }}>
          <Search size={14} className="input-icon" />
          <input
            className="input"
            placeholder="ICD-11 code, e.g. 1A00 or TM26.0"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && code.trim() && mutation.mutate(code.trim())}
          />
        </div>
        <button
          className="btn btn-primary"
          disabled={!code.trim() || mutation.isPending}
          onClick={() => mutation.mutate(code.trim())}
        >
          {mutation.isPending ? 'Asking WHO…' : 'Look up'}
        </button>
      </div>

      {result && prov && (
        <div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10, flexWrap: 'wrap' }}>
            <span className={`badge ${prov.badge}`} title={prov.hint}>{prov.text}</span>
            <span className={`badge ${COMPARISON_BADGE[result.comparison.status] || 'badge-active'}`}>
              {result.comparison.status.replace(/_/g, ' ')}
            </span>
            <span style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
              release {result.release_id}
            </span>
          </div>

          <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginBottom: 12 }}>
            {result.comparison.message}
          </div>

          <div className="grid-2">
            <div className="card-sm">
              <div className="detail-section-label">Our snapshot</div>
              {result.local ? (
                <>
                  <div style={{ fontWeight: 600, marginTop: 4 }}>{result.local.title}</div>
                  <div className="td-code" style={{ fontSize: 11.5 }}>{result.local.code}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                    Chapter {result.local.chapter} · {result.local.class_kind}
                  </div>
                </>
              ) : (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                  Not present in the local ICD-11 snapshot.
                </div>
              )}
            </div>

            <div className="card-sm">
              <div className="detail-section-label">WHO ICD-API</div>
              {result.who ? (
                <>
                  <div style={{ fontWeight: 600, marginTop: 4 }}>{result.who.title}</div>
                  {result.who.definition && (
                    <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', marginTop: 6 }}>
                      {result.who.definition}
                    </div>
                  )}
                  {result.who.browser_url && (
                    <a
                      className="btn btn-ghost btn-sm"
                      style={{ marginTop: 8 }}
                      href={result.who.browser_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open in WHO browser <ExternalLink size={12} />
                    </a>
                  )}
                </>
              ) : (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                  {result.degraded_reason || 'WHO does not list this code in the requested release.'}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function WhoSync() {
  const qc = useQueryClient();
  const [toast, setToast] = useState<string | null>(null);

  const { data: status, isLoading } = useQuery({ queryKey: ['who-status'], queryFn: getWhoStatus });
  const { data: releases } = useQuery({ queryKey: ['who-releases'], queryFn: getWhoReleases });
  const { data: drift } = useQuery({ queryKey: ['who-drift'], queryFn: () => getWhoDrift(100) });
  const { data: history } = useQuery({ queryKey: ['who-history'], queryFn: () => getWhoHistory(10) });

  const sync = useMutation({
    mutationFn: () => runWhoSync({ limit: 25 }),
    onSuccess: (res) => {
      setToast(
        res.mode === 'SKIPPED_NO_CREDENTIALS'
          ? 'No WHO credentials configured — the service kept serving the offline snapshot.'
          : `Checked ${res.codes_checked} codes: ${res.confirmed} confirmed, ${res.drifted} drifted, ${res.missing} missing.`
      );
      setTimeout(() => setToast(null), 6000);
      qc.invalidateQueries({ queryKey: ['who-status'] });
      qc.invalidateQueries({ queryKey: ['who-drift'] });
      qc.invalidateQueries({ queryKey: ['who-history'] });
    },
    onError: () => {
      setToast('Sync could not be started — are you signed in?');
      setTimeout(() => setToast(null), 5000);
    },
  });

  const live = status?.mode === 'LIVE_CAPABLE';

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">
          <Globe size={20} style={{ verticalAlign: -3, marginRight: 6 }} />
          WHO ICD-11 Synchronisation
        </h1>
        <p className="page-desc">
          The rest of this service reads a static ICD-11 snapshot. This page is the live half: it
          authenticates against WHO's ICD-API, resolves codes through it, and reports{' '}
          <strong>drift</strong> — mapping targets whose WHO title no longer matches ours, or that
          have left the release. Nothing is ever rewritten automatically; drift is raised for a human.
        </p>
      </div>

      {!isLoading && !live && (
        <div className="demo-banner" style={{ marginBottom: 14, alignItems: 'flex-start' }}>
          <CloudOff size={14} style={{ flexShrink: 0, marginTop: 3 }} />
          {/* .demo-banner is a flex row, so mixed inline content has to be wrapped
              in a single child or every element becomes its own flex column. */}
          <span>
            <strong>Snapshot-only mode.</strong> No WHO ICD-API credentials are configured, so every
            answer below comes from the offline ICD-11 snapshot ({status?.snapshot_label}) and is
            labelled as such. This is a deliberate degradation, not a failure — the service stays
            fully functional without WHO connectivity. To go live, register a free client at{' '}
            <a href={status?.registration_url} target="_blank" rel="noreferrer">icd.who.int/icdapi</a>{' '}
            and set <code>ICD_API_CLIENT_ID</code> / <code>ICD_API_CLIENT_SECRET</code>.
          </span>
        </div>
      )}

      {toast && <div className="demo-banner" style={{ marginBottom: 14 }}>{toast}</div>}

      <div className="grid-4" style={{ marginBottom: 18 }}>
        <Stat
          label="Connection mode"
          value={live ? 'Live' : 'Snapshot'}
          sub={live ? 'WHO ICD-API credentials present' : 'Offline ICD-11 snapshot'}
        />
        <Stat
          label="Snapshot release"
          value={status?.snapshot_release ?? '—'}
          sub={
            releases?.latest
              ? releases.snapshot_is_latest
                ? 'Matches WHO’s latest release'
                : `WHO’s latest is ${releases.latest}`
              : 'WHO release list unavailable'
          }
        />
        <Stat
          label="Verified against WHO"
          value={`${status?.codes_cached_from_who ?? 0} / ${status?.mapping_target_codes ?? 0}`}
          sub={`${status?.coverage_pct ?? 0}% of mapping targets checked`}
        />
        <Stat
          label="Open drift items"
          value={status?.open_drift_items ?? 0}
          sub="Awaiting human review"
        />
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <div className="section-header">
          <div>
            <div className="section-title">Run a synchronisation pass</div>
            <div className="section-subtitle">
              Checks the next 25 least-recently-verified mapping-target codes against WHO. Repeated
              runs sweep forward through the corpus rather than re-checking the same batch.
            </div>
          </div>
          <button className="btn btn-primary" disabled={sync.isPending} onClick={() => sync.mutate()}>
            <RefreshCw size={14} className={sync.isPending ? 'spin' : undefined} />
            {sync.isPending ? 'Syncing…' : 'Sync with WHO'}
          </button>
        </div>

        {status?.last_sync ? (
          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Last run <strong>{new Date(status.last_sync.run_at).toLocaleString()}</strong> by{' '}
            {status.last_sync.actor || 'system'} — {status.last_sync.mode.replace(/_/g, ' ').toLowerCase()},{' '}
            {status.last_sync.codes_checked} codes checked.
            <div style={{ color: 'var(--text-muted)', marginTop: 4 }}>{status.last_sync.detail}</div>
          </div>
        ) : (
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>No synchronisation has been run yet.</div>
        )}
      </div>

      <div style={{ marginBottom: 18 }}>
        <CodeLookup />
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <div className="section-header">
          <div>
            <div className="section-title">
              <AlertTriangle size={14} style={{ verticalAlign: -2, marginRight: 5 }} />
              Terminology drift
            </div>
            <div className="section-subtitle">{status?.disclaimer}</div>
          </div>
        </div>

        {drift?.items.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th><th>Type</th><th>Our snapshot says</th><th>WHO says</th><th>Detected</th>
                </tr>
              </thead>
              <tbody>
                {drift.items.map((d) => (
                  <tr key={`${d.code}-${d.release_id}`}>
                    <td><span className="td-code">{d.code}</span></td>
                    <td>
                      <span className={`badge ${COMPARISON_BADGE[d.drift_type] || 'badge-pending'}`}>
                        {d.drift_type.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>{d.local_title || '—'}</td>
                    <td>{d.who_title || <span style={{ color: 'var(--text-muted)' }}>absent from release</span>}</td>
                    <td style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                      {new Date(d.detected_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon"><CheckCircle2 size={22} /></div>
            <div className="empty-state-title">No drift recorded</div>
            <div className="empty-state-desc">
              Every code checked so far agrees with WHO. Run a sync to check more.
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <div className="section-header">
          <div>
            <div className="section-title">Synchronisation history</div>
            <div className="section-subtitle">
              Every attempt is logged — including the ones that could not reach WHO.
            </div>
          </div>
        </div>

        {history?.runs.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>When</th><th>Mode</th><th>Release</th><th>Checked</th>
                  <th>Confirmed</th><th>Drifted</th><th>Missing</th><th>Operator</th>
                </tr>
              </thead>
              <tbody>
                {history.runs.map((r) => (
                  <tr key={r.id}>
                    <td style={{ fontSize: 11.5 }}>{new Date(r.run_at).toLocaleString()}</td>
                    <td>
                      <span className={`badge ${r.mode === 'COMPLETED' ? 'badge-equivalent' : 'badge-pending'}`}>
                        {r.mode.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="td-code">{r.release_id}</td>
                    <td>{r.codes_checked}</td>
                    <td>{r.confirmed}</td>
                    <td>{r.drifted}</td>
                    <td>{r.missing}</td>
                    <td style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{r.actor || 'system'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-title">No sync runs yet</div>
          </div>
        )}
      </div>
    </div>
  );
}
