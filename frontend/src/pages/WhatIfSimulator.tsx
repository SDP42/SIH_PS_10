import { useState } from 'react';
import { useLanguage } from '../i18n/LanguageContext';
import { useMutation, useQuery } from '@tanstack/react-query';
import { GitCompareArrows, AlertOctagon, ArrowRight, ClipboardList, History } from 'lucide-react';
import {
  getSimulatorReleases, runSimulation, getAffectedMappings, escalateSimulation, getSimulationHistory,
  type SimulationResult, type AffectedMapping,
} from '../api';

const RISK_COLOR: Record<string, string> = { LOW: 'badge-equivalent', MEDIUM: 'badge-pending', HIGH: 'badge-danger' };

function StatBox({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="stat-card">
      <div className="stat-card-label">{label}</div>
      <div className="stat-card-value" style={tone ? { color: tone } : undefined}>{value.toLocaleString()}</div>
    </div>
  );
}

export default function WhatIfSimulator() {
  const { t } = useLanguage();
  const [fromRelease, setFromRelease] = useState('');
  const [toRelease, setToRelease] = useState('');
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [affected, setAffected] = useState<AffectedMapping[] | null>(null);
  const [escalated, setEscalated] = useState<{ count: number } | null>(null);

  const { data: releasesData } = useQuery({ queryKey: ['sim-releases'], queryFn: getSimulatorReleases });
  const { data: historyData, refetch: refetchHistory } = useQuery({ queryKey: ['sim-history'], queryFn: getSimulationHistory });

  const simMutation = useMutation({
    mutationFn: () => runSimulation(fromRelease, toRelease),
    onSuccess: async (r) => {
      setResult(r);
      setEscalated(null);
      const a = await getAffectedMappings(r.id);
      setAffected(a.items);
      refetchHistory();
    },
  });

  const escalateMutation = useMutation({
    mutationFn: () => escalateSimulation(result!.id),
    onSuccess: (r) => setEscalated(r),
  });

  const releases = releasesData?.releases || [];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">
          <GitCompareArrows size={20} style={{ verticalAlign: -3, marginRight: 6 }} />
          {t('page_what_if_title')}
        </h1>
        <p className="page-desc">{t('page_what_if_desc')}</p>
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <div className="section-header">
          <div>
            <div className="section-title">Simulate a release change</div>
            <div className="section-subtitle">
              Try <strong>2025-01 → 2026-01</strong> — this project's own shipped snapshot vs. WHO's actual current release.
            </div>
          </div>
        </div>
        <div className="filter-row" style={{ gap: 10, alignItems: 'center' }}>
          <select className="select" value={fromRelease} onChange={(e) => setFromRelease(e.target.value)}>
            <option value="">From release…</option>
            {releases.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <ArrowRight size={16} style={{ color: 'var(--text-muted)' }} />
          <select className="select" value={toRelease} onChange={(e) => setToRelease(e.target.value)}>
            <option value="">To release…</option>
            {releases.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <button
            className="btn btn-primary"
            disabled={!fromRelease || !toRelease || simMutation.isPending}
            onClick={() => simMutation.mutate()}
          >
            {simMutation.isPending ? 'Simulating…' : 'Run simulation'}
          </button>
        </div>
        {simMutation.isError && (
          <div style={{ color: 'var(--danger)', fontSize: 12.5, marginTop: 10 }}>
            Could not fetch one of these releases from WHO — check your connection and try again.
          </div>
        )}
      </div>

      {result && (
        <>
          <div className="card" style={{ marginBottom: 18, borderColor: result.risk_score === 'HIGH' ? 'var(--danger)' : undefined }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
              <div>
                <div className="section-title">
                  <AlertOctagon size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
                  Release Impact: {result.from_release} → {result.to_release}
                </div>
                <div className="section-subtitle">
                  Checked all {result.total_mappings_checked} curated mappings against {result.to_release_concept_count.toLocaleString()} real WHO concepts.
                </div>
              </div>
              <span className={`badge ${RISK_COLOR[result.risk_score]}`} style={{ fontSize: 13, padding: '6px 14px' }}>
                RISK: {result.risk_score}
              </span>
            </div>

            <div className="grid-4" style={{ marginBottom: 14 }}>
              <StatBox label="New concepts" value={result.new_concepts} />
              <StatBox label="Deprecated concepts" value={result.deprecated_concepts} />
              <StatBox label="Retitled concepts" value={result.retitled_concepts} />
              <StatBox label="Mappings checked" value={result.total_mappings_checked} />
            </div>
            <div className="grid-2" style={{ marginBottom: 14 }}>
              <StatBox label="Broken mappings" value={result.broken_mappings} tone={result.broken_mappings > 0 ? 'var(--danger)' : undefined} />
              <StatBox label="Ambiguous mappings" value={result.ambiguous_mappings} tone={result.ambiguous_mappings > 0 ? 'var(--warning)' : undefined} />
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button
                className="btn btn-primary"
                disabled={escalateMutation.isPending || (result.broken_mappings + result.ambiguous_mappings === 0) || !!escalated}
                onClick={() => escalateMutation.mutate()}
              >
                <ClipboardList size={14} /> {escalated ? `Escalated (${escalated.count})` : 'Escalate all to expert review'}
              </button>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>{result.disclaimer}</div>
          </div>

          {affected && affected.length > 0 && (
            <div className="card" style={{ marginBottom: 18 }}>
              <div className="section-header">
                <div>
                  <div className="section-title">Affected mappings</div>
                  <div className="section-subtitle">Why each one is flagged.</div>
                </div>
              </div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Source</th><th>Target code</th><th>Impact</th><th>Old title</th><th>New title</th></tr></thead>
                  <tbody>
                    {affected.map((a) => (
                      <tr key={a.id}>
                        <td><span className="td-code">{a.source_code}</span></td>
                        <td><span className="td-code">{a.target_code}</span></td>
                        <td>
                          <span className={`badge ${a.impact_type === 'BROKEN_MAPPING' ? 'badge-danger' : 'badge-pending'}`}>
                            {a.impact_type.replace('_', ' ')}
                          </span>
                        </td>
                        <td style={{ fontSize: 12 }}>{a.old_title || '—'}</td>
                        <td style={{ fontSize: 12 }}>{a.new_title || <em style={{ color: 'var(--text-muted)' }}>no longer exists</em>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      <div className="card">
        <div className="section-header">
          <div>
            <div className="section-title"><History size={14} style={{ verticalAlign: -2, marginRight: 5 }} />Simulation history</div>
          </div>
        </div>
        {historyData?.simulations.length ? (
          <div className="table-wrap">
            <table>
              <thead><tr><th>When</th><th>From → To</th><th>Broken</th><th>Ambiguous</th><th>Risk</th><th>Escalated</th></tr></thead>
              <tbody>
                {historyData.simulations.map((s: any) => (
                  <tr key={s.id}>
                    <td style={{ fontSize: 11.5 }}>{new Date(s.run_at).toLocaleString()}</td>
                    <td className="td-code">{s.from_release} → {s.to_release}</td>
                    <td>{s.broken_mapping_count}</td>
                    <td>{s.ambiguous_mapping_count}</td>
                    <td><span className={`badge ${RISK_COLOR[s.risk_score]}`}>{s.risk_score}</span></td>
                    <td>{s.escalated_at ? '✓' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-title">No simulations run yet</div>
          </div>
        )}
      </div>
    </div>
  );
}
