import { describe, expect, it } from 'vitest'
import {
  LUNAR_ECLIPSE_LABELS,
  MOON_PHASE_LABELS,
  PHASE_EVENT_LABELS,
  SOLAR_ECLIPSE_LABELS,
  tideKind,
} from './moon'

describe('tideKind', () => {
  it('distingue mareas vivas, muertas e intermedias por el cociente de fuerzas', () => {
    expect(tideKind(1.4)).toBe('Mareas vivas (sicigia)')
    expect(tideKind(0.5)).toBe('Mareas muertas (cuadratura)')
    expect(tideKind(1.0)).toBe('Mareas intermedias')
  })

  it('los bordes caen en la categoria intermedia', () => {
    expect(tideKind(1.2)).toBe('Mareas intermedias')
    expect(tideKind(0.7)).toBe('Mareas intermedias')
  })
})

describe('etiquetas', () => {
  it('cubren todas las claves que devuelve el backend', () => {
    expect(Object.keys(MOON_PHASE_LABELS)).toHaveLength(8)
    expect(Object.keys(PHASE_EVENT_LABELS)).toEqual([
      'new',
      'first_quarter',
      'full',
      'last_quarter',
    ])
    expect(Object.keys(SOLAR_ECLIPSE_LABELS).sort()).toEqual(['annular', 'hybrid', 'partial', 'total'])
    expect(Object.keys(LUNAR_ECLIPSE_LABELS).sort()).toEqual(['partial', 'penumbral', 'total'])
  })
})
