import { useState } from 'react'
import type { FormEvent } from 'react'
import { reverseGeocode } from '../api/geocoding'
import { resolveTimezone } from '../api/timezone'
import { useLocation } from '../context/LocationContext'

const buttonStyle = {
  padding: '0.4rem 0.6rem',
  borderRadius: '0.375rem',
  border: '1px solid var(--axis)',
  background: 'var(--surface-1)',
  color: 'var(--text-primary)',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
} as const

const inputStyle = {
  width: '7rem',
  padding: '0.4rem 0.5rem',
  borderRadius: '0.375rem',
  border: '1px solid var(--axis)',
  background: 'var(--surface-1)',
  color: 'var(--text-primary)',
} as const

/** Otras formas de elegir la ubicación además del buscador: la del
 * dispositivo (geolocalización del navegador) y latitud/longitud manuales
 * para lugares que el buscador no encuentra. */
export function LocationExtras() {
  const { setLocation } = useLocation()
  const [isManualOpen, setIsManualOpen] = useState(false)
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [isBusy, setIsBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  async function applyCoordinates(lat: number, lon: number, fallbackName: string) {
    setIsBusy(true)
    setMessage(null)
    try {
      const [name, timezone] = await Promise.all([
        reverseGeocode(lat, lon),
        resolveTimezone(lat, lon).catch(() => null),
      ])
      if (!timezone) {
        setMessage('No se pudo determinar el huso horario del lugar; se muestra en UTC.')
      }
      setLocation({
        displayName: name ?? fallbackName,
        latitude: lat,
        longitude: lon,
        // Mostrar UTC (avisando) antes que la hora equivocada en silencio,
        // igual que en el buscador.
        timezone: timezone ?? 'UTC',
      })
      setIsManualOpen(false)
    } finally {
      setIsBusy(false)
    }
  }

  function locateDevice() {
    if (!('geolocation' in navigator)) {
      setMessage('Este navegador no permite obtener la ubicación.')
      return
    }
    setIsBusy(true)
    setMessage(null)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude: lat, longitude: lon } = position.coords
        void applyCoordinates(lat, lon, 'Mi ubicación')
      },
      (error) => {
        setIsBusy(false)
        setMessage(
          error.code === error.PERMISSION_DENIED
            ? 'Permiso de ubicación denegado. Habilitalo en el navegador o buscá una dirección.'
            : 'No se pudo obtener tu ubicación.',
        )
      },
      { timeout: 10_000 },
    )
  }

  function submitManual(event: FormEvent) {
    event.preventDefault()
    const lat = Number(latitude.replace(',', '.'))
    const lon = Number(longitude.replace(',', '.'))
    if (!latitude.trim() || !longitude.trim() || !Number.isFinite(lat) || !Number.isFinite(lon)) {
      setMessage('Ingresá latitud y longitud como números (ej. -34.6 y -58.4).')
      return
    }
    if (Math.abs(lat) > 90 || Math.abs(lon) > 180) {
      setMessage('La latitud va de -90 a 90 y la longitud de -180 a 180.')
      return
    }
    void applyCoordinates(lat, lon, `${lat.toFixed(4)}, ${lon.toFixed(4)}`)
  }

  return (
    <div style={{ position: 'relative', display: 'flex', gap: '0.5rem' }}>
      <button
        type="button"
        style={buttonStyle}
        onClick={locateDevice}
        disabled={isBusy}
        title="Usar mi ubicación"
        aria-label="Usar mi ubicación"
      >
        📍
      </button>
      <button
        type="button"
        style={buttonStyle}
        onClick={() => {
          setIsManualOpen((open) => !open)
          setMessage(null)
        }}
        aria-expanded={isManualOpen}
        title="Ingresar latitud y longitud"
      >
        Lat/Lon
      </button>

      {(isManualOpen || message) && (
        <div
          style={{
            position: 'absolute',
            zIndex: 10,
            top: 'calc(100% + 0.25rem)',
            right: 0,
            width: 'max-content',
            maxWidth: '20rem',
            padding: '0.75rem',
            background: 'var(--surface-1)',
            border: '1px solid var(--border)',
            borderRadius: '0.375rem',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.12)',
          }}
        >
          {isManualOpen && (
            <form onSubmit={submitManual} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <input
                value={latitude}
                onChange={(e) => setLatitude(e.target.value)}
                placeholder="Latitud"
                aria-label="Latitud"
                inputMode="decimal"
                style={inputStyle}
              />
              <input
                value={longitude}
                onChange={(e) => setLongitude(e.target.value)}
                placeholder="Longitud"
                aria-label="Longitud"
                inputMode="decimal"
                style={inputStyle}
              />
              <button type="submit" style={buttonStyle} disabled={isBusy}>
                Ir
              </button>
            </form>
          )}
          {message && (
            <p
              style={{
                margin: isManualOpen ? '0.5rem 0 0' : 0,
                fontSize: '0.8rem',
                color: 'var(--series-2)',
              }}
            >
              {message}{' '}
              <button
                type="button"
                onClick={() => setMessage(null)}
                aria-label="Cerrar mensaje"
                style={{
                  border: 'none',
                  background: 'transparent',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                ✕
              </button>
            </p>
          )}
        </div>
      )}
    </div>
  )
}
