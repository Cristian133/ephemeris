import { useEffect, useState } from 'react'
import { ApiError, getEclipses } from '../api/client'
import type { EclipsesResponse, LunarEclipseItem, SolarEclipseItem } from '../api/types'
import { useLocation } from '../context/LocationContext'
import { formatDateTime, formatTime } from '../utils/date'
import { LUNAR_ECLIPSE_LABELS, SOLAR_ECLIPSE_LABELS } from '../utils/moon'

const headerStyle = { textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.85rem' } as const

function solarVisibility(eclipse: SolarEclipseItem): string {
  const hemisphere = eclipse.gamma >= 0 ? 'norte' : 'sur'
  return eclipse.central
    ? `Franja central; el eje de la sombra pasa al ${hemisphere} del centro de la Tierra`
    : `Sin franja central; visible desde el hemisferio ${hemisphere}`
}

function lunarDuration(eclipse: LunarEclipseItem): string {
  const minutes = (a: string | null, b: string | null) =>
    a && b ? Math.round((new Date(b).getTime() - new Date(a).getTime()) / 60000) : null
  const total = minutes(eclipse.total_start, eclipse.total_end)
  const partial = minutes(eclipse.partial_start, eclipse.partial_end)
  const penumbral = minutes(eclipse.penumbra_start, eclipse.penumbra_end)
  if (total) return `totalidad ${total} min; fase parcial ${partial} min`
  if (partial) return `fase parcial ${partial} min`
  return `fase penumbral ${penumbral} min`
}

/** Eclipses de Sol y de Luna del año (condiciones globales). */
export default function Eclipses() {
  const { location } = useLocation()
  const [year, setYear] = useState(() => new Date().getFullYear())
  const [data, setData] = useState<EclipsesResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!location || year < 1800 || year > 2200) return
    let cancelled = false
    setError(null)
    getEclipses(year, { latitude: location.latitude, longitude: location.longitude })
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : 'No se pudieron calcular los eclipses.')
        }
      })
    return () => {
      cancelled = true
    }
  }, [location, year])

  if (!location) return null
  const timezone = location.timezone

  return (
    <div>
      <h1 style={{ marginBottom: '0.25rem' }}>Eclipses</h1>
      <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
      <p style={{ margin: '0 0 1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        Horarios en hora local del lugar ({timezone}). Son las condiciones globales de cada eclipse
        (instante del máximo, tipo y magnitud); las circunstancias locales de un eclipse solar
        (horas de contacto, porcentaje de cobertura en tu ciudad) requieren elementos besselianos y
        no se calculan acá. Los eclipses de Luna se ven desde cualquier lugar donde la Luna esté
        sobre el horizonte.
      </p>

      <label style={{ display: 'block', marginBottom: '1.5rem' }}>
        Año:{' '}
        <input
          type="number"
          min={1800}
          max={2200}
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          style={{ width: '6rem' }}
        />
      </label>

      {error && <p style={{ color: 'var(--series-2)' }}>{error}</p>}

      {data && (
        <>
          <h2>Eclipses de Sol</h2>
          {data.solar.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>No hay eclipses de Sol este año.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '2rem' }}>
              <thead>
                <tr style={headerStyle}>
                  <th style={{ padding: '0.5rem 0' }}>Máximo</th>
                  <th>Tipo</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {data.solar.map((e) => (
                  <tr key={e.time} style={{ borderTop: '1px solid var(--gridline)', verticalAlign: 'top' }}>
                    <td style={{ padding: '0.6rem 0' }}>{formatDateTime(e.time, timezone)}</td>
                    <td style={{ fontWeight: 600 }}>{SOLAR_ECLIPSE_LABELS[e.kind]}</td>
                    <td>
                      {solarVisibility(e)}
                      {e.magnitude != null && ` (magnitud ${e.magnitude.toFixed(2)})`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h2>Eclipses de Luna</h2>
          {data.lunar.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>No hay eclipses de Luna este año.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={headerStyle}>
                  <th style={{ padding: '0.5rem 0' }}>Máximo</th>
                  <th>Tipo</th>
                  <th>Duración</th>
                  <th>Desde acá</th>
                </tr>
              </thead>
              <tbody>
                {data.lunar.map((e) => (
                  <tr key={e.time} style={{ borderTop: '1px solid var(--gridline)', verticalAlign: 'top' }}>
                    <td style={{ padding: '0.6rem 0' }}>{formatDateTime(e.time, timezone)}</td>
                    <td style={{ fontWeight: 600 }}>
                      {LUNAR_ECLIPSE_LABELS[e.kind]}
                      {e.kind !== 'penumbral' && ` (${e.umbral_magnitude.toFixed(2)})`}
                    </td>
                    <td>
                      {lunarDuration(e)}
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        {formatTime(e.penumbra_start, timezone)} a{' '}
                        {formatTime(e.penumbra_end, timezone)}
                      </div>
                    </td>
                    <td>
                      {e.moon_altitude_deg == null
                        ? ''
                        : e.moon_altitude_deg > 0
                          ? `Se ve (Luna a ${e.moon_altitude_deg.toFixed(0)}° de altura)`
                          : 'No se ve (Luna bajo el horizonte)'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  )
}
