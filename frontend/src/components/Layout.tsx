import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation as useRouterLocation, useSearchParams } from 'react-router-dom'
import { LocationExtras } from './LocationExtras'
import { LocationSearch } from './LocationSearch'
import { ThemeToggle } from './ThemeToggle'
import { useLocation } from '../context/LocationContext'
import { useDate } from '../context/DateContext'
import { shiftDateIso, todayIso } from '../utils/date'
import { buildUrlParams } from '../utils/urlState'

const NAV_ITEMS = [
  { to: '/', label: 'Horas de sol' },
  { to: '/trayectoria', label: 'Trayectoria' },
  { to: '/mediodia', label: 'Mediodía' },
  { to: '/irradiancia', label: 'Irradiancia' },
  { to: '/crepusculos', label: 'Crepúsculos' },
  { to: '/estaciones', label: 'Estaciones' },
  { to: '/panel', label: 'Panel solar' },
  { to: '/luna', label: 'Luna' },
  { to: '/eclipses', label: 'Eclipses' },
  { to: '/mareas', label: 'Mareas' },
  { to: '/pascua', label: 'Pascua' },
  { to: '/lluvia', label: 'Lluvia' },
  { to: '/nubosidad', label: 'Nubosidad' },
  { to: '/sol-real', label: 'Sol real' },
  { to: '/radiacion-real', label: 'Radiación real' },
]

const smallButtonStyle = {
  padding: '0.4rem 0.6rem',
  borderRadius: '0.375rem',
  border: '1px solid var(--axis)',
  background: 'var(--surface-1)',
  color: 'var(--text-primary)',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
} as const

export function Layout() {
  const { location } = useLocation()
  const { date, setDate } = useDate()
  const { search } = useRouterLocation()
  const [, setSearchParams] = useSearchParams()
  const [linkCopied, setLinkCopied] = useState(false)

  // Ubicación y fecha viajan en la URL para poder compartir la consulta.
  useEffect(() => {
    setSearchParams(buildUrlParams(location, date), { replace: true })
  }, [location, date, setSearchParams])

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setLinkCopied(true)
      setTimeout(() => setLinkCopied(false), 2000)
    } catch {
      // Sin permiso de portapapeles: la URL de la barra del navegador ya
      // es la misma, se puede copiar a mano.
    }
  }

  return (
    <div style={{ minHeight: '100%', display: 'flex', flexDirection: 'column' }}>
      <header
        style={{
          borderBottom: '1px solid var(--gridline)',
          background: 'var(--surface-1)',
          padding: '0.75rem 1rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '1rem',
        }}
      >
        <strong style={{ fontSize: '1.1rem' }}>☀️ Ephemeris</strong>

        <nav style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={{ pathname: item.to, search }}
              end={item.to === '/'}
              style={({ isActive }) => ({
                padding: '0.4rem 0.75rem',
                borderRadius: '0.375rem',
                textDecoration: 'none',
                color: isActive ? '#fff' : 'var(--text-primary)',
                background: isActive ? 'var(--series-1)' : 'transparent',
                fontWeight: isActive ? 600 : 400,
              })}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Fecha</span>
            <button
              type="button"
              style={smallButtonStyle}
              onClick={() => setDate(shiftDateIso(date, -1))}
              aria-label="Día anterior"
              title="Día anterior"
            >
              ◀
            </button>
            <input
              type="date"
              aria-label="Fecha"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              style={{
                padding: '0.4rem 0.5rem',
                borderRadius: '0.375rem',
                border: '1px solid var(--axis)',
                background: 'var(--surface-1)',
                color: 'var(--text-primary)',
              }}
            />
            <button
              type="button"
              style={smallButtonStyle}
              onClick={() => setDate(shiftDateIso(date, 1))}
              aria-label="Día siguiente"
              title="Día siguiente"
            >
              ▶
            </button>
            <button type="button" style={smallButtonStyle} onClick={() => setDate(todayIso())}>
              Hoy
            </button>
          </div>
          <LocationSearch />
          <LocationExtras />
          <button
            type="button"
            style={smallButtonStyle}
            onClick={copyLink}
            title="Copiar enlace a esta consulta"
          >
            {linkCopied ? '✓ Copiado' : '🔗 Enlace'}
          </button>
          <ThemeToggle />
        </div>
      </header>

      <main style={{ flex: 1, padding: '1.5rem 1rem', maxWidth: '64rem', width: '100%', margin: '0 auto' }}>
        {location ? (
          <Outlet />
        ) : (
          <p style={{ color: 'var(--text-secondary)' }}>
            Buscá una ubicación arriba para empezar (ej. "Buenos Aires, Argentina").
          </p>
        )}
      </main>

      <footer
        style={{
          padding: '0.5rem 1rem',
          textAlign: 'right',
          fontSize: '0.7rem',
          color: 'var(--text-muted)',
        }}
      >
        Datos de{' '}
        <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
          OpenStreetMap
        </a>
        {location && (
          <>
            {' '}
            · hora local: <strong>{location.timezone}</strong>
          </>
        )}
      </footer>
    </div>
  )
}
