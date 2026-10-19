import type { SkyModel } from '../api/client'

/** Valores por defecto del modelo de cielo despejado (coinciden con los del
 * backend: nivel del mar, aire limpio, suelo de pasto). */
export const DEFAULT_SKY_MODEL: SkyModel = { elevation_m: 0, linke_turbidity: 3 }
export const DEFAULT_ALBEDO = 0.2
