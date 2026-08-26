import { useQuery } from '@tanstack/react-query';
import { Users, FlaskConical, MapPin, Calendar, PieChart } from 'lucide-react';
import { getPopulationDemo } from '../api';

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
  const { data, isLoading, isError } = useQuery({ queryKey: ['population-demo'], queryFn: getPopulationDemo });

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">
          <FlaskConical size={20} style={{ verticalAlign: -3, marginRight: 6 }} />
          Population Health Demo
        </h1>
        <p className="page-desc">
          An illustration of what a national AYUSH population-health view could look like at realistic
          volume — gender, region, and time breakdowns for a government/Ministry stakeholder to picture.
        </p>
      </div>

      <div
        style={{
          background: 'repeating-linear-gradient(135deg, rgba(251,191,36,0.12), rgba(251,191,36,0.12) 12px, rgba(251,191,36,0.06) 12px, rgba(251,191,36,0.06) 24px)',
          border: '2px solid var(--warning)',
          borderRadius: 12,
          padding: '16px 18px',
          marginBottom: 20,
          display: 'flex',
          gap: 12,
          alignItems: 'flex-start',
        }}
      >
        <FlaskConical size={20} style={{ color: 'var(--warning)', flexShrink: 0, marginTop: 2 }} />
        <div>
          <div style={{ fontWeight: 800, fontSize: 14.5, color: 'var(--warning)', letterSpacing: 0.3 }}>
            100% SYNTHETIC DEMONSTRATION DATA — NO REAL PATIENTS
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 4 }}>
            {data?.disclaimer || 'Every patient, encounter, and demographic figure on this page is fabricated by scripts/generate_synthetic_population.py. It illustrates dashboard shape at realistic volume, not real usage — see the Analytics page for this service’s real, live-computed metrics.'}
          </div>
        </div>
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

          <div className="card">
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
        </>
      )}
    </div>
  );
}
