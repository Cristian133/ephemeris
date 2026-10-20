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
  pressure_mbar: number
  temperature_c: number
  samples: SunPosition[]
}

export interface SolarNoonResponse {
  latitude: number
  longitude: number
  date: string
  pressure_mbar: number
  temperature_c: number
  transit: string
  altitude_deg: number
  apparent_altitude_deg: number
  azimuth_deg: number
}

export interface IrradianceSample {
  time: string
  power_w_per_m2: number // global horizontal = directa + difusa
  direct_w_per_m2: number
  diffuse_w_per_m2: number
}

export interface IrradianceResponse {
  latitude: number
  longitude: number
  date: string
  elevation_m: number
  linke_turbidity: number
  energy_wh_per_m2: number
  direct_energy_wh_per_m2: number
  diffuse_energy_wh_per_m2: number
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
  elevation_m: number
  linke_turbidity: number
  albedo: number
  azimuth_deg: number
  annual_tilt_deg: number
  winter_tilt_deg: number
  summer_tilt_deg: number
  annual_kwh_per_m2: number
  horizontal_kwh_per_m2: number
  curve: TiltEnergy[]
}

/* Etapa 2: Luna, eclipses, calendario y mareas (backend/app/schemas/luna.py). */

export type MoonPhaseKey =
  | 'new'
  | 'waxing_crescent'
  | 'first_quarter'
  | 'waxing_gibbous'
  | 'full'
  | 'waning_gibbous'
  | 'last_quarter'
  | 'waning_crescent'

export interface MoonDayResponse {
  latitude: number
  longitude: number
  date: string
  rise: string | null
  transit: string | null
  set: string | null
  transit_altitude_deg: number | null
  always_above: boolean | null
  illuminated_fraction: number
  phase_angle_deg: number
  phase_key: MoonPhaseKey
  waxing: boolean
  age_days: number
  bright_limb_angle_deg: number
  distance_km: number
}

export interface MoonPositionSample {
  time: string
  altitude: number
  azimuth: number
}

export interface MoonTrajectoryResponse {
  latitude: number
  longitude: number
  date: string
  illuminated_fraction: number
  samples: MoonPositionSample[]
}

export type PhaseEventKind = 'new' | 'first_quarter' | 'full' | 'last_quarter'

export interface MoonPhaseEvent {
  kind: PhaseEventKind
  time: string
  brown_lunation: number
}

export interface MoonPhasesResponse {
  year: number
  phases: MoonPhaseEvent[]
}

export interface ApsisItem {
  kind: 'perigee' | 'apogee'
  time: string
  distance_km: number
  parallax_arcsec: number
}

export interface ApsidesResponse {
  year: number
  apsides: ApsisItem[]
}

export type SolarEclipseKind = 'partial' | 'annular' | 'total' | 'hybrid'
export type LunarEclipseKind = 'penumbral' | 'partial' | 'total'

export interface SolarEclipseItem {
  time: string
  kind: SolarEclipseKind
  central: boolean
  gamma: number
  u: number
  magnitude: number | null
}

export interface LunarEclipseItem {
  time: string
  kind: LunarEclipseKind
  gamma: number
  penumbral_magnitude: number
  umbral_magnitude: number
  penumbra_start: string
  partial_start: string | null
  total_start: string | null
  total_end: string | null
  partial_end: string | null
  penumbra_end: string
  moon_altitude_deg: number | null
}

export interface EclipsesResponse {
  year: number
  solar: SolarEclipseItem[]
  lunar: LunarEclipseItem[]
}

export interface EasterDate {
  date: string
  weekday: string
}

export interface EasterResponse {
  year: number
  western: EasterDate
  orthodox_julian_date: string
  orthodox: EasterDate
  coincide: boolean
}

export interface TideSample {
  time: string
  moon_m: number
  sun_m: number
  total_m: number
}

export interface TideExtremeItem {
  time: string
  height_m: number
  high: boolean
}

export interface TideDayResponse {
  latitude: number
  longitude: number
  date: string
  spring_neap_ratio: number
  max_total_m: number
  min_total_m: number
  extremes: TideExtremeItem[]
  samples: TideSample[]
}
