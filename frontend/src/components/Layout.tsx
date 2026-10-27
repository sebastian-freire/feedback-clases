import { Link, Outlet, useNavigate } from 'react-router'
import type { Role } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { ROLE_HOME, ROLE_LABELS } from '../lib/roles'

export function Layout() {
  const { user, activeRole, setActiveRole, logout } = useAuth()
  const navigate = useNavigate()
  if (!user || !activeRole) return null

  const switchRole = (role: Role) => {
    setActiveRole(role)
    navigate(ROLE_HOME[role])
  }

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 border-b border-line bg-surface">
        <div className="mx-auto flex h-14 max-w-2xl items-center justify-between gap-3 px-4">
          <Link to={ROLE_HOME[activeRole]} className="shrink-0 text-[0.9375rem] font-semibold tracking-tight">
            Feedback de clases
          </Link>
          <div className="flex min-w-0 items-center gap-1">
            <span className="truncate text-sm text-muted">{user.full_name}</span>
            <button onClick={logout} className="min-h-9 shrink-0 rounded-md px-2.5 text-sm font-medium text-brand hover:bg-subtle">
              Salir
            </button>
          </div>
        </div>
        {user.roles.length > 1 && (
          <nav aria-label="Cambiar de rol" className="mx-auto flex max-w-2xl gap-6 px-4">
            {user.roles.map((role) => (
              <button
                key={role}
                onClick={() => switchRole(role)}
                aria-pressed={role === activeRole}
                className={`-mb-px min-h-10 border-b-2 text-sm font-medium ${
                  role === activeRole ? 'border-brand text-ink' : 'border-transparent text-muted hover:text-ink'
                }`}
              >
                {ROLE_LABELS[role]}
              </button>
            ))}
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-2xl px-4 pt-6 pb-16">
        <Outlet />
      </main>
    </div>
  )
}
