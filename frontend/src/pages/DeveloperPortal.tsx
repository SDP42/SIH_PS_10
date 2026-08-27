import { useEffect, useState } from 'react';
import { useLanguage } from '../i18n/LanguageContext';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, Copy, RefreshCw, Ban, PlayCircle, Terminal, ShieldCheck } from 'lucide-react';
import {
  createApiClient, createApiKey, listApiKeys, rotateApiKey, revokeApiKey, getApiKeyUsage, getApiScopes,
  type ApiKeyCreated, type ApiKeyMeta,
} from '../api';
import { BASE_URL } from '../api/client';

const KEY_TYPES = ['sandbox', 'readonly', 'translation', 'fhir_integration', 'admin'];

function CopyableSecret({ secret }: { secret: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <code style={{ fontSize: 12.5, background: 'var(--bg-input)', padding: '6px 10px', borderRadius: 6, wordBreak: 'break-all' }}>
        {secret}
      </code>
      <button
        className="btn btn-ghost btn-sm"
        onClick={() => { navigator.clipboard.writeText(secret); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
      >
        <Copy size={13} /> {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  );
}

function CreateKeyPanel({ onCreated }: { onCreated: (k: ApiKeyCreated) => void }) {
  const [clientName, setClientName] = useState('');
  const [org, setOrg] = useState('');
  const [keyType, setKeyType] = useState('sandbox');

  const mutation = useMutation({
    mutationFn: async () => {
      const client = await createApiClient(clientName.trim(), org.trim() || undefined);
      return createApiKey({ client_id: client.id, key_type: keyType, label: `${clientName} — ${keyType}` });
    },
    onSuccess: onCreated,
  });

  return (
    <div className="card">
      <div className="section-header">
        <div>
          <div className="section-title"><KeyRound size={14} style={{ verticalAlign: -2, marginRight: 5 }} />Generate an API key</div>
          <div className="section-subtitle">Registers a new client and issues a key in one step — exactly what an EMR vendor would do first.</div>
        </div>
      </div>
      <div className="filter-row" style={{ gap: 10, marginBottom: 12 }}>
        <input className="input" placeholder="Client name, e.g. Apollo Hospitals EMR" value={clientName} onChange={(e) => setClientName(e.target.value)} style={{ flex: 2, minWidth: 200 }} />
        <input className="input" placeholder="Organization (optional)" value={org} onChange={(e) => setOrg(e.target.value)} style={{ flex: 1, minWidth: 160 }} />
        <select className="select" value={keyType} onChange={(e) => setKeyType(e.target.value)}>
          {KEY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <button className="btn btn-primary" disabled={!clientName.trim() || mutation.isPending} onClick={() => mutation.mutate()}>
          {mutation.isPending ? 'Creating…' : 'Create key'}
        </button>
      </div>

      {mutation.data && (
        <div className="demo-banner" style={{ alignItems: 'flex-start', background: 'rgba(34,197,94,0.1)', borderColor: 'rgba(34,197,94,0.3)', color: '#4ade80' }}>
          <ShieldCheck size={14} style={{ flexShrink: 0, marginTop: 3 }} />
          <span>
            <strong>{mutation.data.warning}</strong>
            <div style={{ marginTop: 8 }}><CopyableSecret secret={mutation.data.secret} /></div>
            <div style={{ marginTop: 6, fontSize: 11.5 }}>Type: {mutation.data.key_type} · Scopes: {mutation.data.scopes.join(', ')} · Rate limit: {mutation.data.rate_limit_per_minute}/min</div>
          </span>
        </div>
      )}
    </div>
  );
}

function TryItPanel({ defaultKey }: { defaultKey: string }) {
  const [apiKey, setApiKey] = useState(defaultKey);
  useEffect(() => { if (defaultKey) setApiKey(defaultKey); }, [defaultKey]);
  const [endpoint, setEndpoint] = useState<'search' | 'translate' | 'validate'>('search');
  const [q, setQ] = useState('fever');
  const [result, setResult] = useState<{ status: number; body: unknown } | null>(null);
  const [loading, setLoading] = useState(false);

  async function call() {
    setLoading(true);
    setResult(null);
    try {
      let res: Response;
      if (endpoint === 'search') {
        res = await fetch(`${BASE_URL}/api/v1/terminology/search?q=${encodeURIComponent(q)}`, { headers: { 'X-API-Key': apiKey } });
      } else if (endpoint === 'translate') {
        res = await fetch(`${BASE_URL}/api/v1/translate?system=NAM&code=${encodeURIComponent(q)}`, { headers: { 'X-API-Key': apiKey } });
      } else {
        res = await fetch(`${BASE_URL}/api/v1/validate-code`, {
          method: 'POST',
          headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' },
          body: JSON.stringify({ system: 'NAM', code: q }),
        });
      }
      const body = await res.json();
      setResult({ status: res.status, body });
    } catch (e) {
      setResult({ status: 0, body: { error: String(e) } });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="section-header">
        <div>
          <div className="section-title"><Terminal size={14} style={{ verticalAlign: -2, marginRight: 5 }} />Try it live</div>
          <div className="section-subtitle">Calls the real <code>/api/v1</code> endpoint from your browser, with your key in the <code>X-API-Key</code> header — the same request an EMR integration would make.</div>
        </div>
      </div>
      <div className="filter-row" style={{ gap: 10, marginBottom: 10 }}>
        <input className="input" placeholder="Paste an API key (nsk_...)" value={apiKey} onChange={(e) => setApiKey(e.target.value)} style={{ flex: 2, minWidth: 220, fontFamily: 'var(--font-mono, monospace)', fontSize: 12 }} />
        <select className="select" value={endpoint} onChange={(e) => setEndpoint(e.target.value as any)}>
          <option value="search">GET /api/v1/terminology/search</option>
          <option value="translate">GET /api/v1/translate</option>
          <option value="validate">POST /api/v1/validate-code</option>
        </select>
        <input className="input" placeholder="query / code" value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: 1, minWidth: 140 }} />
        <button className="btn btn-primary" disabled={!apiKey.trim() || loading} onClick={call}>
          <PlayCircle size={14} /> {loading ? 'Calling…' : 'Call'}
        </button>
      </div>
      {result && (
        <div>
          <span className={`badge ${result.status === 200 ? 'badge-equivalent' : result.status === 401 ? 'badge-pending' : 'badge-danger'}`}>
            HTTP {result.status}
          </span>
          <pre className="fhir-json" style={{ marginTop: 10, maxHeight: 300, overflow: 'auto', fontSize: 11.5 }}>
            {JSON.stringify(result.body, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function KeyRow({ k, onChanged }: { k: ApiKeyMeta; onChanged: () => void }) {
  const [usage, setUsage] = useState<Awaited<ReturnType<typeof getApiKeyUsage>> | null>(null);
  const rotateM = useMutation({ mutationFn: () => rotateApiKey(k.id), onSuccess: onChanged });
  const revokeM = useMutation({ mutationFn: () => revokeApiKey(k.id), onSuccess: onChanged });

  return (
    <tr>
      <td><span className="td-code">{k.key_prefix}…</span></td>
      <td><span className="badge badge-active">{k.key_type}</span></td>
      <td style={{ fontSize: 11.5 }}>{k.scopes.join(', ')}</td>
      <td>{k.rate_limit_per_minute}/min</td>
      <td>
        {k.revoked_at ? <span className="badge badge-danger">revoked</span> : <span className="badge badge-equivalent">active</span>}
      </td>
      <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>{k.last_used_at ? new Date(k.last_used_at).toLocaleString() : 'never'}</td>
      <td>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <button className="btn btn-ghost btn-sm" onClick={async () => setUsage(await getApiKeyUsage(k.id))}>Usage</button>
          {!k.revoked_at && (
            <>
              <button className="btn btn-outline btn-sm" disabled={rotateM.isPending} onClick={() => rotateM.mutate()}>
                <RefreshCw size={12} /> Rotate
              </button>
              <button className="btn btn-sm" style={{ background: '#dc2626', color: 'white' }} disabled={revokeM.isPending} onClick={() => revokeM.mutate()}>
                <Ban size={12} /> Revoke
              </button>
            </>
          )}
        </div>
        {rotateM.data && (
          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 11, color: 'var(--warning)', marginBottom: 4 }}>New secret (shown once):</div>
            <CopyableSecret secret={rotateM.data.secret} />
          </div>
        )}
        {usage && (
          <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
            {usage.total_requests} requests in last {usage.window_hours}h
            {usage.by_path.length > 0 && (
              <ul style={{ margin: '4px 0 0', paddingLeft: 16 }}>
                {usage.by_path.map((p) => <li key={p.path}>{p.path}: {p.n}</li>)}
              </ul>
            )}
          </div>
        )}
      </td>
    </tr>
  );
}

export default function DeveloperPortal() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [latestKey, setLatestKey] = useState('');

  const { data: keysData } = useQuery({ queryKey: ['api-keys'], queryFn: () => listApiKeys() });
  const { data: scopes } = useQuery({ queryKey: ['api-scopes'], queryFn: getApiScopes });

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title"><KeyRound size={20} style={{ verticalAlign: -3, marginRight: 6 }} />{t('page_developer_title')}</h1>
        <p className="page-desc">{t('page_developer_desc')}</p>
      </div>

      <div style={{ marginBottom: 18 }}>
        <CreateKeyPanel onCreated={(k) => { setLatestKey(k.secret); qc.invalidateQueries({ queryKey: ['api-keys'] }); }} />
      </div>

      <div style={{ marginBottom: 18 }}>
        <TryItPanel defaultKey={latestKey} />
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <div className="section-header">
          <div>
            <div className="section-title">Issued keys</div>
            <div className="section-subtitle">Secrets are never shown again after creation — only the prefix, for recognition.</div>
          </div>
        </div>
        {keysData?.keys.length ? (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Prefix</th><th>Type</th><th>Scopes</th><th>Rate limit</th><th>Status</th><th>Last used</th><th>Actions</th></tr></thead>
              <tbody>
                {keysData.keys.map((k) => (
                  <KeyRow key={k.id} k={k} onChanged={() => qc.invalidateQueries({ queryKey: ['api-keys'] })} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-title">No keys yet</div>
            <div className="empty-state-desc">Create one above to get started.</div>
          </div>
        )}
      </div>

      <div className="card">
        <div className="section-header">
          <div>
            <div className="section-title">Key types &amp; scopes reference</div>
            <div className="section-subtitle">Each key type grants a default scope set and rate limit; sandbox is intentionally the tightest.</div>
          </div>
        </div>
        {scopes && (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Key type</th><th>Default scopes</th><th>Rate limit</th></tr></thead>
              <tbody>
                {Object.entries(scopes.defaults_by_key_type).map(([type, s]) => (
                  <tr key={type}>
                    <td><span className="badge badge-active">{type}</span></td>
                    <td style={{ fontSize: 12 }}>{s.join(', ')}</td>
                    <td>{scopes.rate_limits_by_key_type[type]}/min</td>
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
