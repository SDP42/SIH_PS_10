import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getConceptMapList, getFhirConceptMap } from '../api';
import { Search, Code2, Copy, CheckCircle } from 'lucide-react';

export default function FhirWorkspace() {
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

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 16, height: 'calc(100vh - 200px)' }}>
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
    </div>
  );
}
