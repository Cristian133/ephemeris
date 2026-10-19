import { useEffect, useRef, useState } from 'react'
import { searchLocation } from '../api/geocoding'
import type { GeocodingResult } from '../api/geocoding'
import { resolveTimezone } from '../api/timezone'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { useLocation } from '../context/LocationContext'

/** Buscador de dirección (Nominatim/OpenStreetMap) que resuelve a
 * latitud/longitud. La ubicación elegida queda compartida (ver
 * `LocationContext`) para todas las páginas. */
export function LocationSearch() {
  const { location, setLocation } = useLocation()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<GeocodingResult[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isResolvingTimezone, setIsResolvingTimezone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const debouncedQuery = useDebouncedValue(query, 400)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (debouncedQuery.trim().length < 3) {
      setResults([])
      setIsLoading(false)
      return
    }

    const controller = new AbortController()
    setIsLoading(true)
    setError(null)

    searchLocation(debouncedQuery, controller.signal)
      .then((found) => {
        setResults(found)
        setIsOpen(true)
      })
      .catch(() => {
        // Abortada por una busqueda nueva o por desmontar: no es un error.
        if (controller.signal.aborted) return
        setError('No se pudo buscar la dirección. Probá de nuevo.')
      })
      .finally(() => {
        // Una request abortada no debe apagar el "Buscando..." de la nueva.
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [debouncedQuery])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  async function handleSelect(result: GeocodingResult) {
    setQuery('')
    setResults([])
    setIsOpen(false)
    setIsResolvingTimezone(true)
    setError(null)

    try {
      const timezone = await resolveTimezone(result.latitude, result.longitude)
      setLocation({ ...result, timezone })
    } catch {
      // Sin huso horario resuelto, mostramos UTC antes que romper: es
      // peor mostrar la hora equivocada en silencio, así que avisamos.
      setLocation({ ...result, timezone: 'UTC' })
      setError('No se pudo determinar el huso horario del lugar; se muestra en UTC.')
    } finally {
      setIsResolvingTimezone(false)
    }
  }

  return (
    <div ref={containerRef} style={{ position: 'relative', minWidth: '16rem' }}>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setIsOpen(true)}
        disabled={isResolvingTimezone}
        placeholder={
          isResolvingTimezone
            ? 'Resolviendo huso horario…'
            : location
              ? location.displayName
              : 'Buscar una ciudad o dirección…'
        }
        aria-label="Buscar ubicación"
        style={{
          width: '100%',
          padding: '0.5rem 0.75rem',
          borderRadius: '0.375rem',
          border: `1px solid var(--axis)`,
          background: 'var(--surface-1)',
          color: 'var(--text-primary)',
        }}
      />

      {isOpen && (isLoading || error || results.length > 0) && (
        <ul
          role="listbox"
          style={{
            position: 'absolute',
            zIndex: 10,
            top: 'calc(100% + 0.25rem)',
            left: 0,
            right: 0,
            margin: 0,
            padding: '0.25rem',
            listStyle: 'none',
            background: 'var(--surface-1)',
            border: `1px solid var(--border)`,
            borderRadius: '0.375rem',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.12)',
            maxHeight: '16rem',
            overflowY: 'auto',
          }}
        >
          {isLoading && (
            <li style={{ padding: '0.5rem 0.75rem', color: 'var(--text-muted)' }}>Buscando…</li>
          )}
          {error && (
            <li style={{ padding: '0.5rem 0.75rem', color: 'var(--text-secondary)' }}>{error}</li>
          )}
          {!isLoading &&
            !error &&
            results.map((result) => (
              <li key={`${result.latitude},${result.longitude}`}>
                <button
                  type="button"
                  onClick={() => handleSelect(result)}
                  style={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    padding: '0.5rem 0.75rem',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--text-primary)',
                    borderRadius: '0.25rem',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--gridline)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  {result.displayName}
                </button>
              </li>
            ))}
        </ul>
      )}

      {!isOpen && error && (
        <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: 'var(--series-2)' }}>
          {error}
        </p>
      )}
    </div>
  )
}
