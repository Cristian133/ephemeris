import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TooltipContentProps } from 'recharts'
import type { IrradianceResponse } from '../../api/types'
import { formatTime } from '../../utils/date'

interface ChartPoint {
  time: string
  power: number
  direct: number
  diffuse: number
}

function CustomTooltip({
  active,
  payload,
  timezone,
}: TooltipContentProps & { timezone: string }) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload as ChartPoint

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
        {formatTime(point.time, timezone)}
      </div>
      <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
        {point.power.toFixed(0)} W/m²
      </div>
      <div style={{ color: 'var(--series-1)', fontSize: '0.8rem' }}>
        Directa {point.direct.toFixed(0)} W/m²
      </div>
      <div style={{ color: 'var(--series-3)', fontSize: '0.8rem' }}>
        Difusa {point.diffuse.toFixed(0)} W/m²
      </div>
    </div>
  )
}

/** Irradiancia solar (cielo despejado) a lo largo de un día (punto 5):
 * área apilada de la componente directa y la difusa, con la global como
 * borde superior. Las dos series se rotulan con una leyenda mínima y el
 * pico de la global se marca directamente. */
export function DailyIrradianceChart({
  data,
  timezone,
}: {
  data: IrradianceResponse
  timezone: string
}) {
  const points: ChartPoint[] = data.samples.map((s) => ({
    time: s.time,
    power: s.power_w_per_m2,
    direct: s.direct_w_per_m2,
    diffuse: s.diffuse_w_per_m2,
  }))
  const peak = points.reduce((max, p) => (p.power > max.power ? p : max), points[0])

  return (
    <>
    <ResponsiveContainer width="100%" height={320}>
      <AreaChart data={points} margin={{ top: 16, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--gridline)" vertical={false} />
        <XAxis
          dataKey="time"
          tickFormatter={(t: string) => formatTime(t, timezone)}
          interval={Math.max(Math.floor(points.length / 8) - 1, 0)}
          stroke="var(--axis)"
          tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
        />
        <YAxis
          width={48}
          domain={[0, 'auto']}
          stroke="var(--axis)"
          tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
          label={{
            value: 'W/m²',
            angle: -90,
            position: 'insideLeft',
            fill: 'var(--text-muted)',
            fontSize: 12,
          }}
        />
        <Tooltip content={(props) => <CustomTooltip {...props} timezone={timezone} />} />
        <Area
          type="monotone"
          dataKey="direct"
          stackId="irradiance"
          stroke="var(--series-1)"
          strokeWidth={2}
          fill="var(--series-1)"
          fillOpacity={0.15}
          dot={false}
          isAnimationActive={false}
        />
        <Area
          type="monotone"
          dataKey="diffuse"
          stackId="irradiance"
          stroke="var(--series-3)"
          strokeWidth={2}
          fill="var(--series-3)"
          fillOpacity={0.15}
          dot={false}
          isAnimationActive={false}
        />
        {peak.power > 0 && (
          <ReferenceDot
            x={peak.time}
            y={peak.power}
            r={4}
            fill="var(--text-secondary)"
            stroke="var(--surface-1)"
            strokeWidth={2}
            label={{
              value: `${peak.power.toFixed(0)} W/m² máx.`,
              position: 'top',
              fill: 'var(--text-secondary)',
              fontSize: 11,
            }}
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
    <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
      <span style={{ color: 'var(--series-1)' }}>Directa</span>
      <span style={{ color: 'var(--series-3)' }}>Difusa</span>
    </div>
    </>
  )
}
