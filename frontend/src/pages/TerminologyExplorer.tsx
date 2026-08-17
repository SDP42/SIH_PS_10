import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getConcepts, searchConcepts, type ConceptResult } from '../api';
import { Search, Filter, X, ChevronRight, BookOpen } from 'lucide-react';

const SYSTEMS = [
  { id: '', label: 'All Systems' },
  { id: 'namaste', label: 'NAMASTE' },
  { id: 'icd11', label: 'ICD-11 TM2' },
];

export default function TerminologyExplorer() {
  const [system, setSystem] = useState('namaste');
  const [q, setQ] = useState('');
  const [inputVal, setInputVal] = useState('');
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState<'registry' | 'search'>('registry');

  const browsing = useQuery({
    queryKey: ['concepts', system, page],
    queryFn: () => getConcepts({ system, page, page_size: 20 }),
    enabled: activeTab === 'registry',
  });

  const searching = useQuery({
    queryKey: ['search', q, system],
    queryFn: () => searchConcepts({ q, system: system || 'both', page_size: 30 }),
    enabled: activeTab === 'search' && q.length > 1,
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setQ(inputVal.trim());
    setActiveTab('search');
    setPage(1);
  }

  const data = activeTab === 'search' ? searching : browsing;
  const results: ConceptResult[] = activeTab === 'search'
    ? (searching.data?.results || [])
    : (browsing.data?.results || []);
  const total = activeTab === 'search'
    ? (searching.data?.total || 0)
    : (browsing.data?.total || 0);
  const totalPages = browsing.data?.total_pages || 1;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Terminology Explorer</h1>
        <p className="page-desc">Explore standardized traditional medicine concepts and their cross-system relationships.</p>
      </div>

      <div className="demo-banner">
        ⚠ <strong>Simulated Demo Environment:</strong> Terminology data is real and database-backed. Code-translation and comparison features are in beta.
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button className={`tab${activeTab === 'registry' ? ' active' : ''}`} onClick={() => setActiveTab('registry')}>
          <BookOpen size={14} /> Registry Browser
        </button>
        <button className={`tab${activeTab === 'search' ? ' active' : ''}`} onClick={() => setActiveTab('search')}>
          <Search size={14} /> Concept Search
        </button>
      </div>

      {/* Search + filters */}
      <div className="card mb-4">
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 12 }}>
          <div className="input-with-icon" style={{ flex: 1 }}>
            <Search size={15} className="input-icon" />
            <input
              className="input"
              placeholder="Search NAMASTE, Ayurveda, Siddha, Unani or ICD-11 terminology…"
              value={inputVal}
              onChange={e => setInputVal(e.target.value)}
            />
          </div>
          <button type="submit" className="btn btn-primary"><Search size={14} /> Search</button>
          {q && (
            <button type="button" className="btn btn-outline btn-sm" onClick={() => { setQ(''); setInputVal(''); setActiveTab('registry'); }}>
              <X size={13} /> Clear
            </button>
          )}
        </form>

        <div className="filter-row">
          <span className="filter-label"><Filter size={12} /> System:</span>
          {SYSTEMS.map(s => (
            <button
              key={s.id}
              className={`btn btn-sm ${system === s.id ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => { setSystem(s.id); setPage(1); }}
            >
              {s.label}
            </button>
          ))}
          <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
            {total.toLocaleString()} concepts
          </span>
        </div>
      </div>

      {/* Results */}
      <div className="card">
        <div className="section-header" style={{ marginBottom: 12 }}>
          <div className="section-title">Terminology Concepts · {total.toLocaleString()} results</div>
          {activeTab === 'registry' && totalPages > 1 && (
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn btn-ghost btn-sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', padding: '4px 8px' }}>{page} / {totalPages}</span>
              <button className="btn btn-ghost btn-sm" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
            </div>
          )}
        </div>

        {data.isLoading ? (
          <div>
            {[0,1,2,3,4,5].map(i => (
              <div key={i} style={{ display: 'flex', gap: 16, padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
                <div className="skeleton" style={{ width: 70, height: 14 }} />
                <div className="skeleton skeleton-line" style={{ flex: 1 }} />
                <div className="skeleton" style={{ width: 50, height: 14 }} />
              </div>
            ))}
          </div>
        ) : data.isError ? (
          <div className="empty-state">
            <div className="empty-state-icon">⚠️</div>
            <div className="empty-state-title">Backend Unavailable</div>
            <div className="empty-state-desc">Make sure the FastAPI server is running: <code>uvicorn app.main:app --reload</code></div>
          </div>
        ) : results.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <div className="empty-state-title">{q ? 'No results found' : 'No concepts loaded'}</div>
            <div className="empty-state-desc">{q ? `No concepts match "${q}"` : 'Select a system and try browsing.'}</div>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Concept</th>
                  <th>System</th>
                  <th>Code</th>
                  <th>English Name</th>
                  <th>Definition</th>
                </tr>
              </thead>
              <tbody>
                {results.map((c, i) => (
                  <tr key={`${c.code}-${i}`}>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 13 }}>{c.display || c.code}</div>
                    </td>
                    <td>
                      <span className={`badge badge-${c.system_id === 'namaste' ? 'active' : 'related'}`}>
                        {c.system}
                      </span>
                    </td>
                    <td><span className="td-code">{c.code}</span></td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>{c.name_english || '—'}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 11.5, maxWidth: 200 }}>
                      <div className="truncate">{(c as any).definition || '—'}</div>
                    </td>
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
