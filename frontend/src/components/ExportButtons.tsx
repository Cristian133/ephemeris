import { useState } from 'react'
import type { RefObject } from 'react'
import { downloadCsv, downloadSvgAsPng } from '../utils/export'

const buttonStyle = {
  padding: '0.3rem 0.65rem',
  borderRadius: '0.375rem',
  border: '1px solid var(--axis)',
  background: 'var(--surface-1)',
  color: 'var(--text-primary)',
  fontSize: '0.8rem',
  cursor: 'pointer',
} as const

/** Botones para descargar los datos de una vista como CSV y/o su gráfico
 * como PNG. `chartRef` apunta al contenedor del gráfico: se exporta el
 * primer `<svg>` que contenga. `filename` va sin extensión. */
export function ExportButtons({
  filename,
  getCsvRows,
  chartRef,
}: {
  filename: string
  getCsvRows?: () => (string | number | null)[][]
  chartRef?: RefObject<HTMLElement | null>
}) {
  const [error, setError] = useState<string | null>(null)

  async function exportImage() {
    const svg = chartRef?.current?.querySelector('svg')
    if (!svg) return
    setError(null)
    try {
      await downloadSvgAsPng(svg, `${filename}.png`)
    } catch {
      setError('No se pudo exportar la imagen.')
    }
  }

  return (
    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', margin: '0.5rem 0' }}>
      {getCsvRows && (
        <button type="button" style={buttonStyle} onClick={() => downloadCsv(`${filename}.csv`, getCsvRows())}>
          Descargar CSV
        </button>
      )}
      {chartRef && (
        <button type="button" style={buttonStyle} onClick={exportImage}>
          Descargar imagen
        </button>
      )}
      {error && <span style={{ fontSize: '0.8rem', color: 'var(--series-2)' }}>{error}</span>}
    </div>
  )
}
