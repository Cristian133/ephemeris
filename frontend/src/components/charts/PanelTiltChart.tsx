import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TooltipContentProps } from 'recharts'
import type { PanelResponse, TiltEnergy } from '../../api/types'

function CustomTooltip({ active, payload }: TooltipContentProps) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload as TiltEnergy

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
      <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
        Inclinación {point.tilt_deg}°
      </div>
      <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
        {point.annual_kwh_per_m2.toFixed(0)} kWh/m² al año
      </div>
    </div>
  )
}

/** Energía anual recibida según la inclinación del panel (0° = horizontal,
 * 90° = vertical). Serie única; marca la inclinación óptima. */
export function PanelTiltChart({ data }: { data: PanelResponse }) {
  const best = data.curve.reduce((max, p) => (p.annual_kwh_per_m2 > max.annual_kwh_per_m2 ? p : max))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data.curve} margin={{ top: 24, right: 16, bottom: 16, left: 0 }}>
        <CartesianGrid stroke="var(--gridline)" vertical={false} />
        <XAxis
          dataKey="tilt_deg"
          ticks={[0, 15, 30, 45, 60, 75, 90]}
          tickFormatter={(v: number) => `${v}°`}
          stroke="var(--axis)"
          tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
          label={{
            value: 'inclinación del panel',
            position: 'insideBottom',
            offset: -8,
            fill: 'var(--text-muted)',
            fontSize: 12,
          }}
        />
        <YAxis
          width={56}
          domain={['auto', 'auto']}
          tickFormatter={(v: number) => v.toFixed(0)}
          stroke="var(--axis)"
          tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
          label={{
            value: 'kWh/m² al año',
            angle: -90,
            position: 'insideLeft',
            fill: 'var(--text-muted)',
            fontSize: 12,
          }}
        />
        <Tooltip content={CustomTooltip} />
        <Line
          type="monotone"
          dataKey="annual_kwh_per_m2"
          stroke="var(--series-1)"
          strokeWidth={2}
          strokeLinecap="round"
          dot={false}
          activeDot={{ r: 4, fill: 'var(--series-1)', stroke: 'var(--surface-1)', strokeWidth: 2 }}
          isAnimationActive={false}
        />
        <ReferenceDot
          x={best.tilt_deg}
          y={best.annual_kwh_per_m2}
          r={4}
          fill="var(--series-1)"
          stroke="var(--surface-1)"
          strokeWidth={2}
          label={{
            value: 'óptima',
            position: 'top',
            fill: 'var(--text-secondary)',
            fontSize: 11,
          }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
