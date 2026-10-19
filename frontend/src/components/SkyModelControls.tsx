import type { SkyModel } from '../api/client'

const TURBIDITY_PRESETS: { label: string; value: number }[] = [
  { label: 'Aire muy limpio (alta montaña)', value: 2 },
  { label: 'Limpio (rural)', value: 3 },
  { label: 'Algo turbio (periurbano)', value: 4 },
  { label: 'Turbio (ciudad, polvo)', value: 5.5 },
]

const ALBEDO_PRESETS: { label: string; value: number }[] = [
  { label: 'Asfalto / oscuro (0.1)', value: 0.1 },
  { label: 'Pasto / suelo (0.2)', value: 0.2 },
  { label: 'Cemento claro / arena (0.35)', value: 0.35 },
  { label: 'Nieve fresca (0.8)', value: 0.8 },
]

interface Props {
  sky: SkyModel
  onChange: (sky: SkyModel) => void
  albedo?: number
  onAlbedoChange?: (albedo: number) => void
}

/** Parámetros del modelo de cielo despejado: altitud del lugar, turbidez
 * del aire y, opcionalmente, reflectividad del suelo (solo la usa el
 * panel solar). */
export function SkyModelControls({ sky, onChange, albedo, onAlbedoChange }: Props) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', margin: '0 0 1.5rem' }}>
      <label>
        Altitud del lugar (m):{' '}
        <input
          type="number"
          min={-500}
          max={9000}
          value={sky.elevation_m}
          onChange={(e) => {
            const value = Number(e.target.value)
            if (Number.isFinite(value) && value >= -500 && value <= 9000) {
              onChange({ ...sky, elevation_m: value })
            }
          }}
          style={{ width: '6rem' }}
        />
      </label>
      <label>
        Aire:{' '}
        <select
          value={sky.linke_turbidity}
          onChange={(e) => onChange({ ...sky, linke_turbidity: Number(e.target.value) })}
        >
          {TURBIDITY_PRESETS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </label>
      {albedo !== undefined && onAlbedoChange && (
        <label>
          Suelo:{' '}
          <select value={albedo} onChange={(e) => onAlbedoChange(Number(e.target.value))}>
            {ALBEDO_PRESETS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  )
}
