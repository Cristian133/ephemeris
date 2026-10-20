import { useRef } from 'react'
import { getSunshine } from '../api/client'
import type { SunshineResponse } from '../api/types'
import { ExportButtons } from '../components/ExportButtons'
import { PeriodControls } from '../components/PeriodControls'
import { MonthlyBandChart } from '../components/charts/MonthlyBandChart'
import { useLocation } from '../context/LocationContext'
import { useMeteoQuery } from '../hooks/useMeteoQuery'
import { formatHours, formatPct, MONTH_LABELS } from '../utils/meteo'

const FAILURE = 'No se pudieron obtener las horas de sol.'

const labelStyle = { color: 'var(--text-muted)', fontSize: '0.85rem' } as const
const valueStyle = { margin: 0, fontSize: '1.5rem', fontWeight: 600 } as const

/** Horas de sol frente a las astronómicas, e insolación relativa (etapa 3). */
export default function SolReal() {
  const { location } = useLocation()
  const q = useMeteoQuery<SunshineResponse>(getSunshine, FAILURE)
  const chartRef = useRef<HTMLDivElement>(null)
  const data = q.data

  if (!location) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <section>
        <h1 style={{ marginBottom: '0.25rem' }}>Sol real</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
        <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Horas de sol frente a la duración astronómica del día (orto a ocaso). La insolación
          relativa es qué parte del día con Sol sobre el horizonte llega a brillar.
        </p>
        <p
          style={{
            margin: '0 0 1rem',
            fontSize: '0.8rem',
            color: 'var(--text-secondary)',
            borderLeft: '3px solid var(--series-2)',
            paddingLeft: '0.75rem',
          }}
        >
          Las horas de sol que modela el reanálisis directamente quedaron entre un 29 % y un 62 %
          por encima de lo medido con heliógrafo en siete estaciones de Argentina y España, y más del
          doble en Ushuaia. Por eso aquí se <strong>estiman a partir de la radiación</strong>, que el
          reanálisis reproduce mucho mejor (relación de Ångström-Prescott con a = {data?.angstrom_a ?? 0.29} y
          b = {data?.angstrom_b ?? 0.49}, calibrados con esas estaciones). En validación cruzada el
          error anual medio fue de un 7 %; los peores casos fueron Tucumán (un 15 % por debajo) y
          Ushuaia (un 31 % por encima). Fuera de ese rango de climas no está comprobada.
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
                <dt style={labelStyle}>Horas de sol por año</dt>
                <dd style={valueStyle}>{formatHours(data.annual.estimated_mean_hours, 0)}</dd>
              </div>
              <div>
                <dt style={labelStyle}>Astronómicas por año</dt>
                <dd style={valueStyle}>{formatHours(data.annual.astronomical_hours, 0)}</dd>
              </div>
              <div>
                <dt style={labelStyle}>Insolación relativa</dt>
                <dd style={valueStyle}>{formatPct(data.annual.estimated_relative_pct)}</dd>
              </div>
            </dl>
            <p style={{ margin: '0.75rem 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Estimadas desde la radiación. El modelo directo del reanálisis da{' '}
              {formatHours(data.annual.mean_hours, 0)} por año ({formatPct(data.annual.relative_pct)}
              ), que sobreestima. Celda {data.grid_latitude.toFixed(2)}°,{' '}
              {data.grid_longitude.toFixed(2)}° · fuente: {data.source} ·{' '}
              {data.annual.years_with_data} años con datos completos
            </p>
          </section>

          <section>
            <h2 style={{ marginBottom: '0.25rem' }}>Horas de sol por día, por mes</h2>
            <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              La línea azul es la estimación media del mes y la banda, su rango típico (percentiles
              10 a 90 entre los años). La punteada naranja es la duración astronómica del día y la
              gris, el modelo directo del reanálisis.
            </p>
            <div ref={chartRef}>
              <MonthlyBandChart
                yLabel="horas por día"
                format={(v) => formatHours(v)}
                referenceLabel="Astronómicas"
                extraLabel="Modelo del reanálisis"
                points={data.months.map((m) => ({
                  label: MONTH_LABELS[m.month - 1],
                  mean: m.estimated_mean_hours,
                  range:
                    m.estimated_p10_hours != null && m.estimated_p90_hours != null
                      ? [m.estimated_p10_hours, m.estimated_p90_hours]
                      : null,
                  reference: m.astronomical_hours,
                  extra: m.mean_hours ?? undefined,
                }))}
              />
            </div>
            <ExportButtons
              filename={`sol-real-${data.first_year}-${data.last_year}`}
              chartRef={chartRef}
              getCsvRows={() => [
                [
                  'mes',
                  'horas_estimadas_por_dia',
                  'mediana',
                  'p10',
                  'p90',
                  'horas_modelo_reanalisis_por_dia',
                  'horas_astronomicas_por_dia',
                  'insolacion_relativa_pct',
                  'anios_con_dato',
                ],
                ...data.months.map((m) => [
                  MONTH_LABELS[m.month - 1],
                  m.estimated_mean_hours != null ? Number(m.estimated_mean_hours.toFixed(2)) : null,
                  m.estimated_median_hours != null ? Number(m.estimated_median_hours.toFixed(2)) : null,
                  m.estimated_p10_hours != null ? Number(m.estimated_p10_hours.toFixed(2)) : null,
                  m.estimated_p90_hours != null ? Number(m.estimated_p90_hours.toFixed(2)) : null,
                  m.mean_hours != null ? Number(m.mean_hours.toFixed(2)) : null,
                  Number(m.astronomical_hours.toFixed(2)),
                  m.estimated_relative_pct != null ? Number(m.estimated_relative_pct.toFixed(1)) : null,
                  m.years_with_data,
                ]),
              ]}
            />

            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <th style={{ padding: '0.5rem 0' }}>Mes</th>
                  <th>Sol estimado</th>
                  <th>Típico (p10–p90)</th>
                  <th>Modelo del reanálisis</th>
                  <th>Astronómicas</th>
                  <th>Insolación</th>
                </tr>
              </thead>
              <tbody>
                {data.months.map((m) => (
                  <tr key={m.month} style={{ borderTop: '1px solid var(--gridline)' }}>
                    <td style={{ padding: '0.5rem 0', fontWeight: 600 }}>{MONTH_LABELS[m.month - 1]}</td>
                    <td>{formatHours(m.estimated_mean_hours)}</td>
                    <td>
                      {formatHours(m.estimated_p10_hours)} – {formatHours(m.estimated_p90_hours)}
                    </td>
                    <td style={{ color: 'var(--text-muted)' }}>{formatHours(m.mean_hours)}</td>
                    <td>{formatHours(m.astronomical_hours)}</td>
                    <td>{formatPct(m.estimated_relative_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  )
}
