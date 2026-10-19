import { useEffect, useRef, useState } from 'react'
import { ApiError, getAnnualSun, getDailySun } from '../api/client'
import type { AnnualSunResponse, DailySunResponse } from '../api/types'
import { useLocation } from '../context/LocationContext'
import { useDate } from '../context/DateContext'
import { formatTime } from '../utils/date'
import { ExportButtons } from '../components/ExportButtons'
import { AnnualDayLengthChart } from '../components/charts/AnnualDayLengthChart'

/** Punto 1 (horas de sol de un día) + punto 2 (evolución anual). */
export default function HorasDeSol() {
  const { location } = useLocation()
  const { date } = useDate()
  const [year, setYear] = useState(() => new Date().getFullYear())

  const [daily, setDaily] = useState<DailySunResponse | null>(null)
  const [dailyError, setDailyError] = useState<string | null>(null)

  const [annual, setAnnual] = useState<AnnualSunResponse | null>(null)
  const [annualError, setAnnualError] = useState<string | null>(null)
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!location) return
    setDailyError(null)
    getDailySun({ latitude: location.latitude, longitude: location.longitude, date })
      .then(setDaily)
      .catch((err: unknown) => {
        setDailyError(err instanceof ApiError ? err.message : 'No se pudo calcular el día.')
      })
  }, [location, date])

  useEffect(() => {
    if (!location) return
    setAnnualError(null)
    getAnnualSun({ latitude: location.latitude, longitude: location.longitude, year })
      .then(setAnnual)
      .catch((err: unknown) => {
        setAnnualError(err instanceof ApiError ? err.message : 'No se pudo calcular el año.')
      })
  }, [location, year])

  if (!location) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <section>
        <h1 style={{ marginBottom: '0.25rem' }}>Horas de sol</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>{location.displayName}</p>
        <p style={{ margin: '0 0 1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Horarios en hora local del lugar ({location.timezone})
        </p>

        {dailyError && <p style={{ color: 'var(--series-2)' }}>{dailyError}</p>}

        {daily && (
          <dl
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(9rem, 1fr))',
              gap: '1rem',
              margin: 0,
            }}
          >
            {daily.always_above !== null ? (
              <div style={{ gridColumn: '1 / -1' }}>
                <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  {daily.always_above ? 'Sol de medianoche' : 'Noche polar'}
                </dt>
                <dd style={{ margin: 0, fontSize: '1.1rem' }}>
                  {daily.always_above
                    ? 'El sol no se pone este día.'
                    : 'El sol no sale este día.'}
                </dd>
              </div>
            ) : (
              <>
                <div>
                  <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Orto</dt>
                  <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
                    {formatTime(daily.sunrise!, location.timezone)}
                  </dd>
                </div>
                <div>
                  <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Ocaso</dt>
                  <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
                    {formatTime(daily.sunset!, location.timezone)}
                  </dd>
                </div>
                <div>
                  <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Duración</dt>
                  <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
                    {daily.day_length_hours!.toFixed(2)} h
                  </dd>
                </div>
              </>
            )}
            <div>
              <dt style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Mediodía solar</dt>
              <dd style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
                {formatTime(daily.transit, location.timezone)}
              </dd>
            </div>
          </dl>
        )}
      </section>

      <section>
        <h2 style={{ marginBottom: '0.25rem' }}>Evolución anual</h2>
        <label style={{ display: 'block', marginBottom: '0.5rem' }}>
          Año:{' '}
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            style={{ width: '6rem' }}
          />
        </label>

        {annualError && <p style={{ color: 'var(--series-2)' }}>{annualError}</p>}
        {annual && (
          <>
            <div ref={chartRef}>
              <AnnualDayLengthChart data={annual} />
            </div>
            <ExportButtons
              filename={`horas-de-sol-${annual.year}`}
              chartRef={chartRef}
              getCsvRows={() => [
                [
                  'fecha',
                  `orto (${location.timezone})`,
                  `mediodia_solar (${location.timezone})`,
                  `ocaso (${location.timezone})`,
                  'horas_de_sol',
                ],
                ...annual.days.map((d) => [
                  d.date,
                  d.sunrise ? formatTime(d.sunrise, location.timezone) : null,
                  formatTime(d.transit, location.timezone),
                  d.sunset ? formatTime(d.sunset, location.timezone) : null,
                  d.day_length_hours != null ? Number(d.day_length_hours.toFixed(3)) : null,
                ]),
              ]}
            />
          </>
        )}
      </section>
    </div>
  )
}
