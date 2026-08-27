import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getConceptMapList, getFhirConceptMap, translateConcept, uploadBundle, buildProblemListEntry } from '../api';
import { useLanguage } from '../i18n/LanguageContext';
import { Search, Code2, Copy, CheckCircle, Zap, UploadCloud, FilePlus2 } from 'lucide-react';

// apiClient's response interceptor (see api/client.ts) rejects with
// error.response.data — typically FastAPI's {error, message} detail shape.
function extractErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === 'object') {
    const anyErr = err as any;
    return anyErr.detail?.message || anyErr.message || fallback;
  }
  return fallback;
}

const SAMPLE_BUNDLE_TEMPLATE = (code: string) => JSON.stringify({
  resourceType: 'Bundle',
  type: 'transaction',
  entry: [
    {
      resource: {
        resourceType: 'Condition',
        id: 'cond-demo-1',
        code: { coding: [{ system: 'http://namaste.terminology/CodeSystem/ayurveda-morbidity', code }] },
        subject: { reference: 'Patient/demo-patient' },
      },
    },
  ],
}, null, 2);

function BundleUploadTester() {
  const [bundleText, setBundleText] = useState(SAMPLE_BUNDLE_TEMPLATE('EB-10.18'));
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (bundle: Record<string, unknown>) => uploadBundle(bundle),
  });

  function handleUpload() {
    setErrorMsg(null);
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(bundleText);
    } catch {
      setErrorMsg('Bundle text is not valid JSON.');
      return;
    }
    mutation.mutate(parsed, {
      onError: (err) => setErrorMsg(extractErrorMessage(err, 'Bundle upload failed — are you logged in?')),
    });
  }

  return (
    <div>
      <div className="demo-banner" style={{ marginBottom: 12 }}>
        Real backend call — hits <code>POST /Bundle</code>, gated behind your ABHA Demo Mode session token.
        Resolves every Condition's NAMASTE coding against TM2 <em>and</em> Biomedicine independently and
        returns the Bundle with both codes appended (real double-coding, not two separate mock calls).
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <div>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Bundle JSON (edit the Condition code)</div>
          <textarea
            className="input"
            style={{ width: '100%', height: 300, fontFamily: 'monospace', fontSize: 11.5, resize: 'vertical' }}
            value={bundleText}
            onChange={(e) => setBundleText(e.target.value)}
          />
          <button className="btn btn-primary" style={{ marginTop: 10 }} disabled={mutation.isPending} onClick={handleUpload}>
            <UploadCloud size={14} /> {mutation.isPending ? 'Uploading…' : 'Upload Bundle'}
          </button>
        </div>
        <div>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Enriched Response</div>
          {errorMsg && <div className="empty-state"><div className="empty-state-title">{errorMsg}</div></div>}
          {mutation.data && (
            <div className="fhir-json" style={{ maxHeight: 300, overflow: 'auto' }}>
              {JSON.stringify(mutation.data, null, 2)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ProblemListBuilder() {
  const [code, setCode] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const mutation = useMutation({ mutationFn: () => buildProblemListEntry({ namaste_code: code }) });

  function handleBuild() {
    setErrorMsg(null);
    mutation.mutate(undefined, {
      onError: (err) => setErrorMsg(extractErrorMessage(err, 'Could not build a Problem List entry for this code.')),
    });
  }

  return (
    <div>
      <div className="demo-banner" style={{ marginBottom: 12 }}>
        Real backend call — hits <code>POST /api/problem-list/build</code>. Builds a FHIR{' '}
        <code>Condition</code> with <code>category=problem-list-item</code> carrying the NAMASTE coding
        plus real dual TM2/Biomedicine codes, the concrete "construct a FHIR ProblemList entry" deliverable.
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14, alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>NAMASTE Code</div>
          <input className="input" style={{ width: '100%' }} placeholder="e.g. SR10 (AAA-2.1)" value={code} onChange={(e) => setCode(e.target.value)} />
        </div>
        <button className="btn btn-primary" disabled={!code.trim() || mutation.isPending} onClick={handleBuild}>
          <FilePlus2 size={14} /> {mutation.isPending ? 'Building…' : 'Build Entry'}
        </button>
      </div>
      {errorMsg && <div className="empty-state"><div className="empty-state-title">{errorMsg}</div></div>}
      {mutation.data && (
        <div className="fhir-json" style={{ maxHeight: 420, overflow: 'auto' }}>
          {JSON.stringify(mutation.data, null, 2)}
        </div>
      )}
    </div>
  );
}

function TranslateTester() {
  const [system, setSystem] = useState('NAM');
  const [code, setCode] = useState('');
  const mutation = useMutation({ mutationFn: () => translateConcept({ system, code }) });

  return (
    <div>
      <div className="demo-banner" style={{ marginBottom: 12 }}>
        Real backend call — hits <code>GET /ConceptMap/$translate</code> live. Checks the curated
        registry first, falls back to the AI engine, and returns <code>result:false</code> /{' '}
        <code>unmatched</code> when nothing is validated rather than guessing.
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Source System</div>
          <select className="select" value={system} onChange={(e) => setSystem(e.target.value)}>
            <option value="NAM">NAM (Ayurveda Morbidity)</option>
            <option value="NSM">NSM (Siddha Morbidity)</option>
            <option value="NUM">NUM (Unani Morbidity)</option>
            <option value="AST">AST (Ayurveda Standard)</option>
          </select>
        </div>
        <div style={{ flex: 1, minWidth: 180 }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Source Code</div>
          <input className="input" placeholder="e.g. AAA-1" value={code} onChange={(e) => setCode(e.target.value)} />
        </div>
        <button className="btn btn-primary" disabled={!code.trim() || mutation.isPending} onClick={() => mutation.mutate()}>
          <Zap size={14} /> {mutation.isPending ? 'Translating…' : 'Run $translate'}
        </button>
      </div>

      {mutation.isError && (
        <div className="empty-state"><div className="empty-state-title">Translate failed</div></div>
      )}
      {mutation.data && (
        <div className="fhir-json" style={{ maxHeight: 480, overflow: 'auto' }}>
          {JSON.stringify(mutation.data, null, 2)}
        </div>
      )}
    </div>
  );
}

export default function FhirWorkspace() {
  const { t } = useLanguage();
  const [tab, setTab] = useState<'browse' | 'translate' | 'bundle' | 'problemlist'>('browse');
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [copied, setCopied] = useState(false);

  const { data: bundle, isLoading: bundleLoading } = useQuery({
    queryKey: ['fhir-bundle'],
    queryFn: getConceptMapList,
  });

  const { data: conceptMap, isLoading: cmLoading } = useQuery({
    queryKey: ['fhir-conceptmap', selectedCode],
    queryFn: () => getFhirConceptMap(selectedCode!),
    enabled: !!selectedCode,
  });

  const filteredCodes = (bundle?.available_codes || []).filter(c =>
    c.toLowerCase().includes(searchTerm.toLowerCase())
  );

  function handleCopy() {
    if (conceptMap) {
      navigator.clipboard.writeText(JSON.stringify(conceptMap, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">{t('page_fhir_title')}</h1>
        <p className="page-desc">{t('page_fhir_desc')}</p>
      </div>

      <div className="tabs">
        <button className={`tab${tab === 'browse' ? ' active' : ''}`} onClick={() => setTab('browse')}>Browse ConceptMaps</button>
        <button className={`tab${tab === 'translate' ? ' active' : ''}`} onClick={() => setTab('translate')}>$translate (Live)</button>
        <button className={`tab${tab === 'bundle' ? ' active' : ''}`} onClick={() => setTab('bundle')}>Bundle Upload (Double-Coding)</button>
        <button className={`tab${tab === 'problemlist' ? ' active' : ''}`} onClick={() => setTab('problemlist')}>Problem List Builder</button>
      </div>

      {tab === 'translate' ? (
        <div className="card"><TranslateTester /></div>
      ) : tab === 'bundle' ? (
        <div className="card"><BundleUploadTester /></div>
      ) : tab === 'problemlist' ? (
        <div className="card"><ProblemListBuilder /></div>
      ) : (
      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 16, height: 'calc(100vh - 260px)' }}>
        {/* Left panel: code list */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8, color: 'var(--text-primary)' }}>
              NAMASTE Codes
              {bundle && <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 6 }}>({bundle.total})</span>}
            </div>
            <div className="input-with-icon">
              <Search size={13} className="input-icon" />
              <input className="input" style={{ width: '100%', paddingLeft: 30 }} placeholder="Filter codes…" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
            </div>
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {bundleLoading ? (
              [0,1,2,3,4,5,6,7].map(i => <div key={i} className="skeleton skeleton-line" style={{ margin: '8px 0' }} />)
            ) : filteredCodes.map(code => (
              <div
                key={code}
                onClick={() => setSelectedCode(code)}
                style={{
                  padding: '8px 10px', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 12,
                  fontFamily: 'monospace', color: selectedCode === code ? 'var(--accent)' : 'var(--text-secondary)',
                  background: selectedCode === code ? 'var(--accent-dim)' : 'transparent',
                  marginBottom: 2, transition: 'all .1s', border: `1px solid ${selectedCode === code ? 'var(--accent-dim)' : 'transparent'}`,
                }}
              >
                {code}
              </div>
            ))}
          </div>
        </div>

        {/* Right panel: FHIR JSON */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {!selectedCode ? (
            <div className="empty-state" style={{ margin: 'auto' }}>
              <div className="empty-state-icon">📋</div>
              <div className="empty-state-title">Select a NAMASTE code</div>
              <div className="empty-state-desc">Click any code on the left to view its FHIR R4 ConceptMap.</div>
            </div>
          ) : cmLoading ? (
            <div style={{ padding: 20 }}>
              {[0,1,2,3,4,5].map(i => <div key={i} className="skeleton skeleton-line" style={{ marginBottom: 12 }} />)}
            </div>
          ) : conceptMap ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, flexShrink: 0 }}>
                <Code2 size={16} color="var(--accent)" />
                <div style={{ fontWeight: 700, fontSize: 14 }}>{conceptMap.title}</div>
                <span className="badge badge-active" style={{ marginLeft: 'auto' }}>{conceptMap.status}</span>
                <button className="btn btn-outline btn-sm" onClick={handleCopy}>
                  {copied ? <CheckCircle size={13} color="var(--success)" /> : <Copy size={13} />}
                  {copied ? 'Copied!' : 'Copy JSON'}
                </button>
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginBottom: 12, flexShrink: 0 }}>
                Publisher: {conceptMap.publisher} · Version: {conceptMap.version} · Date: {conceptMap.date}
              </div>
              <div className="fhir-json" style={{ flex: 1, overflow: 'auto' }}>
                {JSON.stringify(conceptMap, null, 2)}
              </div>
            </>
          ) : null}
        </div>
      </div>
      )}
    </div>
  );
}
