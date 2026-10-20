import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TooltipContentProps } from 'recharts'
import type { RainYearTotal } from '../../api/types'
import { formatMm } from '../../utils/meteo'

function CustomTooltip({ active, payload }: TooltipContentProps) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload as RainYearTotal
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
      <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{point.year}</div>
      <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
        {point.total_mm == null ? 'Datos incompletos' : formatMm(point.total_mm)}
      </div>
    </div>
  )
}

/** Lluvia total de cada año del período, con la media como referencia. */
export function RainYearlyChart({
  years,
  meanMm,
}: {
  years: RainYearTotal[]
  meanMm: number | null
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={years} margin={{ top: 16, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--gridline)" vertical={false} />
        <XAxis
          dataKey="year"
          minTickGap={16}
          stroke="var(--axis)"
          tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
        />
        <YAxis
          width={48}
          stroke="var(--axis)"
          tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
          label={{
            value: 'mm por año',
            angle: -90,
            position: 'insideLeft',
            fill: 'var(--text-muted)',
            fontSize: 12,
          }}
        />
        <Tooltip content={CustomTooltip} cursor={{ fill: 'var(--gridline)', fillOpacity: 0.4 }} />
        <Bar dataKey="total_mm" fill="var(--series-1)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
        {meanMm != null && (
          <ReferenceLine
            y={meanMm}
            stroke="var(--series-2)"
            strokeDasharray="4 4"
            label={{
              value: 'media',
              position: 'insideTopRight',
              fill: 'var(--text-secondary)',
              fontSize: 11,
            }}
          />
        )}
      </BarChart>
    </ResponsiveContainer>
  )
}
