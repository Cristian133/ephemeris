/** Hoy según el reloj del navegador (no UTC: pasadas las 21h en Argentina,
 * la fecha UTC ya es la de mañana). */
export function todayIso(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

/** Suma (o resta) días a una fecha YYYY-MM-DD, sin depender de la zona
 * horaria del navegador. */
export function shiftDateIso(iso: string, days: number): string {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10)
}

export function isValidDateIso(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value))
}

/** Formatea un instante (ISO, en UT) en la hora local del lugar
 * consultado — no la del navegador, que puede ser una zona horaria
 * distinta a la del lugar. */
export function formatTime(iso: string, timezone: string): string {
  return new Date(iso).toLocaleTimeString('es-AR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: timezone,
  })
}

/** Fecha y hora de un instante (ISO, en UT) en la hora local del lugar. */
export function formatDateTime(iso: string, timezone: string): string {
  return new Date(iso).toLocaleString('es-AR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: timezone,
  })
}

/** Hora local del lugar como horas decimales desde la medianoche (0–24). */
export function localHours(iso: string, timezone: string): number {
  const parts = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone: timezone,
  }).formatToParts(new Date(iso))
  const hour = Number(parts.find((p) => p.type === 'hour')?.value)
  const minute = Number(parts.find((p) => p.type === 'minute')?.value)
  return hour + minute / 60
}
