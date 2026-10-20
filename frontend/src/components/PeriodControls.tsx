/** Selector del período de años de las páginas meteorológicas, con el
 * error de validación, el error de la consulta y el estado de carga. */
export function PeriodControls({
  firstYear,
  lastYear,
  onFirstYear,
  onLastYear,
  periodError,
  error,
  loading,
}: {
  firstYear: number
  lastYear: number
  onFirstYear: (year: number) => void
  onLastYear: (year: number) => void
  periodError: string | null
  error: string | null
  loading: boolean
}) {
  return (
    <>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <label>
          Desde:{' '}
          <input
            type="number"
            value={firstYear}
            onChange={(e) => onFirstYear(Number(e.target.value))}
            style={{ width: '6rem' }}
          />
        </label>
        <label>
          Hasta:{' '}
          <input
            type="number"
            value={lastYear}
            onChange={(e) => onLastYear(Number(e.target.value))}
            style={{ width: '6rem' }}
          />
        </label>
      </div>
      {periodError && <p style={{ color: 'var(--series-2)' }}>{periodError}</p>}
      {error && <p style={{ color: 'var(--series-2)' }}>{error}</p>}
      {loading && <p style={{ color: 'var(--text-muted)' }}>Obteniendo datos…</p>}
    </>
  )
}
