import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { resetRateLimit, reverseGeocode, searchLocation } from './geocoding'

function okJson(data: unknown) {
  return { ok: true, json: async () => data }
}

beforeEach(() => {
  resetRateLimit()
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('searchLocation', () => {
  it('consultas de menos de 3 caracteres no pegan a la red', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    expect(await searchLocation('')).toEqual([])
    expect(await searchLocation('  a ')).toEqual([])
    expect(await searchLocation('ab')).toEqual([])
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('parsea resultados a numeros', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(okJson([{ display_name: 'Cordoba, AR', lat: '-31.4', lon: '-64.18' }]))
    vi.stubGlobal('fetch', fetchMock)
    const results = await searchLocation('Cordoba')
    expect(results).toEqual([{ displayName: 'Cordoba, AR', latitude: -31.4, longitude: -64.18 }])
    const url = new URL(fetchMock.mock.calls[0][0] as string)
    expect(url.searchParams.get('q')).toBe('Cordoba')
    expect(url.searchParams.get('limit')).toBe('5')
  })

  it('respuesta vacia da lista vacia', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(okJson([])))
    expect(await searchLocation('zzzzzz')).toEqual([])
  })

  it('un body que no es lista da lista vacia', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(okJson({ error: 'x' })))
    expect(await searchLocation('Cordoba')).toEqual([])
  })

  it('descarta resultados con coordenadas no numericas', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        okJson([
          { display_name: 'malo', lat: 'x', lon: '1' },
          { display_name: 'bueno', lat: '1', lon: '2' },
        ]),
      ),
    )
    const results = await searchLocation('lugar')
    expect(results.map((r) => r.displayName)).toEqual(['bueno'])
  })

  it('error HTTP (429) incluye el status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 429, statusText: 'Too Many Requests' }),
    )
    await expect(searchLocation('Cordoba')).rejects.toThrow('Nominatim: 429')
  })

  it('error de red se propaga', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(searchLocation('Cordoba')).rejects.toThrow(TypeError)
  })

  it('pasa el signal a fetch y propaga AbortError', async () => {
    const controller = new AbortController()
    const fetchMock = vi.fn().mockImplementation((_url: string, init: RequestInit) => {
      return new Promise((_resolve, reject) => {
        if (init.signal?.aborted) reject(new DOMException('Aborted', 'AbortError'))
        init.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        )
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const promise = searchLocation('Cordoba', controller.signal)
    controller.abort()
    await expect(promise).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('espacia las requests consecutivas (rate limit de Nominatim)', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockResolvedValue(okJson([]))
    vi.stubGlobal('fetch', fetchMock)
    const first = searchLocation('Cordoba')
    const second = searchLocation('Rosario')
    await vi.advanceTimersByTimeAsync(0)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(200)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    await Promise.all([first, second])
  })

  it('abortar mientras espera el turno no llega a pedir nada', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockResolvedValue(okJson([]))
    vi.stubGlobal('fetch', fetchMock)
    void searchLocation('Cordoba')
    const controller = new AbortController()
    const waiting = searchLocation('Rosario', controller.signal)
    const assertion = expect(waiting).rejects.toMatchObject({ name: 'AbortError' })
    controller.abort()
    await assertion
    await vi.advanceTimersByTimeAsync(5000)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})

describe('reverseGeocode', () => {
  it('devuelve el nombre', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(okJson({ display_name: 'Rosario, AR' })))
    expect(await reverseGeocode(-32.9, -60.6)).toBe('Rosario, AR')
  })

  it('null si Nominatim no conoce el punto (error en body)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(okJson({ error: 'Unable to geocode' })))
    expect(await reverseGeocode(0, 0)).toBeNull()
  })

  it('null ante error HTTP', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 429 }))
    expect(await reverseGeocode(0, 0)).toBeNull()
  })

  it('null ante error de red', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    expect(await reverseGeocode(0, 0)).toBeNull()
  })
})
