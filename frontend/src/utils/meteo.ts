/** Primer año del reanálisis ERA5 que expone la fuente de datos. */
export const MIN_METEO_YEAR = 1940

export const MONTH_LABELS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

/** Último año con estadísticas: el año en curso está incompleto. */
export function lastClosedYear(now: Date = new Date()): number {
  return now.getFullYear() - 1
}

/** Mensaje de error si el período no se puede consultar, o `null` si es válido. */
export function validatePeriod(firstYear: number, lastYear: number, now: Date = new Date()): string | null {
  if (!Number.isInteger(firstYear) || !Number.isInteger(lastYear)) return 'Ingresá años enteros.'
  if (firstYear < MIN_METEO_YEAR) return `No hay datos anteriores a ${MIN_METEO_YEAR}.`
  if (lastYear > lastClosedYear(now)) {
    return `Solo hay estadísticas de años terminados (hasta ${lastClosedYear(now)}).`
  }
  if (firstYear > lastYear) return 'El año inicial no puede ser posterior al final.'
  return null
}

export function formatMm(value: number | null, digits = 0): string {
  return value == null ? '—' : `${value.toLocaleString('es-AR', { maximumFractionDigits: digits, minimumFractionDigits: digits })} mm`
}

export function formatPct(value: number | null, digits = 0): string {
  return value == null ? '—' : `${value.toLocaleString('es-AR', { maximumFractionDigits: digits, minimumFractionDigits: digits })} %`
}

export function formatHours(value: number | null, digits = 1): string {
  return value == null ? '—' : `${value.toLocaleString('es-AR', { maximumFractionDigits: digits, minimumFractionDigits: digits })} h`
}

export function formatKwh(value: number | null, digits = 1): string {
  return value == null ? '—' : `${value.toLocaleString('es-AR', { maximumFractionDigits: digits, minimumFractionDigits: digits })} kWh/m²`
}

/** Índice de claridad (real sobre cielo despejado) con dos decimales. */
export function formatIndex(value: number | null): string {
  return value == null ? '—' : value.toLocaleString('es-AR', { maximumFractionDigits: 2, minimumFractionDigits: 2 })
}
