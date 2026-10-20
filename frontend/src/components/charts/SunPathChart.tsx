import { useState } from 'react'
import type { SunPosition, TrajectoryResponse } from '../../api/types'
import { compassLabel } from '../../utils/compass'
import { formatTime } from '../../utils/date'

const SIZE = 320
const CENTER = SIZE / 2
const OUTER_RADIUS = CENTER - 36
const ALTITUDE_RINGS = [0, 30, 60]
const CARDINAL_POINTS = [
  { deg: 0, label: 'N' },
  { deg: 90, label: 'E' },
  { deg: 180, label: 'S' },
  { deg: 270, label: 'O' },
]

const LEGEND_ROW_HEIGHT = 18

/** Trayectoria de otra fecha, dibujada de fondo para comparar con la del
 * día elegido (ej. los solsticios y el equinoccio). */
export interface SunPathOverlay {
  label: string
  color: string
  samples: SunPosition[]
}

interface VisibleSample {
  index: number
  time: string
  altitude: number
  azimuth: number
}

/** Convierte azimut/altitud a un punto en el plano del gráfico. El centro
 * es el cenit (altitud 90°); el borde, el horizonte (altitud 0°) — la
 * convención estándar de un diagrama de trayectoria solar. Azimut 0°=Norte
 * arriba, en sentido horario. */
function toPoint(azimuthDeg: number, altitudeDeg: number): { x: number; y: number } {
  const clampedAltitude = Math.max(0, Math.min(90, altitudeDeg))
  const r = OUTER_RADIUS * (1 - clampedAltitude / 90)
  const rad = (azimuthDeg * Math.PI) / 180
  return { x: CENTER + r * Math.sin(rad), y: CENTER - r * Math.cos(rad) }
}

/** Puntos (en el plano del gráfico) de cada tramo contiguo con el sol
 * sobre el horizonte. */
function visibleSegments(samples: SunPosition[]): string[] {
  const segments: string[][] = []
  let current: string[] = []
  let previousIndex = -2
  samples.forEach((s, index) => {
    if (s.apparent_altitude <= 0) return
    if (index !== previousIndex + 1 && current.length > 0) {
      segments.push(current)
      current = []
    }
    const p = toPoint(s.azimuth, s.apparent_altitude)
    current.push(`${p.x},${p.y}`)
    previousIndex = index
  })
  if (current.length > 0) segments.push(current)
  return segments.map((points) => points.join(' '))
}

/** Trayectoria del Sol a lo largo de un día (punto 3), como gráfico polar:
 * altitud aparente (la que realmente se ve) como radio, azimut como
 * ángulo. Solo se dibuja el tramo con el sol sobre el horizonte. Con
 * `overlays`, dibuja además esas trayectorias de fondo, con leyenda. */
export function SunPathChart({
  data,
  timezone,
  overlays = [],
  bodyName = 'sol',
}: {
  data: TrajectoryResponse
  timezone: string
  overlays?: SunPathOverlay[]
  /** Cuerpo graficado, para los textos (`sol` o `luna`). */
  bodyName?: 'sol' | 'luna'
}) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  const legendHeight = overlays.length > 0 ? (overlays.length + 1) * LEGEND_ROW_HEIGHT + 8 : 0
  const totalHeight = SIZE + legendHeight

  const visible: VisibleSample[] = data.samples
    .map((s, index) => ({ index, time: s.time, altitude: s.apparent_altitude, azimuth: s.azimuth }))
    .filter((s) => s.altitude > 0)

  if (visible.length === 0) {
    return (
      <p style={{ color: 'var(--text-secondary)' }}>
        {bodyName === 'sol' ? 'El sol no sale' : 'La luna no sale'} este día en esta ubicación.
      </p>
    )
  }

  // Tramos contiguos: si el sol saliera/se pusiera más de una vez en el
  // muestreo (no pasa en un día normal, pero por las dudas) no se unen
  // con una línea recta cruzando la noche.
  const segments: VisibleSample[][] = []
  let current: VisibleSample[] = []
  for (let i = 0; i < visible.length; i++) {
    if (i > 0 && visible[i].index !== visible[i - 1].index + 1) {
      segments.push(current)
      current = []
    }
    current.push(visible[i])
  }
  segments.push(current)

  const peak = visible.reduce((max, s) => (s.altitude > max.altitude ? s : max), visible[0])
  const peakPoint = toPoint(peak.azimuth, peak.altitude)

  const hovered = hoveredIndex != null ? visible.find((s) => s.index === hoveredIndex) : null
  const hoveredPoint = hovered ? toPoint(hovered.azimuth, hovered.altitude) : null

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: `${SIZE}px`,
        aspectRatio: `${SIZE} / ${totalHeight}`,
      }}
    >
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${SIZE} ${totalHeight}`}
        role="img"
        aria-label={`Trayectoria ${bodyName === 'sol' ? 'del sol' : 'de la luna'} a lo largo del día`}
      >
        {ALTITUDE_RINGS.map((altitude) => (
          <circle
            key={altitude}
            cx={CENTER}
            cy={CENTER}
            r={OUTER_RADIUS * (1 - altitude / 90)}
            fill="none"
            stroke="var(--gridline)"
            strokeWidth={1}
          />
        ))}
        {ALTITUDE_RINGS.map((altitude) => (
          <text
            key={`label-${altitude}`}
            x={CENTER + 4}
            y={CENTER - OUTER_RADIUS * (1 - altitude / 90) - 4}
            fontSize={10}
            fill="var(--text-muted)"
          >
            {altitude}°
          </text>
        ))}

        {CARDINAL_POINTS.map(({ deg, label }) => {
          const rad = (deg * Math.PI) / 180
          const edgeX = CENTER + OUTER_RADIUS * Math.sin(rad)
          const edgeY = CENTER - OUTER_RADIUS * Math.cos(rad)
          const labelX = CENTER + (OUTER_RADIUS + 16) * Math.sin(rad)
          const labelY = CENTER - (OUTER_RADIUS + 16) * Math.cos(rad)
          return (
            <g key={deg}>
              <line x1={CENTER} y1={CENTER} x2={edgeX} y2={edgeY} stroke="var(--gridline)" strokeWidth={1} />
              <text
                x={labelX}
                y={labelY}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={12}
                fill="var(--text-secondary)"
              >
                {label}
              </text>
            </g>
          )
        })}

        {overlays.flatMap((overlay) =>
          visibleSegments(overlay.samples).map((points, si) => (
            <polyline
              key={`${overlay.label}-${si}`}
              points={points}
              fill="none"
              stroke={overlay.color}
              strokeWidth={1.75}
              strokeDasharray="5 3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )),
        )}

        {segments.map((segment, si) => (
          <polyline
            key={si}
            points={segment.map((s) => {
              const p = toPoint(s.azimuth, s.altitude)
              return `${p.x},${p.y}`
            }).join(' ')}
            fill="none"
            stroke="var(--series-1)"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}

        {segments.map((segment, si) => (
          <g key={`ends-${si}`}>
            {[segment[0], segment[segment.length - 1]].map((s, i) => {
              const p = toPoint(s.azimuth, s.altitude)
              return (
                <circle
                  key={i}
                  cx={p.x}
                  cy={p.y}
                  r={4}
                  fill="var(--series-1)"
                  stroke="var(--surface-1)"
                  strokeWidth={2}
                />
              )
            })}
          </g>
        ))}

        <circle
          cx={peakPoint.x}
          cy={peakPoint.y}
          r={4}
          fill="var(--series-1)"
          stroke="var(--surface-1)"
          strokeWidth={2}
        />
        <text
          x={peakPoint.x}
          y={peakPoint.y - 10}
          textAnchor="middle"
          fontSize={11}
          fill="var(--text-secondary)"
        >
          {bodyName === 'sol' ? 'mediodía' : 'culmina'}
        </text>

        {visible.map((s) => {
          const p = toPoint(s.azimuth, s.altitude)
          return (
            <circle
              key={s.index}
              cx={p.x}
              cy={p.y}
              r={10}
              fill="transparent"
              onMouseEnter={() => setHoveredIndex(s.index)}
              onMouseLeave={() => setHoveredIndex((current) => (current === s.index ? null : current))}
              style={{ cursor: 'pointer' }}
            />
          )
        })}

        {overlays.length > 0 &&
          [{ label: 'Fecha elegida', color: 'var(--series-1)', dashed: false }, ...overlays.map((o) => ({ ...o, dashed: true }))].map(
            (entry, i) => {
              const y = SIZE + 8 + i * LEGEND_ROW_HEIGHT
              return (
                <g key={entry.label}>
                  <line
                    x1={8}
                    y1={y}
                    x2={32}
                    y2={y}
                    stroke={entry.color}
                    strokeWidth={2}
                    strokeDasharray={entry.dashed ? '5 3' : undefined}
                  />
                  <text x={40} y={y} dominantBaseline="middle" fontSize={11} fill="var(--text-secondary)">
                    {entry.label}
                  </text>
                </g>
              )
            },
          )}

        {hoveredPoint && (
          <circle
            cx={hoveredPoint.x}
            cy={hoveredPoint.y}
            r={5}
            fill="var(--series-1)"
            stroke="var(--surface-1)"
            strokeWidth={2}
          />
        )}
      </svg>

      {hovered && hoveredPoint && (
        <div
          style={{
            position: 'absolute',
            left: `${(hoveredPoint.x / SIZE) * 100}%`,
            top: `${(hoveredPoint.y / totalHeight) * 100}%`,
            transform: 'translate(-50%, calc(-100% - 0.75rem))',
            background: 'var(--surface-1)',
            border: '1px solid var(--border)',
            borderRadius: '0.375rem',
            padding: '0.4rem 0.6rem',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.12)',
            pointerEvents: 'none',
            whiteSpace: 'nowrap',
            fontSize: '0.8rem',
          }}
        >
          <div style={{ color: 'var(--text-secondary)' }}>{formatTime(hovered.time, timezone)}</div>
          <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
            {hovered.altitude.toFixed(1)}° · {compassLabel(hovered.azimuth)}
          </div>
        </div>
      )}
    </div>
  )
}
