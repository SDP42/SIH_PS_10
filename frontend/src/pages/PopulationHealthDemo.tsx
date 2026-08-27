import { useQuery } from '@tanstack/react-query';
import { Users, FlaskConical, MapPin, Calendar, PieChart, ListOrdered } from 'lucide-react';
import { getPopulationDemo } from '../api';
import { useLanguage } from '../i18n/LanguageContext';

function Stat({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="stat-card">
      <div className="stat-card-label">{label}</div>
      <div className="stat-card-value">{value}</div>
      {sub && <div className="stat-card-sub">{sub}</div>}
    </div>
  );
}

function HBar({ label, value, max, tone }: { label: string; value: number; max: number; tone: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, marginBottom: 3 }}>
        <span>{label}</span>
        <span style={{ fontFamily: 'monospace', color: 'var(--text-muted)' }}>{value.toLocaleString()}</span>
      </div>
      <div style={{ height: 8, background: 'var(--border)', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: tone, borderRadius: 4 }} />
      </div>
    </div>
  );
}

const GENDER_COLORS: Record<string, string> = { Male: '#38bdf8', Female: '#f472b6', Other: '#a78bfa' };
const TRADITION_COLORS: Record<string, string> = { Ayurveda: '#2dd4bf', Siddha: '#fbbf24', Unani: '#fb7185' };

export default function PopulationHealthDemo() {
  const { t } = useLanguage();
  const { data, isLoading, isError } = useQuery({ queryKey: ['population-demo'], queryFn: getPopulationDemo });

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">
          <FlaskConical size={20} style={{ verticalAlign: -3, marginRight: 6 }} />
          {t('page_population_title')}
        </h1>
        <p className="page-desc">{t('page_population_desc')}</p>
      </div>

      {isLoading && (
        <div className="grid-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="stat-card"><div className="skeleton skeleton-title" /><div className="skeleton skeleton-line" /></div>
          ))}
        </div>
      )}

      {isError && (
        <div className="empty-state">
          <div className="empty-state-title">Could not load the population demo</div>
        </div>
      )}

      {data && !data.available && (
        <div className="empty-state">
          <div className="empty-state-icon"><FlaskConical size={22} /></div>
          <div className="empty-state-title">Synthetic dataset not generated yet</div>
          <div className="empty-state-desc">{data.message}</div>
        </div>
      )}

      {data?.available && data.overview && (
        <>
          <div className="grid-4" style={{ marginBottom: 20 }}>
            <Stat label="Synthetic patients" value={data.overview.total_patients.toLocaleString()} sub="Fabricated, not real" />
            <Stat label="Synthetic encounters" value={data.overview.total_encounters.toLocaleString()} sub={`${data.overview.regions_covered} regions`} />
            <Stat
              label="Date range"
              value={data.overview.date_range.from ? `${data.overview.date_range.from.slice(0, 7)} → ${data.overview.date_range.to?.slice(0, 7)}` : '—'}
              sub="Synthetic timeline"
            />
            <Stat label="Traditions represented" value={data.by_tradition?.length ?? 0} sub="Ayurveda / Siddha / Unani" />
          </div>

          <div className="grid-2" style={{ gap: 16, marginBottom: 20 }}>
            <div className="card">
              <div className="section-header">
                <div>
                  <div className="section-title"><PieChart size={14} style={{ verticalAlign: -2, marginRight: 5 }} />By gender</div>
                  <div className="section-subtitle">Synthetic patient count, by fabricated gender field.</div>
                </div>
              </div>
              {data.by_gender?.map((g) => (
                <HBar key={g.gender} label={g.gender} value={g.n} max={data.overview!.total_patients} tone={GENDER_COLORS[g.gender] || 'var(--accent)'} />
              ))}
            </div>

            <div className="card">
              <div className="section-header">
                <div>
                  <div className="section-title">By AYUSH tradition</div>
                  <div className="section-subtitle">Synthetic encounters — but attached to real NAMASTE codes.</div>
                </div>
              </div>
              {data.by_tradition?.map((t) => (
                <HBar key={t.tradition} label={t.tradition} value={t.n} max={data.overview!.total_encounters} tone={TRADITION_COLORS[t.tradition] || 'var(--accent)'} />
              ))}
            </div>
          </div>

          <div className="card" style={{ marginBottom: 20 }}>
            <div className="section-header">
              <div>
                <div className="section-title"><Calendar size={14} style={{ verticalAlign: -2, marginRight: 5 }} />Encounters over time</div>
                <div className="section-subtitle">Synthetic monthly volume — the "time" axis of the demo.</div>
              </div>
            </div>
            {data.by_month && data.by_month.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 110 }}>
                {data.by_month.map((m) => {
                  const max = Math.max(...data.by_month!.map((x) => x.n), 1);
                  return (
                    <div key={m.month} title={`${m.month}: ${m.n}`} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', height: '100%' }}>
                      <div style={{ width: '100%', maxWidth: 26, height: `${Math.max(4, (m.n / max) * 90)}px`, background: 'var(--accent)', borderRadius: 3 }} />
                      <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 4, whiteSpace: 'nowrap' }}>{m.month.slice(5)}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="card" style={{ marginBottom: 20 }}>
            <div className="section-header">
              <div>
                <div className="section-title"><ListOrdered size={14} style={{ verticalAlign: -2, marginRight: 5 }} />Most common conditions, nationally</div>
                <div className="section-subtitle">
                  The codes themselves are real NAMASTE terminology — only the encounter volume behind
                  them is synthetic. This is the ranking a government analyst would use to spot where
                  to focus, at realistic scale.
                </div>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>#</th><th>Tradition</th><th>Code</th><th>Condition</th><th>Encounters</th></tr></thead>
                <tbody>
                  {data.top_conditions_national?.map((c, i) => (
                    <tr key={`${c.tradition}-${c.namaste_code}`}>
                      <td className="num">{i + 1}</td>
                      <td><span className="badge" style={{ background: 'transparent', color: TRADITION_COLORS[c.tradition], border: `1px solid ${TRADITION_COLORS[c.tradition]}` }}>{c.tradition}</span></td>
                      <td><span className="td-code">{c.namaste_code}</span></td>
                      <td style={{ fontSize: 12.5 }}>{c.display}</td>
                      <td className="num">{c.encounters.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card" style={{ marginBottom: 20 }}>
            <div className="section-header">
              <div>
                <div className="section-title"><MapPin size={14} style={{ verticalAlign: -2, marginRight: 5 }} />By region</div>
                <div className="section-subtitle">Synthetic patient distribution across Indian states — a shape a Ministry dashboard would want, not a real census.</div>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Region</th><th>Patients</th><th>Encounters</th></tr></thead>
                <tbody>
                  {data.by_region?.map((r) => (
                    <tr key={r.region}>
                      <td>{r.region}</td>
                      <td className="num">{r.patients.toLocaleString()}</td>
                      <td className="num">{r.encounters.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <div className="section-header">
              <div>
                <div className="section-title"><ListOrdered size={14} style={{ verticalAlign: -2, marginRight: 5 }} />Leading condition, by region</div>
                <div className="section-subtitle">
                  What's most common where — the drill-down a state health department would actually
                  want, so outreach can be targeted region by region.
                </div>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Region</th><th>Top condition</th><th>Encounters</th><th>2nd &amp; 3rd</th></tr></thead>
                <tbody>
                  {data.top_conditions_by_region?.map((r) => (
                    <tr key={r.region}>
                      <td style={{ fontWeight: 600 }}>{r.region}</td>
                      <td style={{ fontSize: 12.5 }}>{r.top_conditions[0]?.display || '—'}</td>
                      <td className="num">{r.top_conditions[0]?.encounters ?? '—'}</td>
                      <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {r.top_conditions.slice(1).map((c) => c.display).join('; ') || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
