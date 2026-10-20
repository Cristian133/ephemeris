import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import {
  THEME_STORAGE_KEY,
  applyTheme,
  parseThemePreference,
  resolveTheme,
} from '../utils/theme'
import type { ResolvedTheme, ThemePreference } from '../utils/theme'

interface ThemeContextValue {
  /** Lo que eligió el usuario (puede ser `system`). */
  preference: ThemePreference
  /** El tema que se está mostrando. */
  resolved: ResolvedTheme
  setPreference: (preference: ThemePreference) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

const DARK_QUERY = '(prefers-color-scheme: dark)'

function systemPrefersDark(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia(DARK_QUERY).matches
}

function readStoredPreference(): ThemePreference {
  try {
    return parseThemePreference(localStorage.getItem(THEME_STORAGE_KEY))
  } catch {
    return 'system' // localStorage puede fallar (modo privado, etc.)
  }
}

/** Tema de la app: claro, oscuro o el del sistema operativo, que se sigue en
 * vivo si el usuario cambia el del SO mientras la app está abierta. La
 * elección se guarda en localStorage (conveniencia de este navegador). */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(readStoredPreference)
  const [systemDark, setSystemDark] = useState(systemPrefersDark)

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const query = window.matchMedia(DARK_QUERY)
    const onChange = (event: MediaQueryListEvent) => setSystemDark(event.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  const resolved = resolveTheme(preference, systemDark)
  useEffect(() => applyTheme(resolved), [resolved])

  function setPreference(next: ThemePreference) {
    setPreferenceState(next)
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next)
    } catch {
      // Sin persistencia si localStorage no está disponible; vale para esta sesión.
    }
  }

  return (
    <ThemeContext.Provider value={{ preference, resolved, setPreference }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme debe usarse dentro de <ThemeProvider>')
  }
  return context
}
