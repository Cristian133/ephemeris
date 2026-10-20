import { useRef } from 'react'
import { getClouds } from '../api/client'
import type { CloudResponse } from '../api/types'
import { ExportButtons } from '../components/ExportButtons'
import { PeriodControls } from '../components/PeriodControls'
import { CloudDaysChart } from '../components/charts/CloudDaysChart'
import { MonthlyBandChart } from '../components/charts/MonthlyBandChart'
import { useLocation } from '../context/LocationContext'
import { useMeteoQuery } from '../hooks/useMeteoQuery'
import { formatPct, MONTH_LABELS } from '../utils/meteo'

const FAILURE = 'No se pudo obtener la nubosidad.'

/** Nubosidad media y días despejados, parciales y cubiertos (etapa 3). */
export default function Nubosidad() {
  const { location } = useLocation()
  const q = useMeteoQuery<CloudResponse>(getClouds, FAILURE)
  const bandRef = useRef<HTMLDivElement>(null)
  const daysRef = useRef<HTMLDivElement>(null)
  const data = q.data

  if (!location) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <section>
        <h1 style={{ marginBottom: '0.25rem' }}>Nubosidad</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
        <p style={{ margin: '0 0 1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Cobertura de nubes media de cada mes del período, a partir del reanálisis ERA5 (una celda
          de unos 25 km, no una estación). Un día se cuenta como despejado si su nubosidad media es
          de hasta 20 %, y como cubierto si es de 80 % o más. Contrastada con una sola estación
          (Hong Kong, observación visual del Observatorio, 1991-2020), la nubosidad anual de ERA5 fue
          de 64 % contra 68 % medido, con un error medio mensual de 6 puntos: de octubre a enero
          quedó entre 11 y 14 puntos por debajo. Con una estación no se puede generalizar.
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
                <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Nubosidad anual media</dt>
                <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
                  {formatPct(data.annual.mean_pct)}
                </dd>
              </div>
              <div>
                <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Rango típico</dt>
                <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
                  {formatPct(data.annual.p10_pct)} a {formatPct(data.annual.p90_pct)}
                </dd>
              </div>
            </dl>
            <p style={{ margin: '0.75rem 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Celda {data.grid_latitude.toFixed(2)}°, {data.grid_longitude.toFixed(2)}° · fuente:{' '}
              {data.source} · {data.annual.years_with_data} años con datos completos
            </p>
          </section>

          <section>
            <h2 style={{ marginBottom: '0.25rem' }}>Cobertura por mes</h2>
            <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              La línea es la media del mes; la banda, el rango típico (percentiles 10 a 90 entre los
              años).
            </p>
            <div ref={bandRef}>
              <MonthlyBandChart
                yLabel="nubosidad (%)"
                domain={[0, 100]}
                format={formatPct}
                points={data.months.map((m) => ({
                  label: MONTH_LABELS[m.month - 1],
                  mean: m.mean_pct,
                  range: m.p10_pct != null && m.p90_pct != null ? [m.p10_pct, m.p90_pct] : null,
                }))}
              />
            </div>
            <ExportButtons
              filename={`nubosidad-${data.first_year}-${data.last_year}`}
              chartRef={bandRef}
              getCsvRows={() => [
                [
                  'mes',
                  'nubosidad_media_pct',
                  'mediana_pct',
                  'p10_pct',
                  'p90_pct',
                  'dias_despejados',
                  'dias_parciales',
                  'dias_cubiertos',
                  'anios_con_dato',
                ],
                ...data.months.map((m) => [
                  MONTH_LABELS[m.month - 1],
                  m.mean_pct != null ? Number(m.mean_pct.toFixed(1)) : null,
                  m.median_pct != null ? Number(m.median_pct.toFixed(1)) : null,
                  m.p10_pct != null ? Number(m.p10_pct.toFixed(1)) : null,
                  m.p90_pct != null ? Number(m.p90_pct.toFixed(1)) : null,
                  m.clear_days != null ? Number(m.clear_days.toFixed(1)) : null,
                  m.partly_days != null ? Number(m.partly_days.toFixed(1)) : null,
                  m.overcast_days != null ? Number(m.overcast_days.toFixed(1)) : null,
                  m.years_with_data,
                ]),
              ]}
            />
          </section>

          <section>
            <h2 style={{ marginBottom: '0.25rem' }}>Tipo de día por mes</h2>
            <div ref={daysRef}>
              <CloudDaysChart months={data.months} />
            </div>
            <ExportButtons filename={`nubosidad-dias-${data.first_year}-${data.last_year}`} chartRef={daysRef} />
          </section>
        </>
      )}
    </div>
  )
}
