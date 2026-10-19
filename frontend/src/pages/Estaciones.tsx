import { useEffect, useState } from 'react'
import { ApiError, getAnnualSun, getSeasons } from '../api/client'
import type { AnnualSunResponse, SeasonsResponse } from '../api/types'
import { useLocation } from '../context/LocationContext'
import { formatDateTime } from '../utils/date'

type EventKey = 'march_equinox' | 'june_solstice' | 'september_equinox' | 'december_solstice'

/** El nombre de la estación que inicia cada evento depende del hemisferio:
 * el equinoccio de marzo es el otoño austral y la primavera boreal. */
const EVENTS: { key: EventKey; label: string; south: string; north: string }[] = [
  { key: 'march_equinox', label: 'Equinoccio de marzo', south: 'Otoño', north: 'Primavera' },
  { key: 'june_solstice', label: 'Solsticio de junio', south: 'Invierno', north: 'Verano' },
  { key: 'september_equinox', label: 'Equinoccio de septiembre', south: 'Primavera', north: 'Otoño' },
  { key: 'december_solstice', label: 'Solsticio de diciembre', south: 'Verano', north: 'Invierno' },
]

function formatDay(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString('es-AR', {
    day: 'numeric',
    month: 'long',
  })
}

function extremes(annual: AnnualSunResponse) {
  const withLength = annual.days.filter((d) => d.day_length_hours != null)
  if (withLength.length === 0) return null
  const longest = withLength.reduce((a, b) => (b.day_length_hours! > a.day_length_hours! ? b : a))
  const shortest = withLength.reduce((a, b) => (b.day_length_hours! < a.day_length_hours! ? b : a))
  return { longest, shortest }
}

/** Equinoccios y solsticios del año, con el día más largo y el más corto. */
export default function Estaciones() {
  const { location } = useLocation()
  const [year, setYear] = useState(() => new Date().getFullYear())
  const [seasons, setSeasons] = useState<SeasonsResponse | null>(null)
  const [annual, setAnnual] = useState<AnnualSunResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!location || year < 1000 || year > 3000) return
    setError(null)
    Promise.all([
      getSeasons(year),
      getAnnualSun({ latitude: location.latitude, longitude: location.longitude, year }),
    ])
      .then(([seasonsData, annualData]) => {
        setSeasons(seasonsData)
        setAnnual(annualData)
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'No se pudieron calcular las estaciones.')
      })
  }, [location, year])

  if (!location) return null

  const southern = location.latitude < 0
  const days = annual ? extremes(annual) : null

  return (
    <div>
      <h1 style={{ marginBottom: '0.25rem' }}>Estaciones del año</h1>
      <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
      <p style={{ margin: '0 0 1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        Horarios en hora local del lugar ({location.timezone}). Las estaciones se nombran según el
        hemisferio {southern ? 'sur' : 'norte'}.
      </p>

      <label style={{ display: 'block', marginBottom: '1rem' }}>
        Año:{' '}
        <input
          type="number"
          min={1000}
          max={3000}
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          style={{ width: '6rem' }}
        />
      </label>

      {error && <p style={{ color: 'var(--series-2)' }}>{error}</p>}

      {seasons && (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              <th style={{ padding: '0.5rem 0' }}>Evento</th>
              <th>Comienza</th>
              <th>Fecha y hora</th>
            </tr>
          </thead>
          <tbody>
            {EVENTS.map((event) => (
              <tr key={event.key} style={{ borderTop: '1px solid var(--gridline)' }}>
                <td style={{ padding: '0.6rem 0' }}>{event.label}</td>
                <td style={{ fontWeight: 600 }}>{southern ? event.south : event.north}</td>
                <td>{formatDateTime(seasons[event.key], location.timezone)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {days && (
        <dl
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(12rem, 1fr))',
            gap: '1rem',
            margin: '2rem 0 0',
          }}
        >
          <div>
            <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Día más largo</dt>
            <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
              {days.longest.day_length_hours!.toFixed(2)} h
            </dd>
            <dd style={{ margin: 0, color: 'var(--text-secondary)' }}>{formatDay(days.longest.date)}</dd>
          </div>
          <div>
            <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Día más corto</dt>
            <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
              {days.shortest.day_length_hours!.toFixed(2)} h
            </dd>
            <dd style={{ margin: 0, color: 'var(--text-secondary)' }}>{formatDay(days.shortest.date)}</dd>
          </div>
        </dl>
      )}
    </div>
  )
}
