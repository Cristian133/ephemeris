import { afterEach, describe, expect, it, vi } from 'vitest'
import { formatDateTime, formatTime, isValidDateIso, localHours, shiftDateIso, todayIso } from './date'

describe('shiftDateIso', () => {
  it('suma y resta dias simples', () => {
    expect(shiftDateIso('2024-06-10', 1)).toBe('2024-06-11')
    expect(shiftDateIso('2024-06-10', -1)).toBe('2024-06-09')
    expect(shiftDateIso('2024-06-10', 0)).toBe('2024-06-10')
  })

  it('cruza fin de mes', () => {
    expect(shiftDateIso('2024-01-31', 1)).toBe('2024-02-01')
    expect(shiftDateIso('2024-03-01', -1)).toBe('2024-02-29') // bisiesto
    expect(shiftDateIso('2023-03-01', -1)).toBe('2023-02-28')
  })

  it('cruza fin de anio', () => {
    expect(shiftDateIso('2024-12-31', 1)).toBe('2025-01-01')
    expect(shiftDateIso('2025-01-01', -1)).toBe('2024-12-31')
  })

  it('soporta saltos grandes', () => {
    expect(shiftDateIso('2024-01-01', 366)).toBe('2025-01-01')
    expect(shiftDateIso('2024-01-01', -365)).toBe('2023-01-01')
  })
})

describe('isValidDateIso', () => {
  it('acepta fechas reales', () => {
    expect(isValidDateIso('2024-02-29')).toBe(true)
    expect(isValidDateIso('2024-12-31')).toBe(true)
  })

  it('rechaza formato incorrecto', () => {
    expect(isValidDateIso('')).toBe(false)
    expect(isValidDateIso('2024-2-9')).toBe(false)
    expect(isValidDateIso('10/06/2024')).toBe(false)
    expect(isValidDateIso('2024-06-10T00:00:00Z')).toBe(false)
  })

  it('rechaza fechas inexistentes', () => {
    expect(isValidDateIso('2024-13-01')).toBe(false)
    expect(isValidDateIso('2024-00-10')).toBe(false)
    expect(isValidDateIso('2023-02-29')).toBe(false)
    expect(isValidDateIso('2024-02-31')).toBe(false)
    expect(isValidDateIso('2024-04-31')).toBe(false)
  })
})

describe('todayIso', () => {
  afterEach(() => vi.useRealTimers())

  it('usa la fecha local del reloj, con ceros a la izquierda', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2024, 0, 5, 23, 30)) // hora local
    expect(todayIso()).toBe('2024-01-05')
  })
})

describe('formatTime / localHours', () => {
  // 02:30 UT del 10/06: en Buenos Aires (UTC-3) es el 09/06 a las 23:30.
  const iso = '2024-06-10T02:30:00Z'

  // es-AR formatea en 12 h ("11:30 p. m.") segun la version de ICU; se
  // normaliza a "HH:MM" para no depender de eso.
  const to24h = (text: string) => {
    const match = text.match(/^(\d{1,2}):(\d{2})(?:\s*([ap])\.?\s*m\.?)?$/i)
    if (!match) return text
    let hour = Number(match[1]) % 12
    if (!match[3]) hour = Number(match[1])
    else if (match[3].toLowerCase() === 'p') hour += 12
    return `${String(hour).padStart(2, '0')}:${match[2]}`
  }

  it('convierte a la hora del lugar, cambiando de dia', () => {
    expect(to24h(formatTime(iso, 'America/Argentina/Buenos_Aires'))).toBe('23:30')
    expect(to24h(formatTime(iso, 'UTC'))).toBe('02:30')
    expect(to24h(formatTime(iso, 'Asia/Tokyo'))).toBe('11:30')
  })

  it('formatDateTime refleja el dia local, no el de UT', () => {
    expect(formatDateTime(iso, 'America/Argentina/Buenos_Aires')).toContain('9 de junio')
    expect(formatDateTime(iso, 'UTC')).toContain('10 de junio')
  })

  it('localHours devuelve horas decimales locales', () => {
    expect(localHours(iso, 'America/Argentina/Buenos_Aires')).toBeCloseTo(23.5)
    expect(localHours(iso, 'UTC')).toBeCloseTo(2.5)
    expect(localHours(iso, 'Asia/Kolkata')).toBeCloseTo(8.0) // UTC+5:30
  })

  it('localHours: medianoche local es 0, no 24', () => {
    expect(localHours('2024-06-10T03:00:00Z', 'America/Argentina/Buenos_Aires')).toBe(0)
  })

  it('respeta husos con minutos de desfase y DST', () => {
    expect(localHours('2024-01-15T12:00:00Z', 'Asia/Kathmandu')).toBeCloseTo(17.75)
    expect(localHours('2024-07-15T12:00:00Z', 'Europe/Madrid')).toBeCloseTo(14)
    expect(localHours('2024-01-15T12:00:00Z', 'Europe/Madrid')).toBeCloseTo(13)
  })

  it('un huso invalido lanza RangeError', () => {
    expect(() => formatTime(iso, 'No/Existe')).toThrow(RangeError)
  })

  it('una fecha invalida lanza RangeError en localHours', () => {
    expect(() => localHours('no-es-fecha', 'UTC')).toThrow(RangeError)
  })
})
