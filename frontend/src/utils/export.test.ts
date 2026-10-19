// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { downloadCsv } from './export'

afterEach(() => vi.restoreAllMocks())

// jsdom no implementa Blob.text(): se lee con FileReader.
function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () =>
      // ignoreBOM: conservar el BOM para poder verificarlo.
      resolve(new TextDecoder('utf-8', { ignoreBOM: true }).decode(reader.result as ArrayBuffer))
    reader.onerror = () => reject(reader.error)
    reader.readAsArrayBuffer(blob)
  })
}

async function capturedCsv(rows: (string | number | null)[][]) {
  let blob: Blob | undefined
  vi.stubGlobal('URL', {
    createObjectURL: (b: Blob) => {
      blob = b
      return 'blob:test'
    },
    revokeObjectURL: vi.fn(),
  })
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  downloadCsv('datos.csv', rows)
  expect(click).toHaveBeenCalledOnce()
  return { text: await readBlob(blob!), type: blob!.type }
}

describe('downloadCsv', () => {
  it('genera filas separadas por coma con BOM UTF-8', async () => {
    const { text, type } = await capturedCsv([
      ['Fecha', 'Salida'],
      ['2024-06-10', 7.5],
    ])
    expect(type).toContain('text/csv')
    expect(text.startsWith('﻿')).toBe(true)
    expect(text.slice(1)).toBe('Fecha,Salida\n2024-06-10,7.5')
  })

  it('escapa comillas, comas, saltos de linea y punto y coma', async () => {
    const { text } = await capturedCsv([['a,b', 'di "hola"', 'l1\nl2', 'x;y']])
    expect(text.slice(1)).toBe('"a,b","di ""hola""","l1\nl2","x;y"')
  })

  it('null queda vacio y 0 se conserva', async () => {
    const { text } = await capturedCsv([[null, 0, '']])
    expect(text.slice(1)).toBe(',0,')
  })

  it('asigna el nombre de archivo y libera la URL', async () => {
    const created: HTMLAnchorElement[] = []
    const realCreate = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = realCreate(tag)
      if (tag === 'a') created.push(el as HTMLAnchorElement)
      return el
    })
    await capturedCsv([['x']])
    expect(created[0].download).toBe('datos.csv')
    expect(created[0].href).toBe('blob:test')
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:test')
  })
})
