/** Preferencia de tema del usuario: claro, oscuro o el del sistema operativo. */
export type ThemePreference = 'light' | 'dark' | 'system'
/** Tema que realmente se aplica. */
export type ResolvedTheme = 'light' | 'dark'

/** Misma clave que lee el script de `index.html` antes del primer dibujo. */
export const THEME_STORAGE_KEY = 'ephemeris:theme'

export const THEME_OPTIONS: { value: ThemePreference; label: string; icon: string }[] = [
  { value: 'light', label: 'Claro', icon: '☀️' },
  { value: 'dark', label: 'Oscuro', icon: '🌙' },
  { value: 'system', label: 'Sistema', icon: '🖥️' },
]

/** Lo guardado, o `system` si no hay nada o no es válido. */
export function parseThemePreference(raw: string | null | undefined): ThemePreference {
  return raw === 'light' || raw === 'dark' ? raw : 'system'
}

export function resolveTheme(preference: ThemePreference, systemPrefersDark: boolean): ResolvedTheme {
  if (preference === 'system') return systemPrefersDark ? 'dark' : 'light'
  return preference
}

/** Marca el tema en <html>; los tokens de color de `theme.css` cuelgan de ahí. */
export function applyTheme(theme: ResolvedTheme, root: HTMLElement = document.documentElement): void {
  root.setAttribute('data-theme', theme)
}
