import { useEffect, useRef, useState } from 'react'
import {
  ApiError,
  getApsides,
  getMoonDay,
  getMoonPhases,
  getMoonTrajectory,
} from '../api/client'
import type {
  ApsidesResponse,
  MoonDayResponse,
  MoonPhasesResponse,
  MoonTrajectoryResponse,
} from '../api/types'
import { ExportButtons } from '../components/ExportButtons'
import { MoonDisc } from '../components/MoonDisc'
import { SunPathChart } from '../components/charts/SunPathChart'
import { useDate } from '../context/DateContext'
import { useLocation } from '../context/LocationContext'
import { formatDateTime, formatTime } from '../utils/date'
import { MOON_PHASE_LABELS, PHASE_EVENT_LABELS } from '../utils/moon'

function Stat({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div>
      <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{label}</dt>
      <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>{value}</dd>
      {detail && (
        <dd style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{detail}</dd>
      )}
    </div>
  )
}

/** Fase, salida/puesta y trayectoria de la Luna en el día, más las fases y
 * el perigeo/apogeo del año. */
export default function Luna() {
  const { location } = useLocation()
  const { date } = useDate()
  const [year, setYear] = useState(() => Number(date.slice(0, 4)))
  const [day, setDay] = useState<MoonDayResponse | null>(null)
  const [path, setPath] = useState<MoonTrajectoryResponse | null>(null)
  const [phases, setPhases] = useState<MoonPhasesResponse | null>(null)
  const [apsides, setApsides] = useState<ApsidesResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!location) return
    let cancelled = false
    setError(null)
    const where = { latitude: location.latitude, longitude: location.longitude, date }
    Promise.all([getMoonDay(where), getMoonTrajectory(where)])
      .then(([dayData, pathData]) => {
        if (cancelled) return
        setDay(dayData)
        setPath(pathData)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'No se pudo calcular la Luna.')
      })
    return () => {
      cancelled = true
    }
  }, [location, date])

  useEffect(() => {
    if (year < 1000 || year > 3000) return
    let cancelled = false
    Promise.all([getMoonPhases(year), getApsides(year)])
      .then(([phasesData, apsidesData]) => {
        if (cancelled) return
        setPhases(phasesData)
        setApsides(apsidesData)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'No se pudo calcular el año.')
      })
    return () => {
      cancelled = true
    }
  }, [year])

  if (!location) return null
  const timezone = location.timezone
  const eventTime = (iso: string | null) => (iso ? formatTime(iso, timezone) : 'no ocurre este día')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <section>
        <h1 style={{ marginBottom: '0.25rem' }}>Luna</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
        <p style={{ margin: '0 0 1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Horarios en hora local del lugar ({timezone}). La fase se da al mediodía local.
        </p>

        {error && <p style={{ color: 'var(--series-2)' }}>{error}</p>}

        {day && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2rem', alignItems: 'center' }}>
            <MoonDisc
              fraction={day.illuminated_fraction}
              waxing={day.waxing}
              southern={location.latitude < 0}
            />
            <dl
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(10rem, 1fr))',
                gap: '1.25rem',
                margin: 0,
                flex: 1,
              }}
            >
              <Stat
                label="Fase"
                value={MOON_PHASE_LABELS[day.phase_key]}
                detail={`${(day.illuminated_fraction * 100).toFixed(0)}% iluminada`}
              />
              <Stat label="Edad" value={`${day.age_days.toFixed(1)} días`} detail="desde la luna nueva" />
              <Stat label="Distancia" value={`${Math.round(day.distance_km).toLocaleString('es-AR')} km`} />
              <Stat label="Sale" value={eventTime(day.rise)} />
              <Stat
                label="Culmina"
                value={eventTime(day.transit)}
                detail={
                  day.transit_altitude_deg != null
                    ? `a ${day.transit_altitude_deg.toFixed(0)}° de altura`
                    : undefined
                }
              />
              <Stat label="Se pone" value={eventTime(day.set)} />
            </dl>
          </div>
        )}
        {day && day.always_above != null && (
          <p style={{ color: 'var(--text-secondary)' }}>
            {day.always_above
              ? 'La Luna permanece sobre el horizonte todo el día.'
              : 'La Luna permanece bajo el horizonte todo el día.'}
          </p>
        )}
      </section>

      {path && (
        <section>
          <h2 style={{ marginBottom: '0.25rem' }}>Trayectoria</h2>
          <p style={{ margin: '0 0 1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Posición con paralaje (la Luna se ve hasta un grado más baja que desde el centro de la
            Tierra), sin refracción. El centro es el cenit.
          </p>
          <div ref={chartRef}>
            <SunPathChart
              bodyName="luna"
              timezone={timezone}
              data={{
                latitude: path.latitude,
                longitude: path.longitude,
                date: path.date,
                pressure_mbar: 1010,
                temperature_c: 10,
                samples: path.samples.map((s) => ({
                  time: s.time,
                  altitude: s.altitude,
                  apparent_altitude: s.altitude,
                  azimuth: s.azimuth,
                })),
              }}
            />
          </div>
          <ExportButtons
            filename={`luna-trayectoria-${path.date}`}
            chartRef={chartRef}
            getCsvRows={() => [
              [`hora_local (${timezone})`, 'altitud_grados', 'azimut_grados'],
              ...path.samples.map((s) => [
                formatTime(s.time, timezone),
                Number(s.altitude.toFixed(3)),
                Number(s.azimuth.toFixed(3)),
              ]),
            ]}
          />
        </section>
      )}

      <section>
        <h2 style={{ marginBottom: '0.25rem' }}>Fases y distancia del año</h2>
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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(18rem, 1fr))', gap: '2rem' }}>
          {phases && (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <th style={{ padding: '0.5rem 0' }}>Fase</th>
                  <th>Fecha y hora</th>
                </tr>
              </thead>
              <tbody>
                {phases.phases.map((p) => (
                  <tr key={p.time} style={{ borderTop: '1px solid var(--gridline)' }}>
                    <td
                      style={{
                        padding: '0.4rem 1rem 0.4rem 0',
                        fontWeight: p.kind === 'new' || p.kind === 'full' ? 600 : 400,
                      }}
                    >
                      {PHASE_EVENT_LABELS[p.kind]}
                    </td>
                    <td>{formatDateTime(p.time, timezone)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {apsides && (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <th style={{ padding: '0.5rem 0' }}>Punto</th>
                  <th>Fecha y hora</th>
                  <th>Distancia</th>
                </tr>
              </thead>
              <tbody>
                {apsides.apsides.map((a) => (
                  <tr key={a.time} style={{ borderTop: '1px solid var(--gridline)' }}>
                    <td style={{ padding: '0.4rem 1rem 0.4rem 0' }}>
                      {a.kind === 'perigee' ? 'Perigeo' : 'Apogeo'}
                    </td>
                    <td>{formatDateTime(a.time, timezone)}</td>
                    <td>{Math.round(a.distance_km).toLocaleString('es-AR')} km</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Las fases tienen un error de pocos segundos; el instante exacto del perigeo puede variar
          hasta unos 30 minutos (la distancia casi no cambia cerca del mínimo).
        </p>
      </section>
    </div>
  )
}
