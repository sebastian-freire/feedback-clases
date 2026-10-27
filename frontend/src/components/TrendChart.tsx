import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ClassSummary } from '../api/types'
import { dateShort, formatAverage, timeShort } from '../lib/format'
import { ratingLabel } from '../lib/rating'
import { Face } from './Face'

type Point = { label: string; average: number; responses: number; time: string }

function ChartTooltip({ active, payload }: { active?: boolean; payload?: { payload: Point }[] }) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-line bg-surface px-3 py-2 shadow-md">
      <Face rating={point.average} size={24} />
      <div className="text-sm leading-snug">
        <p className="font-medium">
          {point.label}, {point.time} h
        </p>
        <p>
          Promedio {formatAverage(point.average)} ({ratingLabel(point.average).toLowerCase()})
        </p>
        <p className="text-muted">
          {point.responses} {point.responses === 1 ? 'respuesta' : 'respuestas'}
        </p>
      </div>
    </div>
  )
}

/** Promedio por clase a lo largo del semestre (una sola serie: sin leyenda, el título la nombra). */
export function TrendChart({ classes }: { classes: ClassSummary[] }) {
  // Solo clases con respuestas: una clase sin datos no es un promedio de cero.
  const data: Point[] = classes
    .filter((c) => c.average !== null)
    .map((c) => ({ label: dateShort(c.date), average: c.average as number, responses: c.response_count, time: timeShort(c.start_time) }))

  if (data.length < 2) {
    return <p className="py-6 text-center text-sm text-muted">Hacen falta al menos dos clases con respuestas para ver la tendencia.</p>
  }

  return (
    <div className="h-60 w-full" role="img" aria-label="Gráfico del promedio por clase a lo largo del semestre; los valores están en la tabla de abajo.">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 12, right: 12, bottom: 4, left: -24 }}>
          <CartesianGrid vertical={false} stroke="var(--line)" strokeWidth={1} />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={{ stroke: 'var(--line)' }}
            tick={{ fill: 'var(--muted)', fontSize: 12 }}
            interval="preserveStartEnd"
            minTickGap={24}
            tickMargin={8}
          />
          <YAxis
            domain={[1, 5]}
            ticks={[1, 2, 3, 4, 5]}
            tickLine={false}
            axisLine={false}
            tick={{ fill: 'var(--muted)', fontSize: 12 }}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'var(--muted)', strokeWidth: 1 }} />
          <Line
            type="linear"
            dataKey="average"
            stroke="var(--brand)"
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
            dot={{ r: 4, fill: 'var(--brand)', stroke: 'var(--surface)', strokeWidth: 2 }}
            activeDot={{ r: 6, fill: 'var(--brand)', stroke: 'var(--surface)', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
