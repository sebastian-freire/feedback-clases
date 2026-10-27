import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, setUnauthorizedHandler, tokenStore } from '../api/client'
import type { Role, TokenResponse, User } from '../api/types'
import { AuthContext, type AuthState } from './useAuth'

const ACTIVE_ROLE_KEY = 'feedback.activeRole'
// Rol con el que se entra si el usuario tiene varios (D-028).
const ROLE_PRIORITY: Role[] = ['student', 'teacher', 'admin']


function pickRole(user: User): Role | null {
  const stored = localStorage.getItem(ACTIVE_ROLE_KEY) as Role | null
  if (stored && user.roles.includes(stored)) return stored
  return ROLE_PRIORITY.find((role) => user.roles.includes(role)) ?? null
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [activeRole, setActiveRoleState] = useState<Role | null>(null)
  const [loading, setLoading] = useState(() => tokenStore.get() !== null)
  const [sessionExpired, setSessionExpired] = useState(false)

  const startSession = useCallback((data: TokenResponse) => {
    tokenStore.set(data.access_token)
    setUser(data.user)
    setActiveRoleState(pickRole(data.user))
    setSessionExpired(false)
  }, [])

  const logout = useCallback(() => {
    tokenStore.clear()
    localStorage.removeItem(ACTIVE_ROLE_KEY)
    setUser(null)
    setActiveRoleState(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      logout()
      setSessionExpired(true)
    })
    if (!tokenStore.get()) return
    api<User>('/auth/me')
      .then((me) => {
        setUser(me)
        setActiveRoleState(pickRole(me))
      })
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false))
  }, [logout])

  const value = useMemo<AuthState>(
    () => ({
      user,
      activeRole,
      loading,
      sessionExpired,
      logout,
      login: async (email, password) => {
        startSession(await api<TokenResponse>('/auth/login', { method: 'POST', body: { email, password } }))
      },
      register: async (fullName, email, password) => {
        startSession(
          await api<TokenResponse>('/auth/register', {
            method: 'POST',
            body: { full_name: fullName, email, password },
          }),
        )
      },
      setActiveRole: (role) => {
        localStorage.setItem(ACTIVE_ROLE_KEY, role)
        setActiveRoleState(role)
      },
    }),
    [user, activeRole, loading, sessionExpired, logout, startSession],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
