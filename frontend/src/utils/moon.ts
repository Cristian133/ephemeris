import type {
  LunarEclipseKind,
  MoonPhaseKey,
  PhaseEventKind,
  SolarEclipseKind,
} from '../api/types'

export const MOON_PHASE_LABELS: Record<MoonPhaseKey, string> = {
  new: 'Luna nueva',
  waxing_crescent: 'Creciente',
  first_quarter: 'Cuarto creciente',
  waxing_gibbous: 'Gibosa creciente',
  full: 'Luna llena',
  waning_gibbous: 'Gibosa menguante',
  last_quarter: 'Cuarto menguante',
  waning_crescent: 'Menguante',
}

export const PHASE_EVENT_LABELS: Record<PhaseEventKind, string> = {
  new: 'Luna nueva',
  first_quarter: 'Cuarto creciente',
  full: 'Luna llena',
  last_quarter: 'Cuarto menguante',
}

export const SOLAR_ECLIPSE_LABELS: Record<SolarEclipseKind, string> = {
  partial: 'Parcial',
  annular: 'Anular',
  total: 'Total',
  hybrid: 'Híbrido (anular-total)',
}

export const LUNAR_ECLIPSE_LABELS: Record<LunarEclipseKind, string> = {
  penumbral: 'Penumbral',
  partial: 'Parcial',
  total: 'Total',
}

/** Tipo de marea según el cociente entre la fuerza combinada de Sol y Luna
 * y la lunar sola (~1.4 en sicigias, ~0.5 en cuadraturas). */
export function tideKind(ratio: number): string {
  if (ratio > 1.2) return 'Mareas vivas (sicigia)'
  if (ratio < 0.7) return 'Mareas muertas (cuadratura)'
  return 'Mareas intermedias'
}
