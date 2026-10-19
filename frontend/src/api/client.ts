import type {
  AnnualSunResponse,
  DailySunResponse,
  IrradianceResponse,
  PanelResponse,
  SeasonsResponse,
  SolarNoonResponse,
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

export function getIrradiance(
  { latitude, longitude, date }: LocationDate,
  numSamples = 96,
): Promise<IrradianceResponse> {
  return get('/sol/irradiancia', { latitude, longitude, date, num_samples: numSamples })
}

export function getTwilight({ latitude, longitude, date }: LocationDate): Promise<TwilightResponse> {
  return get('/sol/crepusculos', { latitude, longitude, date })
}

export function getSeasons(year: number): Promise<SeasonsResponse> {
  return get('/sol/estaciones', { year })
}

export function getPanel(params: {
  latitude: number
  longitude: number
  year: number
}): Promise<PanelResponse> {
  return get('/sol/panel', params)
}
