import { useRef } from 'react'
import { getRealIrradiance } from '../api/client'
import type { IrradianceRealResponse } from '../api/types'
import { ExportButtons } from '../components/ExportButtons'
import { PeriodControls } from '../components/PeriodControls'
import { MonthlyBandChart } from '../components/charts/MonthlyBandChart'
import { useLocation } from '../context/LocationContext'
import { useMeteoQuery } from '../hooks/useMeteoQuery'
import { formatIndex, formatKwh, MONTH_LABELS } from '../utils/meteo'

const FAILURE = 'No se pudo obtener la radiación.'

const labelStyle = { color: 'var(--text-muted)', fontSize: '0.85rem' } as const
const valueStyle = { margin: 0, fontSize: '1.5rem', fontWeight: 600 } as const

/** Radiación solar real frente a la de cielo despejado, y panel con cielo real (etapa 3). */
export default function RadiacionReal() {
  const { location } = useLocation()
  const q = useMeteoQuery<IrradianceRealResponse>(getRealIrradiance, FAILURE)
  const chartRef = useRef<HTMLDivElement>(null)
  const data = q.data

  if (!location) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <section>
        <h1 style={{ marginBottom: '0.25rem' }}>Radiación real</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
        <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Energía solar global sobre una superficie horizontal, según el reanálisis ERA5, frente a la
          que llegaría con cielo despejado. El índice de claridad es el cociente: 1 sería un cielo
          limpio y baja con las nubes y la turbidez. En la Pampa Húmeda, la distribución de días
          según su claridad coincide con la medida por una red de piranómetros dentro de 4 puntos
          porcentuales; ERA5 tiene algo menos de días cubiertos (11 % contra 15 %), así que la
          radiación media puede salir algo alta. No está contrastada en zonas montañosas ni
          tropicales.
        </p>
        {data && (
          <p
            style={{
              margin: '0 0 1rem',
              fontSize: '0.8rem',
              color: 'var(--text-secondary)',
              borderLeft: `3px solid ${data.elevation_source === 'default' ? 'var(--series-2)' : 'var(--axis)'}`,
              paddingLeft: '0.75rem',
            }}
          >
            {data.elevation_source === 'default' ? (
              <>
                <strong>Ojo:</strong> no se pudo obtener la altitud de la celda y el cielo despejado
                se calculó a nivel del mar. En un lugar alto el techo real es mayor y el índice de
                claridad, menor que el que se muestra.
              </>
            ) : (
              <>
                El cielo despejado se calculó a {data.elevation_m.toLocaleString('es-AR', { maximumFractionDigits: 0 })} m
                de altitud (la que informa la fuente para la celda) y con turbidez típica (Linke{' '}
                {data.linke_turbidity}).
              </>
            )}
          </p>
        )}
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
                gridTemplateColumns: 'repeat(auto-fit, minmax(11rem, 1fr))',
                gap: '1rem',
                margin: 0,
              }}
            >
              <div>
                <dt style={labelStyle}>Radiación anual real</dt>
                <dd style={valueStyle}>{formatKwh(data.annual.mean_kwh, 0)}</dd>
              </div>
              <div>
                <dt style={labelStyle}>Con cielo despejado</dt>
                <dd style={valueStyle}>{formatKwh(data.annual.clear_sky_kwh, 0)}</dd>
              </div>
              <div>
                <dt style={labelStyle}>Índice de claridad</dt>
                <dd style={valueStyle}>{formatIndex(data.annual.clearness_index)}</dd>
              </div>
            </dl>
            <p style={{ margin: '0.75rem 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Celda {data.grid_latitude.toFixed(2)}°, {data.grid_longitude.toFixed(2)}° · fuente:{' '}
              {data.source} · {data.annual.years_with_data} años con datos completos
            </p>
          </section>

          <section>
            <h2 style={{ marginBottom: '0.25rem' }}>Energía diaria por mes</h2>
            <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              La línea azul es la media real del mes y la banda, su rango típico (percentiles 10 a
              90 entre los años). La punteada es lo que llegaría con cielo despejado.
            </p>
            <div ref={chartRef}>
              <MonthlyBandChart
                yLabel="kWh/m² por día"
                format={(v) => formatKwh(v)}
                referenceLabel="Cielo despejado"
                points={data.months.map((m) => ({
                  label: MONTH_LABELS[m.month - 1],
                  mean: m.mean_kwh,
                  range: m.p10_kwh != null && m.p90_kwh != null ? [m.p10_kwh, m.p90_kwh] : null,
                  reference: m.clear_sky_kwh,
                }))}
              />
            </div>
            <ExportButtons
              filename={`radiacion-real-${data.first_year}-${data.last_year}`}
              chartRef={chartRef}
              getCsvRows={() => [
                [
                  'mes',
                  'real_kwh_m2_dia',
                  'mediana',
                  'p10',
                  'p90',
                  'cielo_despejado_kwh_m2_dia',
                  'indice_de_claridad',
                  'anios_con_dato',
                ],
                ...data.months.map((m) => [
                  MONTH_LABELS[m.month - 1],
                  m.mean_kwh != null ? Number(m.mean_kwh.toFixed(2)) : null,
                  m.median_kwh != null ? Number(m.median_kwh.toFixed(2)) : null,
                  m.p10_kwh != null ? Number(m.p10_kwh.toFixed(2)) : null,
                  m.p90_kwh != null ? Number(m.p90_kwh.toFixed(2)) : null,
                  Number(m.clear_sky_kwh.toFixed(2)),
                  m.clearness_index != null ? Number(m.clearness_index.toFixed(3)) : null,
                  m.years_with_data,
                ]),
              ]}
            />

            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <th style={{ padding: '0.5rem 0' }}>Mes</th>
                  <th>Real</th>
                  <th>Típico (p10–p90)</th>
                  <th>Cielo despejado</th>
                  <th>Claridad</th>
                </tr>
              </thead>
              <tbody>
                {data.months.map((m) => (
                  <tr key={m.month} style={{ borderTop: '1px solid var(--gridline)' }}>
                    <td style={{ padding: '0.5rem 0', fontWeight: 600 }}>{MONTH_LABELS[m.month - 1]}</td>
                    <td>{formatKwh(m.mean_kwh)}</td>
                    <td>
                      {formatKwh(m.p10_kwh)} – {formatKwh(m.p90_kwh)}
                    </td>
                    <td>{formatKwh(m.clear_sky_kwh)}</td>
                    <td>{formatIndex(m.clearness_index)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <h2 style={{ marginBottom: '0.25rem' }}>Panel solar fijo con cielo real</h2>
            <p style={{ margin: '0 0 0.75rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Panel en su inclinación anual óptima, mirando al ecuador (
              {data.panel.azimuth_deg === 0 ? 'norte' : 'sur'}). La estimación aplica a cada mes el
              índice de claridad del plano horizontal: supone que las nubes restan lo mismo a un
              panel inclinado, y no descuenta pérdidas del sistema (temperatura, inversor,
              suciedad). Es una referencia, no un dimensionamiento.
            </p>
            <dl
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(11rem, 1fr))',
                gap: '1rem',
                margin: 0,
              }}
            >
              <div>
                <dt style={labelStyle}>Inclinación óptima</dt>
                <dd style={valueStyle}>{data.panel.tilt_deg.toFixed(0)}°</dd>
              </div>
              <div>
                <dt style={labelStyle}>Con cielo despejado</dt>
                <dd style={valueStyle}>{formatKwh(data.panel.clear_sky_kwh_per_m2, 0)}</dd>
              </div>
              <div>
                <dt style={labelStyle}>Estimada con cielo real</dt>
                <dd style={valueStyle}>{formatKwh(data.panel.estimated_kwh_per_m2, 0)}</dd>
              </div>
            </dl>
            <p style={{ margin: '0.5rem 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Por m² de panel y por año (albedo del suelo {data.panel.albedo}).
            </p>
          </section>
        </>
      )}
    </div>
  )
}
