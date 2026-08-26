import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getConceptMapList, getFhirConceptMap, translateConcept } from '../api';
import { Search, Code2, Copy, CheckCircle, Zap } from 'lucide-react';

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
  const [tab, setTab] = useState<'browse' | 'translate'>('browse');
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
        <h1 className="page-title">FHIR Workspace</h1>
        <p className="page-desc">Browse FHIR R4 ConceptMap resources generated from the NAMASTE-ICD-11 mapping database.</p>
      </div>

      <div className="tabs">
        <button className={`tab${tab === 'browse' ? ' active' : ''}`} onClick={() => setTab('browse')}>Browse ConceptMaps</button>
        <button className={`tab${tab === 'translate' ? ' active' : ''}`} onClick={() => setTab('translate')}>$translate (Live)</button>
      </div>

      {tab === 'translate' ? (
        <div className="card"><TranslateTester /></div>
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
