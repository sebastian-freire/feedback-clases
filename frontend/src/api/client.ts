import { API_URL } from './config'

const TOKEN_KEY = 'feedback.token'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export const tokenStore = {
  get: (): string | null => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

// La capa de autenticación se suscribe para cerrar la sesión cuando la API responde 401.
let onUnauthorized: () => void = () => {}
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

type ValidationIssue = { loc: (string | number)[]; msg: string }

const FIELD_NAMES: Record<string, string> = {
  email: 'Email',
  password: 'Contraseña',
  full_name: 'Nombre',
  rating: 'Calificación',
  liked: 'Qué te gustó',
  disliked: 'Qué no te gustó',
  name: 'Nombre',
}

function messageFrom(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const issue = detail[0] as ValidationIssue
    const field = String(issue.loc.at(-1) ?? '')
    const message = issue.msg.replace(/^Value error, /, '')
    return `${FIELD_NAMES[field] ?? field}: ${message}`
  }
  if (status >= 500) return 'El servidor tuvo un problema. Probá de nuevo en un momento.'
  return `Error inesperado (${status}).`
}

export async function api<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const token = tokenStore.get()
  let response: Response
  try {
    response = await fetch(`${API_URL}/api${path}`, {
      method: options.method ?? 'GET',
      headers: {
        ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'No hay conexión con el servidor. Revisá tu conexión e intentá de nuevo.')
  }

  if (response.status === 204) return undefined as T
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401 && token) onUnauthorized()
    throw new ApiError(response.status, messageFrom(response.status, body))
  }
  return body as T
}

/** Descarga un archivo autenticado (el navegador no manda el token en un <a href> común). */
export async function apiDownload(path: string, fallbackName: string): Promise<void> {
  const token = tokenStore.get()
  const response = await fetch(`${API_URL}/api${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }).catch(() => {
    throw new ApiError(0, 'No hay conexión con el servidor. Revisá tu conexión e intentá de nuevo.')
  })
  if (!response.ok) {
    if (response.status === 401 && token) onUnauthorized()
    throw new ApiError(response.status, messageFrom(response.status, await response.json().catch(() => null)))
  }
  const name = /filename="([^"]+)"/.exec(response.headers.get('Content-Disposition') ?? '')?.[1] ?? fallbackName
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  URL.revokeObjectURL(url)
}
