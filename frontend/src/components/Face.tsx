// La cara (forma de la boca) y la etiqueta identifican cada valor; el color acompaña, nunca es la única señal.
import { RATING_LABELS } from '../lib/rating'

const MOUTHS = [
  'M13 29 Q20 21 27 29', // 1: tristeza marcada
  'M14 28 Q20 24.5 26 28', // 2
  'M14 27 L26 27', // 3: neutra
  'M14 25.5 Q20 29.5 26 25.5', // 4
  'M12.5 24 Q20 33 27.5 24', // 5: sonrisa amplia
]
const FILLS = ['bg-face-1', 'bg-face-2', 'bg-face-3', 'bg-face-4', 'bg-face-5']

type FaceProps = { rating: number; size?: number; className?: string; title?: string }

/** Cara para un valor 1–5; con un promedio, muestra la cara más cercana. */
export function Face({ rating, size = 32, className = '', title }: FaceProps) {
  const index = Math.min(4, Math.max(0, Math.round(rating) - 1))
  return (
    <span
      className={`inline-grid shrink-0 place-items-center rounded-full ${FILLS[index]} ${className}`}
      style={{ width: size, height: size }}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      <svg viewBox="0 0 40 40" width={size} height={size} fill="none">
        <circle cx="14.5" cy="16" r="2.4" fill="#1b2541" />
        <circle cx="25.5" cy="16" r="2.4" fill="#1b2541" />
        <path d={MOUTHS[index]} stroke="#1b2541" strokeWidth="2.6" strokeLinecap="round" />
      </svg>
    </span>
  )
}

type PickerProps = { value: number | null; onChange: (rating: number) => void; disabled?: boolean }

export function RatingPicker({ value, onChange, disabled = false }: PickerProps) {
  return (
    <fieldset disabled={disabled} className="disabled:opacity-60">
      <legend className="mb-2 text-sm font-medium">¿Cómo estuvo la clase?</legend>
      <div className="grid grid-cols-5 gap-1.5">
        {RATING_LABELS.map((label, i) => {
          const rating = i + 1
          const selected = value === rating
          return (
            <label
              key={rating}
              className={`flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border px-1 py-2.5 transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-brand ${
                selected ? 'border-brand bg-brand-soft' : 'border-line hover:bg-subtle'
              }`}
            >
              <input
                type="radio"
                name="rating"
                value={rating}
                checked={selected}
                onChange={() => onChange(rating)}
                className="sr-only"
              />
              <Face
                rating={rating}
                size={40}
                className={`transition-opacity ${value !== null && !selected ? 'opacity-40' : ''}`}
              />
              <span className={`text-center text-xs leading-tight ${selected ? 'font-medium text-ink' : 'text-muted'}`}>
                {label}
              </span>
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}
