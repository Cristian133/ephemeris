import { useEffect, useRef, useState } from 'react'
import { ApiError, getIrradiance } from '../api/client'
import type { IrradianceResponse } from '../api/types'
import { useLocation } from '../context/LocationContext'
import { useDate } from '../context/DateContext'
import { formatTime } from '../utils/date'
import { ExportButtons } from '../components/ExportButtons'
import { DailyIrradianceChart } from '../components/charts/DailyIrradianceChart'

/** Potencia solar recibida por m² (punto 5), modelo teórico de cielo
 * despejado. */
export default function Irradiancia() {
  const { location } = useLocation()
  const { date } = useDate()
  const [data, setData] = useState<IrradianceResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!location) return
    setError(null)
    getIrradiance({ latitude: location.latitude, longitude: location.longitude, date })
      .then(setData)
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'No se pudo calcular la irradiancia.')
      })
  }, [location, date])

  if (!location) return null

  return (
    <div>
      <h1 style={{ marginBottom: '0.25rem' }}>Irradiancia</h1>
      <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
      <p style={{ margin: '0 0 1.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        Modelo teórico de cielo despejado (sin nubosidad ni componente difusa) — sirve de orden
        de magnitud, no para diseño de sistemas fotovoltaicos.
      </p>

      {error && <p style={{ color: 'var(--series-2)' }}>{error}</p>}

      {data && (
        <>
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Energía total del día
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 600 }}>
              {(data.energy_wh_per_m2 / 1000).toFixed(2)} kWh/m²
            </div>
          </div>
          <div ref={chartRef}>
            <DailyIrradianceChart data={data} timezone={location.timezone} />
          </div>
          <ExportButtons
            filename={`irradiancia-${data.date}`}
            chartRef={chartRef}
            getCsvRows={() => [
              [`hora_local (${location.timezone})`, 'irradiancia_w_por_m2'],
              ...data.samples.map((s) => [
                formatTime(s.time, location.timezone),
                Number(s.power_w_per_m2.toFixed(1)),
              ]),
            ]}
          />
        </>
      )}
    </div>
  )
}
