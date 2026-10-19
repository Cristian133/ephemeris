import { useEffect, useRef, useState } from 'react'
import { ApiError, getPanel } from '../api/client'
import type { PanelResponse } from '../api/types'
import { useLocation } from '../context/LocationContext'
import { compassLabel } from '../utils/compass'
import { ExportButtons } from '../components/ExportButtons'
import { PanelTiltChart } from '../components/charts/PanelTiltChart'

function Stat({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div>
      <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{label}</dt>
      <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>{value}</dd>
      {detail && <dd style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{detail}</dd>}
    </div>
  )
}

/** Orientación e inclinación óptimas de un panel solar fijo. */
export default function PanelSolar() {
  const { location } = useLocation()
  const [year, setYear] = useState(() => new Date().getFullYear())
  const [data, setData] = useState<PanelResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!location) return
    setError(null)
    getPanel({ latitude: location.latitude, longitude: location.longitude, year })
      .then(setData)
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'No se pudo calcular el panel óptimo.')
      })
  }, [location, year])

  if (!location) return null

  const gainPercent = data
    ? ((data.annual_kwh_per_m2 / data.horizontal_kwh_per_m2 - 1) * 100).toFixed(0)
    : null

  return (
    <div>
      <h1 style={{ marginBottom: '0.25rem' }}>Panel solar óptimo</h1>
      <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
      <p style={{ margin: '0 0 1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        Panel fijo mirando al ecuador. Modelo teórico de cielo despejado, solo luz directa (sin
        nubosidad ni difusa): es una referencia de orden de magnitud, no un dimensionamiento
        fotovoltaico — con luz difusa, la inclinación ideal real suele ser algo menor.
      </p>

      <label style={{ display: 'block', marginBottom: '1.5rem' }}>
        Año:{' '}
        <input
          type="number"
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          style={{ width: '6rem' }}
        />
      </label>

      {error && <p style={{ color: 'var(--series-2)' }}>{error}</p>}

      {data && (
        <>
          <dl
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(11rem, 1fr))',
              gap: '1.25rem',
              margin: '0 0 2rem',
            }}
          >
            <Stat
              label="Orientación"
              value={`${data.azimuth_deg.toFixed(0)}° (${compassLabel(data.azimuth_deg)})`}
              detail="hacia el ecuador"
            />
            <Stat label="Inclinación anual óptima" value={`${data.annual_tilt_deg.toFixed(0)}°`} />
            <Stat
              label="Mejor en invierno"
              value={`${data.winter_tilt_deg.toFixed(0)}°`}
              detail="si la ajustás por estación"
            />
            <Stat
              label="Mejor en verano"
              value={`${data.summer_tilt_deg.toFixed(0)}°`}
              detail="si la ajustás por estación"
            />
            <Stat
              label="Energía anual"
              value={`${data.annual_kwh_per_m2.toFixed(0)} kWh/m²`}
              detail={`${gainPercent}% más que un panel horizontal`}
            />
          </dl>

          <h2 style={{ marginBottom: '0.25rem' }}>Energía anual según la inclinación</h2>
          <div ref={chartRef}>
            <PanelTiltChart data={data} />
          </div>
          <ExportButtons
            filename={`panel-solar-${data.year}`}
            chartRef={chartRef}
            getCsvRows={() => [
              ['inclinacion_grados', 'kwh_por_m2_anual'],
              ...data.curve.map((p) => [p.tilt_deg, Number(p.annual_kwh_per_m2.toFixed(1))]),
            ]}
          />
        </>
      )}
    </div>
  )
}
