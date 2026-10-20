import type {
  AnnualSunResponse,
  ApsidesResponse,
  CloudResponse,
  DailySunResponse,
  EasterResponse,
  EclipsesResponse,
  IrradianceRealResponse,
  IrradianceResponse,
  MoonDayResponse,
  MoonPhasesResponse,
  MoonTrajectoryResponse,
  PanelResponse,
  RainResponse,
  SeasonsResponse,
  SolarNoonResponse,
  SunshineResponse,
  TideDayResponse,
  TrajectoryResponse,
  TwilightResponse,
} from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function get<T>(path: string, params: Record<string, string | number>): Promise<T> {
  const query = new URLSearchParams(
    Object.fromEntries(Object.entries(params).map(([key, value]) => [key, String(value)])),
  )
  const response = await fetch(`${API_URL}${path}?${query}`)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail ? JSON.stringify(body.detail) : response.statusText
    throw new ApiError(`${path}: ${detail}`, response.status)
  }
  return response.json() as Promise<T>
}

export interface LocationDate {
  latitude: number
  longitude: number
  date: string // YYYY-MM-DD
}

export function getDailySun({ latitude, longitude, date }: LocationDate): Promise<DailySunResponse> {
  return get('/sol/dia', { latitude, longitude, date })
}

export function getAnnualSun(params: {
  latitude: number
  longitude: number
  year: number
}): Promise<AnnualSunResponse> {
  return get('/sol/anual', params)
}

export function getTrajectory(
  { latitude, longitude, date }: LocationDate,
  numSamples = 96,
): Promise<TrajectoryResponse> {
  return get('/sol/trayectoria', { latitude, longitude, date, num_samples: numSamples })
}

export function getSolarNoon({ latitude, longitude, date }: LocationDate): Promise<SolarNoonResponse> {
  return get('/sol/mediodia', { latitude, longitude, date })
}

/** Parámetros del modelo de cielo despejado (ver `app/solar/irradiance.py`). */
export type SkyModel = {
  elevation_m: number
  linke_turbidity: number
}

export function getIrradiance(
  { latitude, longitude, date }: LocationDate,
  sky: SkyModel,
  numSamples = 96,
): Promise<IrradianceResponse> {
  return get('/sol/irradiancia', { latitude, longitude, date, num_samples: numSamples, ...sky })
}

export function getTwilight({ latitude, longitude, date }: LocationDate): Promise<TwilightResponse> {
  return get('/sol/crepusculos', { latitude, longitude, date })
}

export function getSeasons(year: number): Promise<SeasonsResponse> {
  return get('/sol/estaciones', { year })
}

export function getPanel(
  params: {
    latitude: number
    longitude: number
    year: number
    albedo: number
  } & SkyModel,
): Promise<PanelResponse> {
  return get('/sol/panel', params)
}

export function getMoonDay({ latitude, longitude, date }: LocationDate): Promise<MoonDayResponse> {
  return get('/luna/dia', { latitude, longitude, date })
}

export function getMoonTrajectory(
  { latitude, longitude, date }: LocationDate,
  numSamples = 96,
): Promise<MoonTrajectoryResponse> {
  return get('/luna/trayectoria', { latitude, longitude, date, num_samples: numSamples })
}

export function getMoonPhases(year: number): Promise<MoonPhasesResponse> {
  return get('/luna/fases', { year })
}

export function getApsides(year: number): Promise<ApsidesResponse> {
  return get('/luna/apsides', { year })
}

/** Eclipses del año; con ubicación, cada eclipse lunar trae la altitud de
 * la Luna en el máximo desde ese lugar. */
export function getEclipses(
  year: number,
  where?: { latitude: number; longitude: number },
): Promise<EclipsesResponse> {
  return get('/eclipses/anio', { year, ...where })
}

export function getEaster(year: number): Promise<EasterResponse> {
  return get('/calendario/pascua', { year })
}

export function getTides({ latitude, longitude, date }: LocationDate): Promise<TideDayResponse> {
  return get('/mareas/dia', { latitude, longitude, date })
}

export interface MeteoPeriod {
  latitude: number
  longitude: number
  first_year: number
  last_year: number
}

export function getRain(params: MeteoPeriod): Promise<RainResponse> {
  return get('/meteo/lluvia', { ...params })
}

export function getClouds(params: MeteoPeriod): Promise<CloudResponse> {
  return get('/meteo/nubosidad', { ...params })
}

export function getSunshine(params: MeteoPeriod): Promise<SunshineResponse> {
  return get('/meteo/horas-sol', { ...params })
}

export function getRealIrradiance(params: MeteoPeriod): Promise<IrradianceRealResponse> {
  return get('/meteo/irradiancia-real', { ...params })
}
