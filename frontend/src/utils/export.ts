/** Descargas del lado del cliente: tablas como CSV y gráficos SVG como PNG. */

type Cell = string | number | null

function triggerDownload(url: string, filename: string): void {
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
}

function escapeCsv(cell: Cell): string {
  if (cell == null) return ''
  const text = String(cell)
  return /[",\n;]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function downloadCsv(filename: string, rows: Cell[][]): void {
  // BOM para que Excel reconozca UTF-8 (acentos en los encabezados).
  const content = '﻿' + rows.map((row) => row.map(escapeCsv).join(',')).join('\n')
  const url = URL.createObjectURL(new Blob([content], { type: 'text/csv;charset=utf-8' }))
  triggerDownload(url, filename)
  URL.revokeObjectURL(url)
}

const PAINT_ATTRIBUTES = ['fill', 'stroke', 'stop-color', 'color']

/** Los gráficos usan `var(--token)` en sus atributos; un SVG exportado
 * como imagen no tiene acceso al CSS de la página, así que se reemplazan
 * por el valor calculado en ese momento (respetando claro/oscuro). */
function resolveCssVariables(svg: SVGSVGElement): void {
  const rootStyle = getComputedStyle(document.documentElement)
  const resolve = (text: string) =>
    text.replace(/var\((--[\w-]+)\)/g, (_, name: string) => rootStyle.getPropertyValue(name).trim())

  for (const element of [svg, ...svg.querySelectorAll('*')]) {
    for (const attribute of PAINT_ATTRIBUTES) {
      const value = element.getAttribute(attribute)
      if (value?.includes('var(')) element.setAttribute(attribute, resolve(value))
    }
    const style = element.getAttribute('style')
    if (style?.includes('var(')) element.setAttribute('style', resolve(style))
  }
}

export async function downloadSvgAsPng(svg: SVGSVGElement, filename: string): Promise<void> {
  const { width, height } = svg.getBoundingClientRect()
  const clone = svg.cloneNode(true) as SVGSVGElement
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  clone.setAttribute('width', String(width))
  clone.setAttribute('height', String(height))
  if (!clone.getAttribute('viewBox')) clone.setAttribute('viewBox', `0 0 ${width} ${height}`)
  clone.style.fontFamily = getComputedStyle(document.body).fontFamily
  resolveCssVariables(clone)

  const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
  background.setAttribute('width', '100%')
  background.setAttribute('height', '100%')
  background.setAttribute(
    'fill',
    getComputedStyle(document.documentElement).getPropertyValue('--surface-1').trim(),
  )
  clone.insertBefore(background, clone.firstChild)

  const image = new Image()
  const loaded = new Promise<void>((resolve, reject) => {
    image.onload = () => resolve()
    image.onerror = () => reject(new Error('No se pudo renderizar el gráfico.'))
  })
  image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(new XMLSerializer().serializeToString(clone))}`
  await loaded

  const scale = 2 // 2x para que no se vea borroso en pantallas de alta densidad
  const canvas = document.createElement('canvas')
  canvas.width = width * scale
  canvas.height = height * scale
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Canvas no disponible.')
  context.scale(scale, scale)
  context.drawImage(image, 0, 0, width, height)
  triggerDownload(canvas.toDataURL('image/png'), filename)
}
