import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import { todayIso } from '../utils/date'
import { readDateFromUrl } from '../utils/urlState'

interface DateContextValue {
  date: string // YYYY-MM-DD
  setDate: (date: string) => void
}

const DateContext = createContext<DateContextValue | null>(null)

/** Fecha consultada, compartida entre las páginas de un solo día
 * (Horas de sol, Trayectoria, Mediodía, Irradiancia) — así no hay que
 * re-elegirla al cambiar de página. No se persiste entre sesiones (a
 * diferencia de la ubicación): arranca en el día de hoy, salvo que la URL
 * traiga una fecha (enlace compartido). */
export function DateProvider({ children }: { children: ReactNode }) {
  const [date, setDate] = useState(() => readDateFromUrl() ?? todayIso())
  return <DateContext.Provider value={{ date, setDate }}>{children}</DateContext.Provider>
}

export function useDate(): DateContextValue {
  const context = useContext(DateContext)
  if (!context) {
    throw new Error('useDate debe usarse dentro de <DateProvider>')
  }
  return context
}
