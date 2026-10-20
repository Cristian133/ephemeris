import { useRef } from 'react'
import { getRain } from '../api/client'
import type { RainResponse } from '../api/types'
import { ExportButtons } from '../components/ExportButtons'
import { PeriodControls } from '../components/PeriodControls'
import { MonthlyBandChart } from '../components/charts/MonthlyBandChart'
import { RainYearlyChart } from '../components/charts/RainYearlyChart'
import { useLocation } from '../context/LocationContext'
import { useMeteoQuery } from '../hooks/useMeteoQuery'
import { formatMm, MONTH_LABELS } from '../utils/meteo'

const FAILURE = 'No se pudo obtener la lluvia.'

/** Estadísticas de lluvia mensuales y anuales del lugar (etapa 3). */
export default function Lluvia() {
  const { location } = useLocation()
  const q = useMeteoQuery<RainResponse>(getRain, FAILURE)
  const monthlyRef = useRef<HTMLDivElement>(null)
  const yearlyRef = useRef<HTMLDivElement>(null)
  const data = q.data

  if (!location) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <section>
        <h1 style={{ marginBottom: '0.25rem' }}>Lluvia</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
        <p style={{ margin: '0 0 1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Estadísticas del período elegido, a partir del reanálisis ERA5: el valor típico de una
          celda de unos 25 km, no el de una estación. Contrastado con ocho estaciones del SMN y la
          AEMET, en ciudades llanas el total anual quedó entre un 15 % por debajo y un 17 % por
          encima. <strong>En zonas montañosas, áridas o subpolares sobreestima mucho</strong>: en
          Mendoza y Salta dio de 2 a 3 veces lo medido, y en Ushuaia un 84 % más. La primera consulta
          de un lugar puede tardar unos segundos; después queda guardada.
        </p>
        <PeriodControls
          firstYear={q.firstYear}
          lastYear={q.lastYear}
          onFirstYear={q.setFirstYear}
          onLastYear={q.setLastYear}
          periodError={q.periodError}
          error={q.error}
          loading={q.loading}
        />
      </section>

      {data && (
        <>
          <section>
            <dl
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(10rem, 1fr))',
                gap: '1rem',
                margin: 0,
              }}
            >
              <div>
                <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Total anual medio</dt>
                <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
                  {formatMm(data.annual.mean_mm)}
                </dd>
              </div>
              <div>
                <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Rango típico</dt>
                <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
                  {formatMm(data.annual.p10_mm)} a {formatMm(data.annual.p90_mm)}
                </dd>
              </div>
              <div>
                <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Año más húmedo</dt>
                <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
                  {data.wettest_year
                    ? `${data.wettest_year.year} · ${formatMm(data.wettest_year.total_mm)}`
                    : '—'}
                </dd>
              </div>
              <div>
                <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Año más seco</dt>
                <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
                  {data.driest_year
                    ? `${data.driest_year.year} · ${formatMm(data.driest_year.total_mm)}`
                    : '—'}
                </dd>
              </div>
            </dl>
            <p style={{ margin: '0.75rem 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Celda {data.grid_latitude.toFixed(2)}°, {data.grid_longitude.toFixed(2)}° · fuente:{' '}
              {data.source} · {data.annual.years_with_data} años con datos completos
            </p>
          </section>

          <section>
            <h2 style={{ marginBottom: '0.25rem' }}>Por mes</h2>
            <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              La línea es la media del mes; la banda, el rango típico (percentiles 10 a 90 entre los
              años).
            </p>
            <div ref={monthlyRef}>
              <MonthlyBandChart
                yLabel="mm por mes"
                format={(v) => formatMm(v)}
                points={data.months.map((m) => ({
                  label: MONTH_LABELS[m.month - 1],
                  mean: m.mean_mm,
                  range: m.p10_mm != null && m.p90_mm != null ? [m.p10_mm, m.p90_mm] : null,
                }))}
              />
            </div>
            <ExportButtons
              filename={`lluvia-mensual-${data.first_year}-${data.last_year}`}
              chartRef={monthlyRef}
              getCsvRows={() => [
                ['mes', 'media_mm', 'mediana_mm', 'p10_mm', 'p90_mm', 'dias_de_lluvia', 'anios_con_dato'],
                ...data.months.map((m) => [
                  MONTH_LABELS[m.month - 1],
                  m.mean_mm != null ? Number(m.mean_mm.toFixed(1)) : null,
                  m.median_mm != null ? Number(m.median_mm.toFixed(1)) : null,
                  m.p10_mm != null ? Number(m.p10_mm.toFixed(1)) : null,
                  m.p90_mm != null ? Number(m.p90_mm.toFixed(1)) : null,
                  m.mean_rainy_days != null ? Number(m.mean_rainy_days.toFixed(1)) : null,
                  m.years_with_data,
                ]),
              ]}
            />

            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <th style={{ padding: '0.5rem 0' }}>Mes</th>
                  <th>Media</th>
                  <th>Mediana</th>
                  <th>Típico (p10–p90)</th>
                  <th>Días de lluvia</th>
                </tr>
              </thead>
              <tbody>
                {data.months.map((m) => (
                  <tr key={m.month} style={{ borderTop: '1px solid var(--gridline)' }}>
                    <td style={{ padding: '0.5rem 0', fontWeight: 600 }}>{MONTH_LABELS[m.month - 1]}</td>
                    <td>{formatMm(m.mean_mm)}</td>
                    <td>{formatMm(m.median_mm)}</td>
                    <td>
                      {formatMm(m.p10_mm)} – {formatMm(m.p90_mm)}
                    </td>
                    <td>{m.mean_rainy_days != null ? m.mean_rainy_days.toFixed(1) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ margin: '0.5rem 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Día de lluvia: {data.rainy_day_threshold_mm} mm o más (criterio de la OMM).
            </p>
          </section>

          <section>
            <h2 style={{ marginBottom: '0.25rem' }}>Por año</h2>
            <div ref={yearlyRef}>
              <RainYearlyChart years={data.yearly_totals} meanMm={data.annual.mean_mm} />
            </div>
            <ExportButtons
              filename={`lluvia-anual-${data.first_year}-${data.last_year}`}
              chartRef={yearlyRef}
              getCsvRows={() => [
                ['anio', 'total_mm'],
                ...data.yearly_totals.map((y) => [
                  y.year,
                  y.total_mm != null ? Number(y.total_mm.toFixed(1)) : null,
                ]),
              ]}
            />
          </section>
        </>
      )}
    </div>
  )
}
