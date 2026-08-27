import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { MessageSquareText, AlertTriangle, Ban, Search } from 'lucide-react';
import { getClinicalTextCandidates, type SymptomCandidate } from '../api';
import { useLanguage } from '../i18n/LanguageContext';

const EXAMPLES = [
  'Patient has cough.',
  'Patient has fever and productive cough for 5 days.',
  'Patient has no fever but has cough for 5 days.',
  'Patient complains of lower back pain radiating to right leg.',
  'Patient reports burning sensation during urination.',
];

function AttributeChips({ s }: { s: SymptomCandidate }) {
  const chips: string[] = [];
  if (s.duration) chips.push(`duration: ${s.duration}`);
  if (s.body_site) chips.push(`site: ${s.body_site}`);
  if (s.laterality) chips.push(`laterality: ${s.laterality}`);
  if (!chips.length) return null;
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
      {chips.map((c) => (
        <span key={c} className="badge badge-active" style={{ fontSize: 10.5 }}>{c}</span>
      ))}
    </div>
  );
}

function SymptomCard({ s }: { s: SymptomCandidate }) {
  return (
    <div className="card-sm" style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <span className="badge badge-equivalent" style={{ textTransform: 'capitalize' }}>{s.symptom}</span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>from &ldquo;{s.surface_form}&rdquo;</span>
      </div>
      <AttributeChips s={s} />

      {s.candidates.length > 0 ? (
        <div className="table-wrap" style={{ marginTop: 10 }}>
          <table>
            <thead><tr><th>System</th><th>Code</th><th>Display</th></tr></thead>
            <tbody>
              {s.candidates.map((c, i) => (
                <tr key={`${c.code}-${i}`}>
                  <td><span className={`badge badge-${c.system_id === 'namaste' ? 'active' : 'related'}`}>{(c as any).tradition || c.system}</span></td>
                  <td><span className="td-code">{c.code}</span></td>
                  <td style={{ fontSize: 12.5 }}>
                    {c.display}
                    {(c as any).native_script && (
                      <span style={{ color: 'var(--accent)', marginLeft: 8 }}>{(c as any).native_script}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
          No terminology candidates found — this would route to expert review rather than a guess.
        </div>
      )}
    </div>
  );
}

export default function ClinicalTextAssistant() {
  const { t } = useLanguage();
  const [text, setText] = useState('');
  const [submitted, setSubmitted] = useState('');

  const mutation = useMutation({
    mutationFn: (t: string) => getClinicalTextCandidates(t),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setSubmitted(text.trim());
    mutation.mutate(text.trim());
  }

  const data = mutation.data;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">
          <MessageSquareText size={20} style={{ verticalAlign: -3, marginRight: 6 }} />
          {t('page_clinical_text_title')}
        </h1>
        <p className="page-desc">{t('page_clinical_text_desc')}</p>
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <form onSubmit={handleSubmit}>
          <textarea
            className="input"
            style={{ width: '100%', minHeight: 90, fontFamily: 'inherit', fontSize: 14, resize: 'vertical' }}
            placeholder="e.g. Patient has fever and productive cough for 5 days."
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={2000}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10, flexWrap: 'wrap', gap: 8 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => setText(ex)}
                >
                  {ex.length > 38 ? ex.slice(0, 38) + '…' : ex}
                </button>
              ))}
            </div>
            <button className="btn btn-primary" type="submit" disabled={!text.trim() || mutation.isPending}>
              <Search size={14} /> {mutation.isPending ? 'Analyzing…' : 'Analyze'}
            </button>
          </div>
        </form>
      </div>

      {mutation.isError && (
        <div className="empty-state">
          <div className="empty-state-title">Could not analyze this text</div>
          <div className="empty-state-desc">Check the backend is reachable and try again.</div>
        </div>
      )}

      {data && (
        <>
          <div className="card" style={{ marginBottom: 18, borderColor: 'var(--accent)' }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <Ban size={16} style={{ color: 'var(--danger)', flexShrink: 0, marginTop: 2 }} />
              <div>
                <div style={{ fontWeight: 700, fontSize: 13.5 }}>No diagnosis inferred</div>
                <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 2 }}>{data.safety_note}</div>
              </div>
            </div>
          </div>

          <div className="grid-2" style={{ gap: 16 }}>
            <div>
              <h3 style={{ fontSize: 14, marginBottom: 10 }}>
                Detected symptoms ({data.detected_symptoms.length})
              </h3>
              {data.detected_symptoms.length ? (
                data.detected_symptoms.map((s, i) => <SymptomCard key={i} s={s} />)
              ) : (
                <div className="empty-state">
                  <div className="empty-state-title">No recognised symptoms</div>
                  <div className="empty-state-desc">Try one of the example phrases above.</div>
                </div>
              )}
            </div>

            <div>
              <h3 style={{ fontSize: 14, marginBottom: 10 }}>
                <AlertTriangle size={13} style={{ verticalAlign: -1, marginRight: 4 }} />
                Negated symptoms ({data.negated_symptoms.length})
              </h3>
              {data.negated_symptoms.length ? (
                data.negated_symptoms.map((s, i) => (
                  <div key={i} className="card-sm" style={{ marginBottom: 10, opacity: 0.75 }}>
                    <span className="badge badge-danger" style={{ textTransform: 'capitalize' }}>
                      not present: {s.symptom}
                    </span>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                      Denied in the text — not searched for terminology candidates.
                    </div>
                  </div>
                ))
              ) : (
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>None denied in this text.</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
