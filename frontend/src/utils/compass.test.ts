import { describe, expect, it } from 'vitest'
import { compassLabel } from './compass'

describe('compassLabel', () => {
  it('mapea los 8 rumbos', () => {
    const cases: [number, string][] = [
      [0, 'N'], [45, 'NE'], [90, 'E'], [135, 'SE'],
      [180, 'S'], [225, 'SO'], [270, 'O'], [315, 'NO'],
    ]
    for (const [azimuth, label] of cases) expect(compassLabel(azimuth)).toBe(label)
  })

  it('redondea al rumbo mas cercano', () => {
    expect(compassLabel(22)).toBe('N')
    expect(compassLabel(23)).toBe('NE')
    expect(compassLabel(350)).toBe('N')
  })

  it('360 vuelve a Norte', () => {
    expect(compassLabel(360)).toBe('N')
  })

  it('azimuts negativos o mayores a 360 no devuelven undefined', () => {
    expect(compassLabel(-90)).toBe('O')
    expect(compassLabel(-45)).toBe('NO')
    expect(compassLabel(450)).toBe('E')
  })
})
