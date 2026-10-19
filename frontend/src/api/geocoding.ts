/**
 * Buscador de direcciones vía Nominatim (OpenStreetMap) — gratuito, sin
 * API key. Uso liviano (búsqueda interactiva de un solo usuario), acorde
 * a su política de uso: https://operations.osmfoundation.org/policies/nominatim/
 * Igual, atribuir "datos de OpenStreetMap" donde se muestren resultados.
 */

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'

// Nominatim pide como maximo ~1 request por segundo. El debounce del
// buscador evita disparar por tecla, pero este espaciado cubre ademas el
// uso combinado de busqueda y geocodificacion inversa.
const MIN_INTERVAL_MS = 1100
let nextSlot = 0

/** Reserva el proximo turno (espaciado MIN_INTERVAL_MS entre requests a
 * Nominatim). Si `signal` se aborta mientras espera, rechaza con AbortError
 * sin llegar a pedir nada. */
async function waitForSlot(signal?: AbortSignal): Promise<void> {
  const now = Date.now()
  const slot = Math.max(now, nextSlot)
  nextSlot = slot + MIN_INTERVAL_MS
  const delay = slot - now
  if (delay > 0) {
    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(resolve, delay)
      signal?.addEventListener(
        'abort',
        () => {
          clearTimeout(timeout)
          reject(new DOMException('Aborted', 'AbortError'))
        },
        { once: true },
      )
    })
  }
  signal?.throwIfAborted()
}

/** Solo para tests: reinicia el espaciado entre requests. */
export function resetRateLimit(): void {
  nextSlot = 0
}

export interface GeocodingResult {
  displayName: string
  latitude: number
  longitude: number
}

export async function searchLocation(
  query: string,
  signal?: AbortSignal,
): Promise<GeocodingResult[]> {
  if (query.trim().length < 3) return []

  const params = new URLSearchParams({
    q: query,
    format: 'jsonv2',
    limit: '5',
  })
  await waitForSlot(signal)
  const response = await fetch(`${NOMINATIM_URL}?${params}`, { signal })
  if (!response.ok) {
    // 429 = rate limit de Nominatim; se distingue para poder avisar.
    throw new Error(`Nominatim: ${response.status} ${response.statusText}`.trim())
  }

  const results = (await response.json()) as { display_name: string; lat: string; lon: string }[]
  if (!Array.isArray(results)) return []
  return results
    .map((r) => ({
      displayName: r.display_name,
      latitude: Number(r.lat),
      longitude: Number(r.lon),
    }))
    .filter((r) => Number.isFinite(r.latitude) && Number.isFinite(r.longitude))
}

const NOMINATIM_REVERSE_URL = 'https://nominatim.openstreetmap.org/reverse'

/** Nombre legible de un punto (geocodificación inversa). Devuelve `null`
 * si Nominatim no lo conoce (ej. mar abierto) o falla: quien llama decide
 * cómo rotular el lugar en ese caso. */
export async function reverseGeocode(latitude: number, longitude: number): Promise<string | null> {
  const params = new URLSearchParams({
    lat: String(latitude),
    lon: String(longitude),
    format: 'jsonv2',
    zoom: '10',
  })
  try {
    await waitForSlot()
    const response = await fetch(`${NOMINATIM_REVERSE_URL}?${params}`)
    if (!response.ok) return null
    const data = (await response.json()) as { display_name?: string }
    return data.display_name ?? null
  } catch {
    return null
  }
}
