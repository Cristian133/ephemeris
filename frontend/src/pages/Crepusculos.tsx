import { useEffect, useState } from 'react'
import { ApiError, getTwilight } from '../api/client'
import type { AltitudeCrossing, TwilightResponse } from '../api/types'
import { useLocation } from '../context/LocationContext'
import { useDate } from '../context/DateContext'
import { formatTime, localHours } from '../utils/date'

interface Phase {
  label: string
  /** Color del tramo en la barra del día. */
  color: string
  /** Cruces que delimitan el tramo de la mañana: [desde, hasta]. */
  from: AltitudeCrossing
  to: AltitudeCrossing
}

function phasesOf(data: TwilightResponse): Phase[] {
  return [
    { label: 'Crepúsculo astronómico', color: '#2b2f6b', from: data.astronomical, to: data.nautical },
    { label: 'Crepúsculo náutico', color: '#3d4fa3', from: data.nautical, to: data.civil },
    { label: 'Hora azul', color: '#4f86d9', from: data.civil, to: data.blue_hour_limit },
    { label: 'Hora dorada', color: '#f0a43a', from: data.blue_hour_limit, to: data.golden_hour_limit },
  ]
}

function range(from: string | null, to: string | null, timezone: string): string {
  if (!from || !to) return '—'
  return `${formatTime(from, timezone)} – ${formatTime(to, timezone)}`
}

/** Barra de 24 h (hora local) con la noche, los crepúsculos, las horas
 * azul y dorada y el día. Solo se dibuja si todos los cruces existen: en
 * latitudes altas hay días sin noche astronómica y la barra mentiría. */
function DayBar({ data, timezone }: { data: TwilightResponse; timezone: string }) {
  const crossings = [
    data.astronomical,
    data.nautical,
    data.civil,
    data.blue_hour_limit,
    data.golden_hour_limit,
  ]
  if (crossings.some((c) => !c.rise || !c.set)) return null

  const pct = (iso: string) => `${(localHours(iso, timezone) / 24) * 100}%`
  const segment = (startIso: string, endIso: string, color: string, label: string) => {
    const start = localHours(startIso, timezone)
    const end = localHours(endIso, timezone)
    if (end <= start) return null
    return (
      <div
        key={`${label}-${startIso}`}
        title={label}
        style={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          left: pct(startIso),
          width: `${((end - start) / 24) * 100}%`,
          background: color,
        }}
      />
    )
  }

  const phases = phasesOf(data)
  return (
    <div style={{ margin: '1.5rem 0' }}>
      <div
        role="img"
        aria-label="Fases del día en hora local"
        style={{
          position: 'relative',
          height: '2.5rem',
          borderRadius: '0.375rem',
          overflow: 'hidden',
          background: '#14163a', // noche
        }}
      >
        {phases.flatMap((phase) => [
          segment(phase.from.rise!, phase.to.rise!, phase.color, phase.label),
          segment(phase.to.set!, phase.from.set!, phase.color, phase.label),
        ])}
        {segment(data.golden_hour_limit.rise!, data.golden_hour_limit.set!, '#8fc7f5', 'Día')}
      </div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          marginTop: '0.25rem',
        }}
      >
        {[0, 6, 12, 18, 24].map((h) => (
          <span key={h}>{String(h).padStart(2, '0')}:00</span>
        ))}
      </div>
      <ul
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.5rem 1.25rem',
          listStyle: 'none',
          padding: 0,
          margin: '0.75rem 0 0',
          fontSize: '0.8rem',
          color: 'var(--text-secondary)',
        }}
      >
        {[
          { label: 'Noche', color: '#14163a' },
          ...phases.map((p) => ({ label: p.label, color: p.color })),
          { label: 'Día', color: '#8fc7f5' },
        ].map((item) => (
          <li key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span
              style={{ width: '0.75rem', height: '0.75rem', borderRadius: '2px', background: item.color }}
            />
            {item.label}
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Crepúsculos (civil, náutico, astronómico) y horas azul y dorada. */
export default function Crepusculos() {
  const { location } = useLocation()
  const { date } = useDate()
  const [data, setData] = useState<TwilightResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!location) return
    setError(null)
    getTwilight({ latitude: location.latitude, longitude: location.longitude, date })
      .then(setData)
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'No se pudieron calcular los crepúsculos.')
      })
  }, [location, date])

  if (!location) return null

  const timezone = location.timezone
  const phases = data ? phasesOf(data) : []
  const missing =
    data && [data.astronomical, data.nautical, data.civil].some((c) => !c.rise || !c.set)

  return (
    <div>
      <h1 style={{ marginBottom: '0.25rem' }}>Crepúsculos y horas especiales</h1>
      <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
      <p style={{ margin: '0 0 1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        Horarios en hora local del lugar ({timezone}). Crepúsculos según el Sol esté 6°, 12° o 18° bajo
        el horizonte; hora azul entre -6° y -4°, hora dorada entre -4° y +6° de altitud.
      </p>

      {error && <p style={{ color: 'var(--series-2)' }}>{error}</p>}

      {data && (
        <>
          <DayBar data={data} timezone={timezone} />

          {missing && (
            <p style={{ color: 'var(--text-secondary)' }}>
              En esta latitud y fecha el Sol no baja lo suficiente: alguno de los crepúsculos no
              llega a terminar (o la noche no llega a empezar), por eso faltan horarios.
            </p>
          )}

          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                <th style={{ padding: '0.5rem 0' }}>Fase</th>
                <th>Mañana</th>
                <th>Tarde</th>
              </tr>
            </thead>
            <tbody>
              {phases.map((phase) => (
                <tr key={phase.label} style={{ borderTop: '1px solid var(--gridline)' }}>
                  <td style={{ padding: '0.6rem 0' }}>{phase.label}</td>
                  <td>{range(phase.from.rise, phase.to.rise, timezone)}</td>
                  <td>{range(phase.to.set, phase.from.set, timezone)}</td>
                </tr>
              ))}
              <tr style={{ borderTop: '1px solid var(--gridline)' }}>
                <td style={{ padding: '0.6rem 0' }}>
                  Crepúsculo civil{' '}
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    (abarca la hora azul y parte de la dorada)
                  </span>
                </td>
                <td>{range(data.civil.rise, data.horizon.rise, timezone)}</td>
                <td>{range(data.horizon.set, data.civil.set, timezone)}</td>
              </tr>
              <tr style={{ borderTop: '1px solid var(--gridline)' }}>
                <td style={{ padding: '0.6rem 0' }}>Orto / ocaso</td>
                <td>{data.horizon.rise ? formatTime(data.horizon.rise, timezone) : '—'}</td>
                <td>{data.horizon.set ? formatTime(data.horizon.set, timezone) : '—'}</td>
              </tr>
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
