import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TooltipContentProps } from 'recharts'

export interface MonthlyBandPoint {
  label: string
  mean: number | null
  /** Rango típico (percentiles 10 a 90), o `null` si no hay datos. */
  range: [number, number] | null
  /** Valor de referencia del mes (línea punteada), si el gráfico la tiene. */
  reference?: number
  /** Segundo valor de comparación del mes (línea punteada gris), si lo hay. */
  extra?: number
}

function BandTooltip({
  active,
  payload,
  format,
  referenceLabel,
  extraLabel,
}: TooltipContentProps & {
  format: (value: number | null) => string
  referenceLabel?: string
  extraLabel?: string
}) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload as MonthlyBandPoint
  if (point.mean == null) return null
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--border)',
        borderRadius: '0.375rem',
        padding: '0.5rem 0.75rem',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.12)',
      }}
    >
      <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{point.label}</div>
      <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
        {format(point.mean)} en promedio
      </div>
      {point.range && (
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
          Típico: {format(point.range[0])} a {format(point.range[1])}
        </div>
      )}
      {point.reference != null && referenceLabel && (
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
          {referenceLabel}: {format(point.reference)}
        </div>
      )}
      {point.extra != null && extraLabel && (
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
          {extraLabel}: {format(point.extra)}
        </div>
      )}
    </div>
  )
}

/** Gráfico de 12 meses: línea con la media, banda con el rango típico y,
 * opcionalmente, una línea punteada de referencia. Lo comparten lluvia,
 * nubosidad y horas de sol. */
export function MonthlyBandChart({
  points,
  yLabel,
  format,
  referenceLabel,
  extraLabel,
  domain,
}: {
  points: MonthlyBandPoint[]
  yLabel: string
  format: (value: number | null) => string
  referenceLabel?: string
  extraLabel?: string
  domain?: [number, number]
}) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={points} margin={{ top: 16, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--gridline)" vertical={false} />
        <XAxis dataKey="label" stroke="var(--axis)" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
        <YAxis
          width={48}
          domain={domain}
          stroke="var(--axis)"
          tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
          label={{
            value: yLabel,
            angle: -90,
            position: 'insideLeft',
            fill: 'var(--text-muted)',
            fontSize: 12,
          }}
        />
        <Tooltip
          content={(props) => (
            <BandTooltip
              {...props}
              format={format}
              referenceLabel={referenceLabel}
              extraLabel={extraLabel}
            />
          )}
        />
        <Bar
          dataKey="range"
          fill="var(--series-1)"
          fillOpacity={0.2}
          barSize={22}
          isAnimationActive={false}
        />
        {referenceLabel && (
          <Line
            type="monotone"
            dataKey="reference"
            stroke="var(--series-2)"
            strokeWidth={2}
            strokeDasharray="4 4"
            dot={false}
            isAnimationActive={false}
          />
        )}
        {extraLabel && (
          <Line
            type="monotone"
            dataKey="extra"
            stroke="var(--text-muted)"
            strokeWidth={2}
            strokeDasharray="2 4"
            dot={false}
            isAnimationActive={false}
          />
        )}
        <Line
          type="monotone"
          dataKey="mean"
          stroke="var(--series-1)"
          strokeWidth={2}
          strokeLinecap="round"
          dot={{ r: 3, fill: 'var(--series-1)', stroke: 'var(--surface-1)', strokeWidth: 1 }}
          activeDot={{ r: 4, fill: 'var(--series-1)', stroke: 'var(--surface-1)', strokeWidth: 2 }}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
