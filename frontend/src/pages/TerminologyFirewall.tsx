import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ShieldAlert, ShieldCheck, ShieldQuestion, PlayCircle, History } from 'lucide-react';
import { checkFirewall, getFirewallHistory, type FirewallResult } from '../api';

const VERDICT_STYLE: Record<string, { badge: string; icon: JSX.Element; label: string }> = {
  ACCEPTED: { badge: 'badge-equivalent', icon: <ShieldCheck size={16} />, label: 'ACCEPTED' },
  REVIEW_REQUIRED: { badge: 'badge-pending', icon: <ShieldQuestion size={16} />, label: 'REVIEW REQUIRED' },
  REJECTED: { badge: 'badge-danger', icon: <ShieldAlert size={16} />, label: 'REJECTED' },
};

const SAMPLE_BUNDLE = `{
  "resourceType": "Bundle",
  "type": "collection",
  "entry": [
    {
      "resource": {
        "resourceType": "Condition",
        "id": "c1",
        "clinicalStatus": { "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active" }] },
        "subject": { "reference": "Patient/demo" },
        "code": { "coding": [{ "system": "http://namaste.terminology/CodeSystem/ayurveda-morbidity", "code": "AA-1" }] }
      }
    }
  ]
}`;

export default function TerminologyFirewall() {
  const [apiKey, setApiKey] = useState('');
  const [bundleText, setBundleText] = useState(SAMPLE_BUNDLE);
  const [result, setResult] = useState<FirewallResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { data: historyData, refetch } = useQuery({ queryKey: ['firewall-history'], queryFn: getFirewallHistory });

  async function runCheck() {
    setError(null);
    setResult(null);
    let bundle: Record<string, unknown>;
    try {
      bundle = JSON.parse(bundleText);
    } catch {
      setError('That is not valid JSON.');
      return;
    }
    setLoading(true);
    try {
      const r = await checkFirewall(bundle, apiKey);
      setResult(r);
      refetch();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">
          <ShieldAlert size={20} style={{ verticalAlign: -3, marginRight: 6 }} />
          Terminology Firewall
        </h1>
        <p className="page-desc">
          A clinical terminology quality gateway for external EMRs — composes this service's existing
          code-existence check, WHO drift registry, and dual-coding translate logic into one
          accept / reject / review verdict for an incoming FHIR Bundle. Never modifies the Bundle,
          the mapping registry, or the review queue — it's advisory, not a mutation.
        </p>
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <div className="section-header">
          <div>
            <div className="section-title">Check a Bundle</div>
            <div className="section-subtitle">
              Needs an API key with <code>bundle:write</code> scope (a <code>fhir_integration</code> or
              <code> admin</code> key from the Developer Portal).
            </div>
          </div>
        </div>
        <input
          className="input"
          placeholder="X-API-Key (nsk_fhir_... or nsk_admin_...)"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          style={{ width: '100%', marginBottom: 10, fontFamily: 'monospace', fontSize: 12.5 }}
        />
        <textarea
          className="input"
          style={{ width: '100%', minHeight: 220, fontFamily: 'monospace', fontSize: 12.5, resize: 'vertical' }}
          value={bundleText}
          onChange={(e) => setBundleText(e.target.value)}
        />
        <div style={{ marginTop: 10 }}>
          <button className="btn btn-primary" disabled={!apiKey.trim() || loading} onClick={runCheck}>
            <PlayCircle size={14} /> {loading ? 'Checking…' : 'Run firewall check'}
          </button>
        </div>
        {error && <div style={{ color: 'var(--danger)', fontSize: 12.5, marginTop: 10 }}>{error}</div>}
      </div>

      {result && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            {VERDICT_STYLE[result.verdict]?.icon}
            <span className={`badge ${VERDICT_STYLE[result.verdict]?.badge}`} style={{ fontSize: 13, padding: '6px 14px' }}>
              {VERDICT_STYLE[result.verdict]?.label}
            </span>
            <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{result.checked_conditions} Condition(s) checked</span>
          </div>

          {result.results.map((r, i) => (
            <div key={i} className="card-sm" style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span className="td-code">{r.source_code || r.resource_id || `resource #${i + 1}`}</span>
                <span className={`badge ${VERDICT_STYLE[r.verdict]?.badge}`} style={{ fontSize: 10.5 }}>{r.verdict}</span>
              </div>
              {r.issues.length > 0 ? (
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, color: 'var(--text-secondary)' }}>
                  {r.issues.map((issue, j) => <li key={j}>{issue}</li>)}
                </ul>
              ) : (
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>No issues found.</div>
              )}
            </div>
          ))}

          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>{result.disclaimer}</div>
        </div>
      )}

      <div className="card">
        <div className="section-header">
          <div>
            <div className="section-title"><History size={14} style={{ verticalAlign: -2, marginRight: 5 }} />Recent decisions</div>
          </div>
        </div>
        {historyData?.decisions.length ? (
          <div className="table-wrap">
            <table>
              <thead><tr><th>When</th><th>Verdict</th><th>Conditions checked</th><th>Decided by</th></tr></thead>
              <tbody>
                {historyData.decisions.map((d: any) => (
                  <tr key={d.id}>
                    <td style={{ fontSize: 11.5 }}>{new Date(d.decided_at).toLocaleString()}</td>
                    <td><span className={`badge ${VERDICT_STYLE[d.verdict]?.badge}`}>{d.verdict}</span></td>
                    <td>{d.checked_conditions}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: 11.5 }}>{d.decided_by}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state"><div className="empty-state-title">No checks run yet</div></div>
        )}
      </div>
    </div>
  );
}
