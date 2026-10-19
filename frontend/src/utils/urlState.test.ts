// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest'
import { buildUrlParams, readDateFromUrl, readLocationFromUrl } from './urlState'

function setSearch(search: string) {
  window.history.replaceState(null, '', `/${search}`)
}

beforeEach(() => setSearch(''))

describe('readLocationFromUrl', () => {
  it('lee una ubicacion completa', () => {
    setSearch('?lat=-34.6&lon=-58.4&tz=America/Argentina/Buenos_Aires&n=Buenos%20Aires')
    expect(readLocationFromUrl()).toEqual({
      displayName: 'Buenos Aires',
      latitude: -34.6,
      longitude: -58.4,
      timezone: 'America/Argentina/Buenos_Aires',
    })
  })

  it('sin nombre usa las coordenadas', () => {
    setSearch('?lat=-34.6&lon=-58.4&tz=UTC')
    expect(readLocationFromUrl()?.displayName).toBe('-34.6000, -58.4000')
  })

  it('devuelve null si falta algun parametro', () => {
    setSearch('?lon=-58.4&tz=UTC')
    expect(readLocationFromUrl()).toBeNull()
    setSearch('?lat=1&lon=2')
    expect(readLocationFromUrl()).toBeNull()
  })

  it('rechaza coordenadas fuera de rango o no numericas', () => {
    setSearch('?lat=91&lon=0&tz=UTC')
    expect(readLocationFromUrl()).toBeNull()
    setSearch('?lat=0&lon=181&tz=UTC')
    expect(readLocationFromUrl()).toBeNull()
    setSearch('?lat=abc&lon=0&tz=UTC')
    expect(readLocationFromUrl()).toBeNull()
    setSearch('?lat=Infinity&lon=0&tz=UTC')
    expect(readLocationFromUrl()).toBeNull()
  })

  it('rechaza un huso horario inexistente', () => {
    setSearch('?lat=0&lon=0&tz=Marte/Olympus')
    expect(readLocationFromUrl()).toBeNull()
  })

  it('acepta el borde de los rangos y lat/lon 0', () => {
    setSearch('?lat=0&lon=0&tz=UTC')
    expect(readLocationFromUrl()).toMatchObject({ latitude: 0, longitude: 0 })
    setSearch('?lat=-90&lon=180&tz=UTC')
    expect(readLocationFromUrl()).toMatchObject({ latitude: -90, longitude: 180 })
  })
})

describe('readDateFromUrl', () => {
  it('lee fechas validas', () => {
    setSearch('?fecha=2024-02-29')
    expect(readDateFromUrl()).toBe('2024-02-29')
  })

  it('ignora fechas ausentes o invalidas', () => {
    expect(readDateFromUrl()).toBeNull()
    setSearch('?fecha=2024-02-31')
    expect(readDateFromUrl()).toBeNull()
    setSearch('?fecha=hoy')
    expect(readDateFromUrl()).toBeNull()
  })
})

describe('buildUrlParams', () => {
  it('sin ubicacion solo incluye la fecha', () => {
    expect(buildUrlParams(null, '2024-06-10')).toEqual({ fecha: '2024-06-10' })
  })

  it('con ubicacion hace ida y vuelta con readLocationFromUrl', () => {
    const location = {
      displayName: 'Cordoba, Argentina & alrededores',
      latitude: -31.4,
      longitude: -64.18,
      timezone: 'America/Argentina/Cordoba',
    }
    const params = buildUrlParams(location, '2024-06-10')
    expect(params).toEqual({
      fecha: '2024-06-10',
      lat: '-31.4',
      lon: '-64.18',
      tz: 'America/Argentina/Cordoba',
      n: location.displayName,
    })
    setSearch(`?${new URLSearchParams(params)}`)
    expect(readLocationFromUrl()).toEqual(location)
    expect(readDateFromUrl()).toBe('2024-06-10')
  })
})
