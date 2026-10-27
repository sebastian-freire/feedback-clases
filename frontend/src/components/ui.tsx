import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react'
import { Link } from 'react-router'
import type { WindowState } from '../api/types'

// Lista con divisores finos: de borde a borde en el celular, con marco desde tablet.
export const LIST_CLASS = '-mx-4 divide-y divide-line border-y border-line sm:mx-0 sm:rounded-lg sm:border'
// Fila clickeable dentro de LIST_CLASS.
export const ROW_LINK_CLASS = 'flex items-center gap-3 px-4 py-3.5 transition-colors hover:bg-subtle'

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'quiet'

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  primary: 'bg-brand text-on-brand hover:opacity-90',
  secondary: 'border border-line bg-surface text-ink hover:bg-subtle',
  danger: 'border border-line bg-surface text-danger hover:bg-danger-soft',
  quiet: 'text-brand hover:underline underline-offset-4',
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 text-[0.9375rem] font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_STYLES[variant]} ${className}`}
      {...props}
    />
  )
}

type FieldProps = { label: string; hint?: ReactNode; id: string }

const INPUT_CLASS =
  'min-h-11 rounded-lg border border-line bg-surface px-3 text-base outline-none transition-colors placeholder:text-muted focus:border-brand focus:ring-3 focus:ring-brand/15 focus-visible:outline-none'

export function TextField({ label, hint, id, className, ...props }: FieldProps & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <input id={id} className={`${INPUT_CLASS} ${className ?? ''}`} {...props} />
      {hint && <p className="text-sm text-muted">{hint}</p>}
    </div>
  )
}

export function TextArea({
  label,
  id,
  value,
  maxLength,
  ...props
}: FieldProps & TextareaHTMLAttributes<HTMLTextAreaElement> & { value: string; maxLength: number }) {
  const remaining = maxLength - value.length
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor={id} className="text-sm font-medium">
          {label}
        </label>
        <span className={`text-xs tabular-nums ${remaining < 50 ? 'text-danger' : 'text-muted'}`}>
          {remaining} caracteres
        </span>
      </div>
      <textarea id={id} value={value} maxLength={maxLength} rows={3} className={`${INPUT_CLASS} py-2.5`} {...props} />
    </div>
  )
}

export function Alert({ kind = 'error', children }: { kind?: 'error' | 'success' | 'info'; children: ReactNode }) {
  const styles = {
    error: 'border-danger/30 bg-danger-soft',
    success: 'border-success/30 bg-success-soft',
    info: 'border-line bg-subtle',
  }[kind]
  return (
    <div role={kind === 'error' ? 'alert' : 'status'} className={`rounded-lg border px-4 py-3 text-sm ${styles}`}>
      {children}
    </div>
  )
}

export function Loading({ label = 'Cargando…' }: { label?: string }) {
  return (
    <p className="py-10 text-center text-sm text-muted" role="status">
      {label}
    </p>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-line px-5 py-8 text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="mt-1 text-sm text-muted">{children}</div>}
    </div>
  )
}

export function PageHeader({ title, back, children }: { title: string; back?: { to: string; label: string }; children?: ReactNode }) {
  return (
    <header className="mb-6">
      {back && (
        <Link to={back.to} className="mb-2 inline-flex min-h-9 items-center gap-1 text-sm font-medium text-brand hover:underline">
          <span aria-hidden>‹</span> {back.label}
        </Link>
      )}
      <h1 className="text-2xl font-semibold tracking-tight text-balance">{title}</h1>
      {children && <div className="mt-1 text-sm text-muted">{children}</div>}
    </header>
  )
}

/** Título de sección dentro de una página. */
export function SectionTitle({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="mb-3">
      <h2 className="text-base font-semibold">{children}</h2>
      {hint && <p className="mt-0.5 text-sm text-muted">{hint}</p>}
    </div>
  )
}

const WINDOW_LABEL: Record<WindowState, string> = {
  upcoming: 'Próxima',
  open: 'Abierta',
  closed: 'Cerrada',
}

export function WindowBadge({ state }: { state: WindowState }) {
  const styles = state === 'open' ? 'bg-brand-soft text-brand' : 'bg-subtle text-muted'
  return <span className={`rounded-md px-2 py-0.5 text-xs font-medium ${styles}`}>{WINDOW_LABEL[state]}</span>
}
