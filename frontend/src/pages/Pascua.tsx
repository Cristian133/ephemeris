import { useEffect, useState } from 'react'
import { ApiError, getEaster } from '../api/client'
import type { EasterResponse } from '../api/types'

const YEARS_SHOWN = 10

function formatIso(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString('es-AR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

/** Pascua occidental y ortodoxa de un rango de años. */
export default function Pascua() {
  const [firstYear, setFirstYear] = useState(() => new Date().getFullYear())
  const [rows, setRows] = useState<EasterResponse[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (firstYear < 1583 || firstYear + YEARS_SHOWN - 1 > 9999) return
    let cancelled = false
    setError(null)
    Promise.all(Array.from({ length: YEARS_SHOWN }, (_, i) => getEaster(firstYear + i)))
      .then((result) => {
        if (!cancelled) setRows(result)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'No se pudo calcular la Pascua.')
      })
    return () => {
      cancelled = true
    }
  }, [firstYear])

  return (
    <div>
      <h1 style={{ marginBottom: '0.25rem' }}>Pascua</h1>
      <p style={{ margin: '0 0 1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        La Pascua occidental se calcula en el calendario gregoriano. La ortodoxa se calcula en el
        calendario juliano (columna "juliano") y se muestra además su fecha equivalente en el
        calendario gregoriano. No depende de la ubicación.
      </p>

      <label style={{ display: 'block', marginBottom: '1rem' }}>
        Desde el año:{' '}
        <input
          type="number"
          min={1583}
          max={9990}
          value={firstYear}
          onChange={(e) => setFirstYear(Number(e.target.value))}
          style={{ width: '6rem' }}
        />
      </label>

      {error && <p style={{ color: 'var(--series-2)' }}>{error}</p>}

      {rows.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              <th style={{ padding: '0.5rem 0' }}>Año</th>
              <th>Occidental</th>
              <th>Ortodoxa (gregoriano)</th>
              <th>Ortodoxa (juliano)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.year} style={{ borderTop: '1px solid var(--gridline)' }}>
                <td style={{ padding: '0.5rem 0', fontWeight: 600 }}>{row.year}</td>
                <td>{formatIso(row.western.date)}</td>
                <td>
                  {formatIso(row.orthodox.date)}
                  {row.coincide && ' (coincide)'}
                </td>
                <td>{formatIso(row.orthodox_julian_date)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
