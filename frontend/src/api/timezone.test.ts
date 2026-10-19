import { afterEach, describe, expect, it, vi } from 'vitest'
import { resolveTimezone } from './timezone'

afterEach(() => vi.unstubAllGlobals())

describe('resolveTimezone', () => {
  it('devuelve el huso y pide timezone=auto', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ timezone: 'America/Argentina/Buenos_Aires' }) })
    vi.stubGlobal('fetch', fetchMock)
    await expect(resolveTimezone(-34.6, -58.4)).resolves.toBe('America/Argentina/Buenos_Aires')
    const url = new URL(fetchMock.mock.calls[0][0] as string)
    expect(url.searchParams.get('timezone')).toBe('auto')
    expect(url.searchParams.get('latitude')).toBe('-34.6')
  })

  it('pasa el AbortSignal a fetch', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ timezone: 'UTC' }) })
    vi.stubGlobal('fetch', fetchMock)
    const controller = new AbortController()
    await resolveTimezone(0, 0, controller.signal)
    expect(fetchMock.mock.calls[0][1]).toEqual({ signal: controller.signal })
  })

  it('error HTTP incluye el status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 429, statusText: 'Too Many Requests' }),
    )
    await expect(resolveTimezone(0, 0)).rejects.toThrow('Open-Meteo: 429 Too Many Requests')
  })

  it('respuesta sin timezone lanza error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }))
    await expect(resolveTimezone(0, 0)).rejects.toThrow('huso horario')
  })

  it('timezone vacio tambien es error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ timezone: '' }) }))
    await expect(resolveTimezone(0, 0)).rejects.toThrow()
  })

  it('error de red se propaga', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(resolveTimezone(0, 0)).rejects.toThrow(TypeError)
  })

  it('JSON invalido se propaga como error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => {
          throw new SyntaxError('bad json')
        },
      }),
    )
    await expect(resolveTimezone(0, 0)).rejects.toThrow(SyntaxError)
  })
})
