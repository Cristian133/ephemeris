import { useEffect, useRef, useState } from 'react'
import { ApiError, getTides } from '../api/client'
import type { TideDayResponse } from '../api/types'
import { ExportButtons } from '../components/ExportButtons'
import { TideChart } from '../components/charts/TideChart'
import { useDate } from '../context/DateContext'
import { useLocation } from '../context/LocationContext'
import { formatTime } from '../utils/date'
import { tideKind } from '../utils/moon'

/** Marea teórica de equilibrio del Sol y la Luna. */
export default function Mareas() {
  const { location } = useLocation()
  const { date } = useDate()
  const [data, setData] = useState<TideDayResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!location) return
    let cancelled = false
    setError(null)
    getTides({ latitude: location.latitude, longitude: location.longitude, date })
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'No se pudo calcular la marea.')
      })
    return () => {
      cancelled = true
    }
  }, [location, date])

  if (!location) return null
  const timezone = location.timezone

  return (
    <div>
      <h1 style={{ marginBottom: '0.25rem' }}>Mareas teóricas</h1>
      <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
      <p style={{ margin: '0 0 1.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        Marea de equilibrio: la deformación que produciría la atracción de la Luna y el Sol sobre un
        océano que cubriera toda la Tierra. Muestra cuándo y cuánto tiran los astros, y el ciclo de
        mareas vivas y muertas. <strong>No es la altura de la marea real de un puerto</strong>: esa
        depende de la forma de las cuencas, la profundidad y la costa, y puede ser varias veces
        mayor o menor, y llegar horas antes o después.
      </p>

      {error && <p style={{ color: 'var(--series-2)' }}>{error}</p>}

      {data && (
        <>
          <dl
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(12rem, 1fr))',
              gap: '1.25rem',
              margin: '0 0 1.5rem',
            }}
          >
            <div>
              <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Ciclo</dt>
              <dd style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>
                {tideKind(data.spring_neap_ratio)}
              </dd>
              <dd style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                fuerza combinada: {data.spring_neap_ratio.toFixed(2)} veces la de la Luna sola
              </dd>
            </div>
            <div>
              <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Rango del día</dt>
              <dd style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>
                {(data.max_total_m - data.min_total_m).toFixed(2)} m
              </dd>
              <dd style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                de {data.min_total_m.toFixed(2)} a {data.max_total_m.toFixed(2)} m
              </dd>
            </div>
          </dl>

          <div ref={chartRef}>
            <TideChart data={data} timezone={timezone} />
          </div>

          <h2>Pleamares y bajamares de equilibrio</h2>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {data.extremes.map((e) => (
              <li key={e.time} style={{ padding: '0.35rem 0', borderTop: '1px solid var(--gridline)' }}>
                <strong>{e.high ? 'Pleamar' : 'Bajamar'}</strong> a las {formatTime(e.time, timezone)}:{' '}
                {e.height_m >= 0 ? '+' : ''}
                {e.height_m.toFixed(2)} m
              </li>
            ))}
          </ul>

          <ExportButtons
            filename={`mareas-${data.date}`}
            chartRef={chartRef}
            getCsvRows={() => [
              [`hora_local (${timezone})`, 'total_m', 'luna_m', 'sol_m'],
              ...data.samples.map((s) => [
                formatTime(s.time, timezone),
                Number(s.total_m.toFixed(3)),
                Number(s.moon_m.toFixed(3)),
                Number(s.sun_m.toFixed(3)),
              ]),
            ]}
          />
        </>
      )}
    </div>
  )
}
