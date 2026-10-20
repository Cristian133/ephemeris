import { describe, expect, it } from 'vitest'
import {
  formatHours,
  formatIndex,
  formatKwh,
  formatMm,
  formatPct,
  lastClosedYear,
  validatePeriod,
} from './meteo'

const NOW = new Date(2026, 9, 20)

describe('lastClosedYear', () => {
  it('es el año anterior al actual', () => {
    expect(lastClosedYear(NOW)).toBe(2025)
  })
})

describe('validatePeriod', () => {
  it('acepta el período climatológico estándar', () => {
    expect(validatePeriod(1991, 2020, NOW)).toBeNull()
  })

  it('acepta los extremos permitidos', () => {
    expect(validatePeriod(1940, 2025, NOW)).toBeNull()
    expect(validatePeriod(2025, 2025, NOW)).toBeNull()
  })

  it('rechaza el año en curso y los futuros', () => {
    expect(validatePeriod(2000, 2026, NOW)).toMatch(/terminados/)
  })

  it('rechaza años anteriores a ERA5', () => {
    expect(validatePeriod(1939, 2000, NOW)).toMatch(/1940/)
  })

  it('rechaza un rango invertido o no entero', () => {
    expect(validatePeriod(2010, 2000, NOW)).toMatch(/posterior/)
    expect(validatePeriod(2000.5, 2010, NOW)).toMatch(/enteros/)
    expect(validatePeriod(NaN, 2010, NOW)).toMatch(/enteros/)
  })
})

describe('formatMm', () => {
  it('formatea con separador es-AR y unidad', () => {
    expect(formatMm(1070.9)).toBe('1.071 mm')
    expect(formatMm(12.345, 1)).toBe('12,3 mm')
  })

  it('muestra una raya cuando no hay dato', () => {
    expect(formatMm(null)).toBe('—')
  })
})

describe('formatPct y formatHours', () => {
  it('formatean con unidad y coma decimal', () => {
    expect(formatPct(47.4)).toBe('47 %')
    expect(formatPct(79.26, 1)).toBe('79,3 %')
    expect(formatHours(3498, 0)).toBe('3.498 h')
    expect(formatHours(7.25)).toBe('7,3 h')
  })

  it('muestran una raya cuando no hay dato', () => {
    expect(formatPct(null)).toBe('—')
    expect(formatHours(null)).toBe('—')
  })
})

describe('formatKwh y formatIndex', () => {
  it('formatean con unidad y coma decimal', () => {
    expect(formatKwh(4.17)).toBe('4,2 kWh/m²')
    expect(formatKwh(1742, 0)).toBe('1.742 kWh/m²')
    expect(formatIndex(0.783)).toBe('0,78')
  })

  it('muestran una raya cuando no hay dato', () => {
    expect(formatKwh(null)).toBe('—')
    expect(formatIndex(null)).toBe('—')
  })
})
