import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { CloudMonth } from '../../api/types'
import { MONTH_LABELS } from '../../utils/meteo'

/** Días por mes según el cielo: despejado, parcialmente nublado y cubierto,
 * apilados (suman los días del mes). */
export function CloudDaysChart({ months }: { months: CloudMonth[] }) {
  const points = months.map((m) => ({
    label: MONTH_LABELS[m.month - 1],
    clear: m.clear_days,
    partly: m.partly_days,
    overcast: m.overcast_days,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={points} margin={{ top: 16, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--gridline)" vertical={false} />
        <XAxis dataKey="label" stroke="var(--axis)" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
        <YAxis
          width={48}
          domain={[0, 31]}
          stroke="var(--axis)"
          tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
          label={{
            value: 'días por mes',
            angle: -90,
            position: 'insideLeft',
            fill: 'var(--text-muted)',
            fontSize: 12,
          }}
        />
        <Tooltip
          formatter={(value) => (typeof value === 'number' ? value.toFixed(1) : '—')}
          contentStyle={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border)',
            borderRadius: '0.375rem',
          }}
          cursor={{ fill: 'var(--gridline)', fillOpacity: 0.4 }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }} />
        <Bar dataKey="clear" name="Despejados" stackId="sky" fill="var(--series-2)" isAnimationActive={false} />
        <Bar dataKey="partly" name="Parcialmente nublados" stackId="sky" fill="var(--series-1)" fillOpacity={0.45} isAnimationActive={false} />
        <Bar dataKey="overcast" name="Cubiertos" stackId="sky" fill="var(--text-muted)" isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}
