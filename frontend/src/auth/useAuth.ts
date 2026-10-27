import { createContext, useContext } from 'react'
import type { Role, User } from '../api/types'

export type AuthState = {
  user: User | null
  activeRole: Role | null
  loading: boolean
  sessionExpired: boolean
  login: (email: string, password: string) => Promise<void>
  register: (fullName: string, email: string, password: string) => Promise<void>
  logout: () => void
  setActiveRole: (role: Role) => void
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return context
}
