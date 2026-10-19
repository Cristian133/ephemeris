/**
 * Tipos que reflejan los modelos Pydantic de `backend/app/schemas/sol.py`.
 * Mantener en sync a mano (sin generador de OpenAPI todavía).
 */

export interface DailySunResponse {
  date: string // ISO (YYYY-MM-DD)
  transit: string // ISO datetime UTC
  sunrise: string | null
  sunset: string | null
  day_length_hours: number | null
  always_above: boolean | null
  latitude: number
  longitude: number
}

export interface AnnualSunResponse {
  latitude: number
  longitude: number
  year: number
  days: Omit<DailySunResponse, 'latitude' | 'longitude'>[]
}

export interface SunPosition {
  time: string
  altitude: number
  apparent_altitude: number
  azimuth: number
}

export interface TrajectoryResponse {
  latitude: number
  longitude: number
  date: string
  samples: SunPosition[]
}

export interface SolarNoonResponse {
  latitude: number
  longitude: number
  date: string
  transit: string
  altitude_deg: number
  apparent_altitude_deg: number
  azimuth_deg: number
}

export interface IrradianceSample {
  time: string
  power_w_per_m2: number
}

export interface IrradianceResponse {
  latitude: number
  longitude: number
  date: string
  energy_wh_per_m2: number
  samples: IrradianceSample[]
}

export interface AltitudeCrossing {
  altitude_deg: number
  rise: string | null
  set: string | null
  always_above: boolean | null
}

export interface TwilightResponse {
  latitude: number
  longitude: number
  date: string
  astronomical: AltitudeCrossing
  nautical: AltitudeCrossing
  civil: AltitudeCrossing
  blue_hour_limit: AltitudeCrossing
  horizon: AltitudeCrossing
  golden_hour_limit: AltitudeCrossing
}

export interface SeasonsResponse {
  year: number
  march_equinox: string
  june_solstice: string
  september_equinox: string
  december_solstice: string
}

export interface TiltEnergy {
  tilt_deg: number
  annual_kwh_per_m2: number
}

export interface PanelResponse {
  latitude: number
  longitude: number
  year: number
  azimuth_deg: number
  annual_tilt_deg: number
  winter_tilt_deg: number
  summer_tilt_deg: number
  annual_kwh_per_m2: number
  horizontal_kwh_per_m2: number
  curve: TiltEnergy[]
}
