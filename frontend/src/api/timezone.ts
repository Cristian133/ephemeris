/**
 * Resuelve el huso horario IANA (ej. "America/Argentina/Buenos_Aires")
 * para una latitud/longitud dada, vía la API de pronóstico de Open-Meteo
 * (gratuita, sin API key) con `timezone=auto` — Open-Meteo resuelve el
 * huso horario real del punto pedido a partir de sus propios límites
 * geográficos; no hace falta ningún dato de clima, solo leemos el campo
 * `timezone` de la respuesta.
 *
 * El backend calcula todo en UT; esto es puramente para mostrarle al
 * usuario los horarios en la hora del lugar consultado (no la del
 * navegador, que puede ser una zona horaria distinta).
 */

const OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'

export async function resolveTimezone(
  latitude: number,
  longitude: number,
  signal?: AbortSignal,
): Promise<string> {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    timezone: 'auto',
    forecast_days: '1',
    daily: 'sunrise',
  })
  const response = await fetch(`${OPEN_METEO_URL}?${params}`, { signal })
  if (!response.ok) {
    throw new Error(`Open-Meteo: ${response.status} ${response.statusText}`.trim())
  }
  const data = (await response.json()) as { timezone?: string }
  if (!data.timezone) {
    throw new Error('Open-Meteo no devolvió huso horario')
  }
  return data.timezone
}
