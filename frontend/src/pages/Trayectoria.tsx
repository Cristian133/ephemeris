import { useEffect, useRef, useState } from 'react'
import { ApiError, getSeasons, getTrajectory } from '../api/client'
import type { TrajectoryResponse } from '../api/types'
import { useLocation } from '../context/LocationContext'
import { useDate } from '../context/DateContext'
import { formatTime } from '../utils/date'
import { ExportButtons } from '../components/ExportButtons'
import { SunPathChart } from '../components/charts/SunPathChart'
import type { SunPathOverlay } from '../components/charts/SunPathChart'

/** Fechas de referencia para comparar: los dos solsticios y el equinoccio
 * (el de marzo y el de septiembre trazan prácticamente la misma curva). */
const COMPARISON_DATES = [
  { key: 'june_solstice', label: 'Solsticio de junio', color: 'var(--series-2)' },
  { key: 'december_solstice', label: 'Solsticio de diciembre', color: 'var(--series-3)' },
  { key: 'march_equinox', label: 'Equinoccios', color: 'var(--series-4)' },
] as const

/** Trayectoria/posición del sol (punto 3), como gráfico polar. */
export default function Trayectoria() {
  const { location } = useLocation()
  const { date } = useDate()
  const [data, setData] = useState<TrajectoryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [compare, setCompare] = useState(false)
  const [overlays, setOverlays] = useState<SunPathOverlay[]>([])
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!location) return
    setError(null)
    getTrajectory({ latitude: location.latitude, longitude: location.longitude, date })
      .then(setData)
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'No se pudo calcular la trayectoria.')
      })
  }, [location, date])

  const year = Number(date.slice(0, 4))
  useEffect(() => {
    if (!location || !compare || year < 1000 || year > 3000) {
      setOverlays([])
      return
    }
    let cancelled = false
    getSeasons(year)
      .then((seasons) =>
        Promise.all(
          COMPARISON_DATES.map(async ({ key, label, color }) => {
            const day = seasons[key].slice(0, 10)
            const trajectory = await getTrajectory({
              latitude: location.latitude,
              longitude: location.longitude,
              date: day,
            })
            return { label, color, samples: trajectory.samples }
          }),
        ),
      )
      .then((result) => {
        if (!cancelled) setOverlays(result)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'No se pudo calcular la comparación.')
      })
    return () => {
      cancelled = true
    }
  }, [location, compare, year])

  if (!location) return null

  return (
    <div>
      <h1 style={{ marginBottom: '0.25rem' }}>Trayectoria solar</h1>
      <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
      <p style={{ margin: '0 0 1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        Posición del sol a lo largo del día: el centro es el cenit (90° de altitud), el borde es
        el horizonte. Pasá el mouse sobre la curva para ver hora, altitud y dirección.
      </p>

      <label style={{ display: 'block', marginBottom: '1rem' }}>
        <input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)} />{' '}
        Comparar con solsticios y equinoccios de {year}
      </label>

      {error && <p style={{ color: 'var(--series-2)' }}>{error}</p>}
      {data && (
        <>
          <div ref={chartRef}>
            <SunPathChart data={data} timezone={location.timezone} overlays={compare ? overlays : []} />
          </div>
          <ExportButtons
            filename={`trayectoria-${data.date}`}
            chartRef={chartRef}
            getCsvRows={() => [
              [`hora_local (${location.timezone})`, 'altitud_grados', 'altitud_aparente_grados', 'azimut_grados'],
              ...data.samples.map((s) => [
                formatTime(s.time, location.timezone),
                Number(s.altitude.toFixed(3)),
                Number(s.apparent_altitude.toFixed(3)),
                Number(s.azimuth.toFixed(3)),
              ]),
            ]}
          />
        </>
      )}
    </div>
  )
}
