import type { SelectedLocation } from '../context/LocationContext'
import { isValidDateIso } from './date'

/** Ubicación y fecha en la URL (`?lat=…&lon=…&tz=…&n=…&fecha=…`), para
 * poder compartir el enlace de una consulta. */

export function readLocationFromUrl(): SelectedLocation | null {
  const params = new URLSearchParams(window.location.search)
  const latitude = Number(params.get('lat'))
  const longitude = Number(params.get('lon'))
  const timezone = params.get('tz')
  if (!params.get('lat') || !params.get('lon') || !timezone) return null
  if (!Number.isFinite(latitude) || Math.abs(latitude) > 90) return null
  if (!Number.isFinite(longitude) || Math.abs(longitude) > 180) return null
  try {
    new Intl.DateTimeFormat('es-AR', { timeZone: timezone })
  } catch {
    return null // huso horario inexistente: mejor ignorar el enlace que romper todas las horas
  }
  return {
    displayName: params.get('n') || `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`,
    latitude,
    longitude,
    timezone,
  }
}

export function readDateFromUrl(): string | null {
  const date = new URLSearchParams(window.location.search).get('fecha')
  return date && isValidDateIso(date) ? date : null
}

export function buildUrlParams(
  location: SelectedLocation | null,
  date: string,
): Record<string, string> {
  const params: Record<string, string> = { fecha: date }
  if (location) {
    params.lat = String(location.latitude)
    params.lon = String(location.longitude)
    params.tz = location.timezone
    params.n = location.displayName
  }
  return params
}
