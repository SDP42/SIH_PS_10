import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Sparkles, Search, PlayCircle, ChevronRight } from 'lucide-react';
import {
  getAiSuggestion, getUnmapped, batchSuggest,
  type AiSuggestion, type AiDecision,
} from '../api';

const DECISION_META: Record<AiDecision, { label: string; color: string; bg: string }> = {
  AUTO_SUGGEST: { label: 'Auto-Suggest', color: '#16a34a', bg: 'rgba(22,163,74,0.12)' },
  NEEDS_CONTEXT: { label: 'Needs Context', color: '#d97706', bg: 'rgba(217,119,6,0.12)' },
  EXPERT_REVIEW: { label: 'Expert Review', color: '#ea580c', bg: 'rgba(234,88,12,0.12)' },
  NO_VALIDATED_EQUIVALENT: { label: 'No Validated Equivalent', color: '#6b7280', bg: 'rgba(107,114,128,0.12)' },
};

function DecisionBadge({ decision }: { decision: AiDecision }) {
  const meta = DECISION_META[decision];
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '4px 10px', borderRadius: 999, fontSize: 12.5, fontWeight: 700,
      color: meta.color, background: meta.bg,
    }}>
      {meta.label}
    </span>
  );
}

function SimilarityBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const cls = pct >= 72 ? 'high' : pct >= 45 ? '' : 'medium';
  return (
    <div className="confidence-bar">
      <div className="confidence-track"><div className={`confidence-fill ${cls}`} style={{ width: `${pct}%` }} /></div>
      <span className="confidence-pct">{pct}%</span>
    </div>
  );
}

function SuggestionCard({ suggestion }: { suggestion: AiSuggestion }) {
  return (
    <div className="card mb-4">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 2 }}>{suggestion.source_system}</div>
          <div style={{ fontSize: 16, fontWeight: 700 }}>{suggestion.namaste_code}</div>
        </div>
        <DecisionBadge decision={suggestion.decision} />
      </div>

      <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: 14 }}>
        {suggestion.rationale}
      </p>

      {suggestion.margin !== null && (
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
          Margin (top1 − top2): <strong>{suggestion.margin.toFixed(3)}</strong>
        </div>
      )}

      {suggestion.has_curated_mapping && (
        <div className="card" style={{ background: 'var(--bg-input)', marginBottom: 14, padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent)', marginBottom: 8 }}>
            RULE-BASED v0 RESULT (curated registry — ground truth)
          </div>
          {suggestion.curated_mappings.map((m, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, fontSize: 13, marginBottom: 4 }}>
              <span className={`badge badge-${m.equivalence === 'equivalent' ? 'equivalent' : 'related'}`}>{m.equivalence}</span>
              <span className="td-code">{m.target_code}</span>
              <span>{m.target_title}</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8 }}>
        AI-ASSISTED RESULT — {suggestion.candidates.length} candidate{suggestion.candidates.length !== 1 ? 's' : ''}
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>#</th><th>ICD-11 TM2 Candidate</th><th>Code</th><th>Similarity</th><th>Shared Terms</th></tr>
          </thead>
          <tbody>
            {suggestion.candidates.map((c) => (
              <tr key={c.icd11_code}>
                <td>{c.rank}</td>
                <td>{c.icd11_title}</td>
                <td><span className="td-code">{c.icd11_code}</span></td>
                <td style={{ minWidth: 140 }}><SimilarityBar value={c.similarity} /></td>
                <td style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{c.shared_terms.join(', ') || '—'}</td>
              </tr>
            ))}
            {suggestion.candidates.length === 0 && (
              <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 16 }}>No candidates above the floor threshold.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function AiMappingLab() {
  const [codeInput, setCodeInput] = useState('');
  const [activeCode, setActiveCode] = useState<string | null>(null);
  const [batchResults, setBatchResults] = useState<AiSuggestion[] | null>(null);
  const qc = useQueryClient();

  const { data: unmappedPreview } = useQuery({
    queryKey: ['ai-unmapped-preview'],
    queryFn: () => getUnmapped({ page: 1, page_size: 8 }),
  });

  const { data: suggestion, isLoading, isError, error } = useQuery({
    queryKey: ['ai-suggest', activeCode],
    queryFn: () => getAiSuggestion(activeCode as string),
    enabled: !!activeCode,
    retry: false,
  });

  const batchMutation = useMutation({
    mutationFn: () => batchSuggest({ all_unmapped: true, limit: 50 }),
    onSuccess: (data) => {
      const ok = data.results.filter((r): r is AiSuggestion => !('error' in r));
      setBatchResults(ok);
      qc.invalidateQueries({ queryKey: ['ai-unmapped-preview'] });
    },
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (codeInput.trim()) setActiveCode(codeInput.trim());
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title"><Sparkles size={20} style={{ verticalAlign: -3, marginRight: 6 }} />AI Mapping Lab</h1>
        <p className="page-desc">
          Ambiguity-aware AI suggestions for the {unmappedPreview ? unmappedPreview.total_unmapped.toLocaleString() : '…'} NAMASTE-family
          codes with no curated ICD-11 mapping — every suggestion is transparently classified, never silently guessed.
        </p>
      </div>

      <div className="card mb-4">
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 10 }}>
          <div className="input-with-icon" style={{ flex: 1 }}>
            <Search size={15} className="input-icon" />
            <input
              className="input"
              placeholder="Enter a NAMASTE-family code (e.g. from nam, nsm, num, ast)…"
              value={codeInput}
              onChange={(e) => setCodeInput(e.target.value)}
            />
          </div>
          <button type="submit" className="btn btn-primary">Get AI Suggestion</button>
        </form>
        {unmappedPreview && unmappedPreview.concepts.length > 0 && (
          <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>Try:</span>
            {unmappedPreview.concepts.slice(0, 6).map((c) => (
              <button
                key={c.code}
                className="btn btn-outline btn-sm"
                onClick={() => { setCodeInput(c.code); setActiveCode(c.code); }}
              >
                {c.code}
              </button>
            ))}
          </div>
        )}
      </div>

      {isLoading && (
        <div className="card mb-4">
          {[0, 1, 2].map((i) => <div key={i} className="skeleton skeleton-line" style={{ marginBottom: 10 }} />)}
        </div>
      )}
      {isError && (
        <div className="card mb-4 empty-state">
          <div className="empty-state-icon">⚠️</div>
          <div className="empty-state-title">Could not get a suggestion</div>
          <div className="empty-state-desc">{(error as any)?.detail?.message || (error as any)?.message || 'Code not found or AI engine not ready.'}</div>
        </div>
      )}
      {suggestion && <SuggestionCard suggestion={suggestion} />}

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14 }}>Run AI over next 50 unmapped codes</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Live demo: the AI engine chews through the real unmapped gap.</div>
          </div>
          <button className="btn btn-primary" onClick={() => batchMutation.mutate()} disabled={batchMutation.isPending}>
            <PlayCircle size={15} /> {batchMutation.isPending ? 'Running…' : 'Run Batch'}
          </button>
        </div>

        {batchMutation.isPending && (
          <div>{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton skeleton-line" style={{ marginBottom: 8 }} />)}</div>
        )}

        {batchResults && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Code</th><th>System</th><th>Decision</th><th>Top Candidate</th><th>Similarity</th><th></th></tr>
              </thead>
              <tbody>
                {batchResults.map((r) => (
                  <tr key={r.namaste_code} className="cursor-pointer" onClick={() => setActiveCode(r.namaste_code)}>
                    <td><span className="td-code">{r.namaste_code}</span></td>
                    <td>{r.source_system}</td>
                    <td><DecisionBadge decision={r.decision} /></td>
                    <td>{r.candidates[0]?.icd11_title || '—'}</td>
                    <td>{r.candidates[0] ? `${Math.round(r.candidates[0].similarity * 100)}%` : '—'}</td>
                    <td><ChevronRight size={14} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
