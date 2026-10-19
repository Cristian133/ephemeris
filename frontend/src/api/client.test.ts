import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, getDailySun, getIrradiance, getPanel, getSeasons, getTrajectory } from './client'

function mockFetch(response: Partial<Response> & { json?: () => Promise<unknown> }) {
  const fn = vi.fn().mockResolvedValue(response)
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

describe('client get', () => {
  it('arma la query string y devuelve el JSON', async () => {
    const fetchMock = mockFetch({ ok: true, json: async () => ({ ok: 1 }) })
    const result = await getDailySun({ latitude: -34.6, longitude: -58.4, date: '2024-06-10' })
    expect(result).toEqual({ ok: 1 })
    const url = new URL(fetchMock.mock.calls[0][0] as string)
    expect(url.pathname).toBe('/sol/dia')
    expect(Object.fromEntries(url.searchParams)).toEqual({
      latitude: '-34.6',
      longitude: '-58.4',
      date: '2024-06-10',
    })
  })

  it('getTrajectory manda num_samples (96 por defecto)', async () => {
    const fetchMock = mockFetch({ ok: true, json: async () => ({}) })
    await getTrajectory({ latitude: 0, longitude: 0, date: '2024-06-10' })
    await getTrajectory({ latitude: 0, longitude: 0, date: '2024-06-10' }, 24)
    expect(new URL(fetchMock.mock.calls[0][0] as string).searchParams.get('num_samples')).toBe('96')
    expect(new URL(fetchMock.mock.calls[1][0] as string).searchParams.get('num_samples')).toBe('24')
  })

  it('getIrradiance y getPanel mandan los parametros del modelo de cielo', async () => {
    const fetchMock = mockFetch({ ok: true, json: async () => ({}) })
    const sky = { elevation_m: 650, linke_turbidity: 4 }
    await getIrradiance({ latitude: 40, longitude: -3, date: '2024-06-21' }, sky)
    await getPanel({ latitude: 40, longitude: -3, year: 2024, albedo: 0.8, ...sky })
    const irradiance = new URL(fetchMock.mock.calls[0][0] as string)
    expect(irradiance.pathname).toBe('/sol/irradiancia')
    expect(irradiance.searchParams.get('elevation_m')).toBe('650')
    expect(irradiance.searchParams.get('linke_turbidity')).toBe('4')
    const panel = new URL(fetchMock.mock.calls[1][0] as string)
    expect(panel.searchParams.get('albedo')).toBe('0.8')
    expect(panel.searchParams.get('elevation_m')).toBe('650')
  })

  it('latitud/longitud 0 no se pierden al serializar', async () => {
    const fetchMock = mockFetch({ ok: true, json: async () => ({}) })
    await getSeasons(2024)
    await getDailySun({ latitude: 0, longitude: 0, date: '2024-06-10' })
    const url = new URL(fetchMock.mock.calls[1][0] as string)
    expect(url.searchParams.get('latitude')).toBe('0')
  })

  it('ApiError con detail JSON de FastAPI', async () => {
    mockFetch({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: async () => ({ detail: [{ msg: 'latitud fuera de rango' }] }),
    })
    const error = await getSeasons(2024).catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.name).toBe('ApiError')
    expect(error.status).toBe(422)
    expect(error.message).toContain('/sol/estaciones')
    expect(error.message).toContain('latitud fuera de rango')
  })

  it('ApiError con body no-JSON cae al statusText', async () => {
    mockFetch({
      ok: false,
      status: 502,
      statusText: 'Bad Gateway',
      json: async () => {
        throw new SyntaxError('Unexpected token <')
      },
    })
    const error = await getSeasons(2024).catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(502)
    expect(error.message).toBe('/sol/estaciones: Bad Gateway')
  })

  it('ApiError con JSON sin detail usa statusText', async () => {
    mockFetch({ ok: false, status: 500, statusText: 'Internal Server Error', json: async () => ({}) })
    const error = await getSeasons(2024).catch((e) => e)
    expect(error.message).toBe('/sol/estaciones: Internal Server Error')
  })

  it('ApiError con body null (JSON "null")', async () => {
    mockFetch({ ok: false, status: 404, statusText: 'Not Found', json: async () => null })
    const error = await getSeasons(2024).catch((e) => e)
    expect(error.status).toBe(404)
  })

  it('un error de red se propaga tal cual', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(getSeasons(2024)).rejects.toThrow(TypeError)
  })
})
