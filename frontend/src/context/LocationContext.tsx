import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { readLocationFromUrl } from '../utils/urlState'

export interface SelectedLocation {
  displayName: string
  latitude: number
  longitude: number
  /** Huso horario IANA del lugar (ej. "America/Argentina/Buenos_Aires"),
   * resuelto al elegir la ubicación — ver `api/timezone.ts`. */
  timezone: string
}

interface LocationContextValue {
  location: SelectedLocation | null
  setLocation: (location: SelectedLocation) => void
}

const STORAGE_KEY = 'calculadora-solar:location'

const LocationContext = createContext<LocationContextValue | null>(null)

function readStoredLocation(): SelectedLocation | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<SelectedLocation>
    // Descarta lo guardado por una versión anterior sin `timezone` (o
    // corrupto) en vez de propagar `undefined` a Intl.DateTimeFormat.
    if (typeof parsed.timezone !== 'string' || !parsed.timezone) return null
    return parsed as SelectedLocation
  } catch {
    return null // localStorage puede fallar (modo privado, etc.) — sin ubicación guardada
  }
}

/** Ubicación elegida por el usuario, compartida entre todas las páginas y
 * persistida en localStorage (conveniencia de este navegador, no un
 * backend — ver skill de capacidades de artifacts si algún día hiciera
 * falta compartir entre dispositivos). Una ubicación en la URL (enlace
 * compartido) tiene prioridad sobre la guardada. */
export function LocationProvider({ children }: { children: ReactNode }) {
  const [location, setLocationState] = useState<SelectedLocation | null>(
    () => readLocationFromUrl() ?? readStoredLocation(),
  )

  useEffect(() => {
    if (!location) return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(location))
    } catch {
      // Sin persistencia si localStorage no está disponible; la sesión
      // sigue funcionando igual con el estado en memoria.
    }
  }, [location])

  return (
    <LocationContext.Provider value={{ location, setLocation: setLocationState }}>
      {children}
    </LocationContext.Provider>
  )
}

export function useLocation(): LocationContextValue {
  const context = useContext(LocationContext)
  if (!context) {
    throw new Error('useLocation debe usarse dentro de <LocationProvider>')
  }
  return context
}
