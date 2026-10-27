// Barras horizontales simples (una sola serie, un solo color): valor al final de la fila,
// texto siempre en colores de texto, nunca en el color de la barra.

type Bar = { label: string; value: number; display: string }

export function BarList({ bars, max, label }: { bars: Bar[]; max: number; label: string }) {
  return (
    <ul aria-label={label} className="flex flex-col gap-2.5">
      {bars.map((bar) => (
        <li key={bar.label} className="grid grid-cols-[minmax(0,8.5rem)_1fr_2.75rem] items-center gap-3">
          <span className="text-sm leading-tight break-words">
            {bar.label}
          </span>
          <span className="h-3.5">
            <span
              className="block h-full rounded-r-[4px] bg-brand"
              style={{ width: `${Math.max(2, (bar.value / max) * 100)}%` }}
            />
          </span>
          <span className="text-right text-sm font-semibold tabular-nums">{bar.display}</span>
        </li>
      ))}
    </ul>
  )
}
