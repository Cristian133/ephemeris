import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TooltipContentProps } from 'recharts'
import type { TideDayResponse, TideSample } from '../../api/types'
import { formatTime } from '../../utils/date'

function CustomTooltip({ active, payload, timezone }: TooltipContentProps & { timezone: string }) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload as TideSample
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
      <div style={{ fontWeight: 600 }}>Total {point.total_m.toFixed(2)} m</div>
      <div style={{ color: 'var(--series-3)', fontSize: '0.8rem' }}>Luna {point.moon_m.toFixed(2)} m</div>
      <div style={{ color: 'var(--series-2)', fontSize: '0.8rem' }}>Sol {point.sun_m.toFixed(2)} m</div>
    </div>
  )
}

/** Marea de equilibrio a lo largo del día: la total (Luna + Sol) como serie
 * principal y las de la Luna y el Sol por separado, más finas. */
export function TideChart({ data, timezone }: { data: TideDayResponse; timezone: string }) {
  return (
    <>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data.samples} margin={{ top: 16, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--gridline)" vertical={false} />
          <XAxis
            dataKey="time"
            tickFormatter={(t: string) => formatTime(t, timezone)}
            interval={Math.max(Math.floor(data.samples.length / 8) - 1, 0)}
            stroke="var(--axis)"
            tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
          />
          <YAxis
            width={48}
            stroke="var(--axis)"
            tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
            tickFormatter={(v: number) => v.toFixed(1)}
            label={{ value: 'm', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 12 }}
          />
          <ReferenceLine y={0} stroke="var(--axis)" />
          <Tooltip content={(props) => <CustomTooltip {...props} timezone={timezone} />} />
          <Line type="monotone" dataKey="sun_m" stroke="var(--series-2)" strokeWidth={1} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="moon_m" stroke="var(--series-3)" strokeWidth={1} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="total_m" stroke="var(--series-1)" strokeWidth={2.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
        <span style={{ color: 'var(--series-1)' }}>Total</span>
        <span style={{ color: 'var(--series-3)' }}>Luna</span>
        <span style={{ color: 'var(--series-2)' }}>Sol</span>
      </div>
    </>
  )
}
