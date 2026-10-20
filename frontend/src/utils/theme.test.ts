// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import indexHtml from '../../index.html?raw'
import {
  THEME_OPTIONS,
  THEME_STORAGE_KEY,
  applyTheme,
  parseThemePreference,
  resolveTheme,
} from './theme'

describe('parseThemePreference', () => {
  it('acepta claro y oscuro', () => {
    expect(parseThemePreference('light')).toBe('light')
    expect(parseThemePreference('dark')).toBe('dark')
  })

  it('usa el sistema si no hay nada guardado o el valor no es válido', () => {
    expect(parseThemePreference(null)).toBe('system')
    expect(parseThemePreference(undefined)).toBe('system')
    expect(parseThemePreference('system')).toBe('system')
    expect(parseThemePreference('sepia')).toBe('system')
    expect(parseThemePreference('')).toBe('system')
  })
})

describe('resolveTheme', () => {
  it('claro y oscuro ignoran al sistema', () => {
    expect(resolveTheme('light', true)).toBe('light')
    expect(resolveTheme('dark', false)).toBe('dark')
  })

  it('sistema sigue la preferencia del sistema operativo', () => {
    expect(resolveTheme('system', true)).toBe('dark')
    expect(resolveTheme('system', false)).toBe('light')
  })
})

describe('applyTheme', () => {
  it('marca el tema en el elemento raíz', () => {
    const root = document.createElement('html')
    applyTheme('dark', root)
    expect(root.getAttribute('data-theme')).toBe('dark')
    applyTheme('light', root)
    expect(root.getAttribute('data-theme')).toBe('light')
  })
})

describe('opciones del selector', () => {
  it('ofrecen claro, oscuro y sistema, en ese orden', () => {
    expect(THEME_OPTIONS.map((o) => o.value)).toEqual(['light', 'dark', 'system'])
  })

  it('usan la misma clave de almacenamiento que el script de index.html', () => {
    expect(indexHtml).toContain(`'${THEME_STORAGE_KEY}'`)
  })
})
