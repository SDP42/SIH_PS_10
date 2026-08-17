import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMappings, getMappingById, type Mapping, type MappingDetail } from '../api';
import { GitMerge, Search, X, ChevronLeft, ChevronRight, Filter } from 'lucide-react';

function ConfBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const cls = pct >= 90 ? 'high' : pct >= 70 ? '' : 'medium';
  return (
    <div className="confidence-bar">
      <div className="confidence-track"><div className="confidence-fill" style={{ width: `${pct}%` }} /></div>
      <span className="confidence-pct">{pct}%</span>
    </div>
  );
}

function MappingDetailPanel({ id, onClose }: { id: number; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ['mapping', id],
    queryFn: () => getMappingById(id),
  });

  return (
    <div className="detail-overlay" onClick={onClose}>
      <div className="detail-panel" onClick={e => e.stopPropagation()}>
        <div className="detail-header">
          <div className="detail-header-title">Mapping Detail</div>
          <button className="btn btn-ghost btn-sm" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="detail-body">
          {isLoading ? (
            <div>
              {[0,1,2,3,4].map(i => <div key={i} className="skeleton skeleton-line" style={{marginBottom:12}} />)}
            </div>
          ) : data ? (
            <>
              <div className="detail-section">
                <div className="detail-section-label">SOURCE</div>
                <div className="detail-field">
                  <div className="detail-field-label">System</div>
                  <div className="detail-field-value">{data.source_system}</div>
                </div>
                <div className="detail-field">
                  <div className="detail-field-label">Code</div>
                  <span className="detail-field-code">{data.source_code}</span>
                </div>
                <div className="detail-field">
                  <div className="detail-field-label">Term</div>
                  <div className="detail-field-value">{data.source_display}</div>
                </div>
                {data.source_english && (
                  <div className="detail-field">
                    <div className="detail-field-label">English Name</div>
                    <div className="detail-field-value">{data.source_english}</div>
                  </div>
                )}
                {data.source_devanagari && (
                  <div className="detail-field">
                    <div className="detail-field-label">Devanagari</div>
                    <div className="detail-field-value" style={{ fontFamily: 'serif', fontSize: 15 }}>{data.source_devanagari}</div>
                  </div>
                )}
                {data.source_definition && (
                  <div className="detail-field">
                    <div className="detail-field-label">Definition</div>
                    <div className="detail-field-value" style={{ fontSize: 12.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{data.source_definition}</div>
                  </div>
                )}
              </div>

              <div className="detail-arrow">↓</div>

              <div className="detail-section">
                <div className="detail-section-label" style={{ color: 'var(--accent)' }}>
                  RELATIONSHIP · <span className={`badge badge-${data.equivalence === 'equivalent' ? 'equivalent' : 'related'}`}>{data.equivalence}</span>
                </div>
                <div className="detail-field">
                  <div className="detail-field-label">Confidence</div>
                  <ConfBar value={data.confidence} />
                </div>
              </div>

              <div className="detail-arrow">↓</div>

              <div className="detail-section">
                <div className="detail-section-label">TARGET</div>
                <div className="detail-field">
                  <div className="detail-field-label">System</div>
                  <div className="detail-field-value">{data.target_system}</div>
                </div>
                <div className="detail-field">
                  <div className="detail-field-label">Code</div>
                  <span className="detail-field-code">{data.target_code}</span>
                </div>
                <div className="detail-field">
                  <div className="detail-field-label">Title</div>
                  <div className="detail-field-value">{data.target_display}</div>
                </div>
              </div>

              <div className="detail-section" style={{ background: 'var(--bg-input)', borderRadius: 'var(--radius)', padding: 12 }}>
                <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-muted)' }}>
                  <div><div style={{ color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 2 }}>Status</div><span className={`badge badge-${data.status === 'validated' ? 'equivalent' : 'pending'}`}>{data.status}</span></div>
                  <div><div style={{ color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 2 }}>Version</div>{data.version}</div>
                  <div><div style={{ color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 2 }}>Mapping ID</div>#{data.id}</div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function MappingIntelligence() {
  const [q, setQ] = useState('');
  const [inputVal, setInputVal] = useState('');
  const [equivalence, setEquivalence] = useState('');
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const PAGE_SIZE = 15;

  const { data, isLoading, isError } = useQuery({
    queryKey: ['mappings', q, equivalence, page],
    queryFn: () => getMappings({ q: q || undefined, equivalence: equivalence || undefined, page, page_size: PAGE_SIZE }),
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setQ(inputVal);
    setPage(1);
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Mapping Intelligence</h1>
        <p className="page-desc">Discover, validate and manage cross-system terminology mappings between NAMASTE and ICD-11 TM2.</p>
      </div>

      {/* Mapping flow header */}
      <div className="mapping-flow">
        <div className="mapping-side">
          <div className="mapping-side-label">Source</div>
          <div className="mapping-side-sys">NAMASTE</div>
          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4 }}>National AYUSH Morbidity Terminologies</div>
        </div>
        <div className="mapping-divider" />
        <div className="mapping-arrow">→</div>
        <div className="mapping-divider" />
        <div className="mapping-side" style={{ textAlign: 'right' }}>
          <div className="mapping-side-label">Target</div>
          <div className="mapping-side-sys">ICD-11 TM2</div>
          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4 }}>WHO Traditional Medicine Module 2</div>
        </div>
      </div>

      {/* Search + filters */}
      <div className="card mb-4">
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 12 }}>
          <div className="input-with-icon" style={{ flex: 1 }}>
            <Search size={15} className="input-icon" />
            <input
              className="input"
              placeholder="Search source concept, target term, or code…"
              value={inputVal}
              onChange={e => setInputVal(e.target.value)}
            />
          </div>
          <button type="submit" className="btn btn-primary"><Search size={14} /> Search</button>
          {q && <button type="button" className="btn btn-outline btn-sm" onClick={() => { setQ(''); setInputVal(''); setPage(1); }}><X size={13} /> Clear</button>}
        </form>
        <div className="filter-row">
          <span className="filter-label"><Filter size={12} /> Relationship:</span>
          <select className="select" value={equivalence} onChange={e => { setEquivalence(e.target.value); setPage(1); }}>
            <option value="">All</option>
            <option value="equivalent">Equivalent</option>
            <option value="relatedto">Related To</option>
          </select>
          {data && <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>{data.total.toLocaleString()} mappings found</span>}
        </div>
      </div>

      {/* Table */}
      <div className="card">
        {isLoading ? (
          <div>
            {[0,1,2,3,4,5].map(i => (
              <div key={i} style={{ display: 'flex', gap: 16, padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
                {[1,2,1,1,0.8].map((w, j) => <div key={j} className="skeleton skeleton-line" style={{ flex: w }} />)}
              </div>
            ))}
          </div>
        ) : isError ? (
          <div className="empty-state">
            <div className="empty-state-icon">⚠️</div>
            <div className="empty-state-title">Backend Unavailable</div>
            <div className="empty-state-desc">Ensure the FastAPI server is running at <code>http://localhost:8000</code></div>
          </div>
        ) : !data?.results.length ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <div className="empty-state-title">No mappings found</div>
            <div className="empty-state-desc">Try different search terms or clear the filter.</div>
          </div>
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Source Concept</th>
                    <th>Source Code</th>
                    <th>Target Concept</th>
                    <th>Target Code</th>
                    <th>Relationship</th>
                    <th>Confidence</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((m: Mapping) => (
                    <tr key={m.id} className="cursor-pointer" onClick={() => setSelectedId(m.id)}>
                      <td>
                        <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{m.source_display}</div>
                        {m.source_english && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{m.source_english}</div>}
                      </td>
                      <td><span className="td-code">{m.source_code}</span></td>
                      <td style={{ maxWidth: 200 }}>
                        <div className="truncate" style={{ fontSize: 13 }}>{m.target_display}</div>
                      </td>
                      <td><span className="td-code">{m.target_code}</span></td>
                      <td>
                        <span className={`badge badge-${m.equivalence === 'equivalent' ? 'equivalent' : 'related'}`}>
                          {m.equivalence === 'equivalent' ? 'Equivalent' : 'Related'}
                        </span>
                      </td>
                      <td><ConfBar value={m.confidence} /></td>
                      <td>
                        <button className="btn btn-ghost btn-sm" onClick={e => { e.stopPropagation(); setSelectedId(m.id); }}>
                          View →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {data.total_pages > 1 && (
              <div className="pagination">
                <button className="page-btn" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
                  <ChevronLeft size={14} />
                </button>
                {Array.from({ length: Math.min(7, data.total_pages) }, (_, i) => {
                  const pg = page <= 4 ? i + 1 : page - 3 + i;
                  if (pg < 1 || pg > data.total_pages) return null;
                  return (
                    <button key={pg} className={`page-btn${pg === page ? ' active' : ''}`} onClick={() => setPage(pg)}>{pg}</button>
                  );
                })}
                <button className="page-btn" disabled={page === data.total_pages} onClick={() => setPage(p => p + 1)}>
                  <ChevronRight size={14} />
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {selectedId !== null && (
        <MappingDetailPanel id={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </div>
  );
}
