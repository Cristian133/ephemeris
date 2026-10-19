/**
 * Buscador de direcciones vía Nominatim (OpenStreetMap) — gratuito, sin
 * API key. Uso liviano (búsqueda interactiva de un solo usuario), acorde
 * a su política de uso: https://operations.osmfoundation.org/policies/nominatim/
 * Igual, atribuir "datos de OpenStreetMap" donde se muestren resultados.
 */

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'

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
  const response = await fetch(`${NOMINATIM_URL}?${params}`, { signal })
  if (!response.ok) {
    throw new Error(`Nominatim: ${response.statusText}`)
  }

  const results = (await response.json()) as { display_name: string; lat: string; lon: string }[]
  return results.map((r) => ({
    displayName: r.display_name,
    latitude: Number(r.lat),
    longitude: Number(r.lon),
  }))
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
    const response = await fetch(`${NOMINATIM_REVERSE_URL}?${params}`)
    if (!response.ok) return null
    const data = (await response.json()) as { display_name?: string }
    return data.display_name ?? null
  } catch {
    return null
  }
}
