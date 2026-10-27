import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'

type ApiState<T> = { data: T | null; error: ApiError | null; loading: boolean; reload: () => void }
type Result<T> = { key: string; data: T | null; error: ApiError | null }

/** GET con estados de carga y error. Al recargar mantiene los datos previos (sin parpadeo). */
export function useApi<T>(path: string): ApiState<T> {
  const [version, setVersion] = useState(0)
  const [result, setResult] = useState<Result<T>>({ key: '', data: null, error: null })
  const key = `${path}#${version}`

  useEffect(() => {
    let cancelled = false
    api<T>(path)
      .then((data) => !cancelled && setResult({ key, data, error: null }))
      .catch((err: unknown) => {
        const error = err instanceof ApiError ? err : new ApiError(0, 'Error inesperado.')
        if (!cancelled) setResult((prev) => ({ key, data: prev.data, error }))
      })
    return () => {
      cancelled = true
    }
  }, [path, key])

  const reload = useCallback(() => setVersion((v) => v + 1), [])
  return { data: result.data, error: result.error, loading: result.key !== key, reload }
}
