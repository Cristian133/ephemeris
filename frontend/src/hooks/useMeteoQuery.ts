import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type { MeteoPeriod } from '../api/client'
import { useLocation } from '../context/LocationContext'
import { useDebouncedValue } from './useDebouncedValue'
import { validatePeriod } from '../utils/meteo'

/** Período climatológico estándar de la OMM. */
const DEFAULT_FIRST_YEAR = 1991
const DEFAULT_LAST_YEAR = 2020

/** Estado común de las páginas meteorológicas: el período elegido (con
 * espera al tipear y validación), la consulta al backend para la
 * ubicación actual y su carga o error. `fetcher` debe ser estable (una
 * función de `api/client`). */
export function useMeteoQuery<T>(
  fetcher: (params: MeteoPeriod) => Promise<T>,
  failureMessage: string,
) {
  const { location } = useLocation()
  const [firstYear, setFirstYear] = useState(DEFAULT_FIRST_YEAR)
  const [lastYear, setLastYear] = useState(DEFAULT_LAST_YEAR)
  const debouncedFirst = useDebouncedValue(firstYear, 600)
  const debouncedLast = useDebouncedValue(lastYear, 600)
  const periodError = validatePeriod(debouncedFirst, debouncedLast)

  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!location || periodError) return
    let cancelled = false
    setLoading(true)
    setError(null)
    fetcher({
      latitude: location.latitude,
      longitude: location.longitude,
      first_year: debouncedFirst,
      last_year: debouncedLast,
    })
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : failureMessage)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [location, debouncedFirst, debouncedLast, periodError, fetcher, failureMessage])

  return {
    firstYear,
    setFirstYear,
    lastYear,
    setLastYear,
    periodError,
    data,
    loading,
    error,
  }
}
