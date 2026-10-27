import { useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'
import { Alert, Button, TextField } from '../components/ui'

function AuthFrame({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center px-4 py-10">
      <div className="mb-8">
        <p className="mb-6 text-sm font-semibold tracking-tight text-brand">Feedback de clases</p>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-1.5 text-sm text-muted">Contá qué te pareció cada clase. Tu docente lo lee sin tu nombre.</p>
      </div>
      {children}
    </main>
  )
}

function useSubmit(action: () => Promise<void>) {
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setSending(true)
    try {
      await action()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error inesperado.')
      setSending(false)
    }
  }
  return { error, sending, onSubmit }
}

export function LoginPage() {
  const { login, sessionExpired } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { error, sending, onSubmit } = useSubmit(() => login(email, password))

  return (
    <AuthFrame title="Iniciar sesión">
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        {sessionExpired && !error && <Alert kind="info">Tu sesión venció. Iniciá sesión de nuevo.</Alert>}
        {error && <Alert>{error}</Alert>}
        <TextField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <TextField
          id="password"
          label="Contraseña"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" disabled={sending} className="mt-2">
          {sending ? 'Ingresando…' : 'Ingresar'}
        </Button>
      </form>
      <p className="mt-6 text-center text-muted">
        ¿Sos alumno y no tenés cuenta?{' '}
        <Link to="/registro" className="font-semibold text-brand hover:underline">
          Creá una
        </Link>
      </p>
    </AuthFrame>
  )
}

export function RegisterPage() {
  const { register } = useAuth()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { error, sending, onSubmit } = useSubmit(() => register(fullName, email, password))

  return (
    <AuthFrame title="Crear cuenta de alumno">
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        {error && <Alert>{error}</Alert>}
        <TextField
          id="full_name"
          label="Nombre y apellido"
          autoComplete="name"
          required
          minLength={2}
          maxLength={120}
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
        <TextField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <TextField
          id="password"
          label="Contraseña"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          maxLength={128}
          hint="Mínimo 8 caracteres."
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" disabled={sending} className="mt-2">
          {sending ? 'Creando cuenta…' : 'Crear cuenta'}
        </Button>
      </form>
      <p className="mt-6 text-center text-muted">
        ¿Ya tenés cuenta?{' '}
        <Link to="/login" className="font-semibold text-brand hover:underline">
          Ingresá
        </Link>
      </p>
    </AuthFrame>
  )
}
