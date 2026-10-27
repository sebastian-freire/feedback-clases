import { useState, type FormEvent } from 'react'
import { Link, NavLink, useParams } from 'react-router'
import { api, ApiError } from '../../api/client'
import type { AdminSubject, AdminSubjectDetail, Role, ScheduleRule, User } from '../../api/types'
import { Alert, Button, EmptyState, LIST_CLASS, Loading, PageHeader, ROW_LINK_CLASS, TextField } from '../../components/ui'
import { dayNumber, groupByMonth, timeShort, weekdayShort } from '../../lib/format'
import { ROLE_LABELS } from '../../lib/roles'
import { useApi } from '../../lib/useApi'

const WEEKDAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
const ALL_ROLES: Role[] = ['student', 'teacher', 'admin']

const errorText = (err: unknown) => (err instanceof ApiError ? err.message : 'Error inesperado.')

function AdminTabs() {
  const tab = ({ isActive }: { isActive: boolean }) =>
    `-mb-px flex min-h-10 items-center border-b-2 text-sm font-medium ${
      isActive ? 'border-brand text-ink' : 'border-transparent text-muted hover:text-ink'
    }`
  return (
    <nav aria-label="Secciones de administración" className="mb-6 flex gap-6 border-b border-line">
      <NavLink to="/admin" end className={tab}>
        Materias
      </NavLink>
      <NavLink to="/admin/usuarios" className={tab}>
        Usuarios
      </NavLink>
    </nav>
  )
}

function TeacherChecklist({
  teachers,
  selected,
  onChange,
  legend = true,
}: {
  teachers: User[]
  selected: number[]
  onChange: (ids: number[]) => void
  legend?: boolean
}) {
  if (teachers.length === 0) {
    return <p className="text-muted">No hay usuarios con rol docente. Creá uno en Usuarios.</p>
  }
  return (
    <fieldset className="flex flex-col">
      <legend className={legend ? 'mb-1 text-sm font-medium' : 'sr-only'}>Docentes</legend>
      {teachers.map((t) => (
        <label key={t.id} className="flex min-h-11 cursor-pointer items-center gap-3">
          <input
            type="checkbox"
            className="size-5 accent-[var(--brand)]"
            checked={selected.includes(t.id)}
            onChange={(e) => onChange(e.target.checked ? [...selected, t.id] : selected.filter((id) => id !== t.id))}
          />
          <span className="text-[0.9375rem]">
            {t.full_name} <span className="text-sm text-muted">{t.email}</span>
          </span>
        </label>
      ))}
    </fieldset>
  )
}

// --- Materias ---

function CreateSubjectForm({ onCreated }: { onCreated: () => void }) {
  const teachers = useApi<User[]>('/admin/users?role=teacher')
  const [name, setName] = useState('')
  const [teacherIds, setTeacherIds] = useState<number[]>([])
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSending(true)
    setError(null)
    try {
      await api<AdminSubject>('/admin/subjects', { method: 'POST', body: { name, teacher_ids: teacherIds } })
      setName('')
      setTeacherIds([])
      onCreated()
    } catch (err) {
      setError(errorText(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <form onSubmit={submit} className="mt-10 flex flex-col gap-4 border-t border-line pt-6">
      <h2 className="text-base font-semibold">Nueva materia</h2>
      <TextField id="subject-name" label="Nombre" required minLength={2} maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
      {teachers.data && <TeacherChecklist teachers={teachers.data} selected={teacherIds} onChange={setTeacherIds} />}
      {error && <Alert>{error}</Alert>}
      <Button type="submit" disabled={sending}>
        {sending ? 'Creando…' : 'Crear materia'}
      </Button>
      <p className="-mt-2 text-sm text-muted">El código de inscripción se genera solo.</p>
    </form>
  )
}

export function AdminSubjectsPage() {
  const { data, error, loading, reload } = useApi<AdminSubject[]>('/admin/subjects')

  return (
    <>
      <AdminTabs />
      <PageHeader title="Materias" />
      {error && <Alert>{error.message}</Alert>}
      {loading && !data && <Loading />}
      {data?.length === 0 && <EmptyState title="Todavía no hay materias">Creá la primera con el formulario de abajo.</EmptyState>}
      {data && data.length > 0 && (
        <ul className={LIST_CLASS}>
          {data.map((s) => (
            <li key={s.id}>
              <Link to={`/admin/materias/${s.id}`} className={ROW_LINK_CLASS}>
                <span className="min-w-0 flex-1">
                  <span className="block font-medium">{s.name}</span>
                  <span className="block text-sm text-muted">
                    {s.teachers.length > 0 ? s.teachers.map((t) => t.full_name).join(', ') : 'Sin docentes'}
                  </span>
                  <span className="text-sm text-muted">
                    {s.class_count} clases, {s.student_count} alumnos, código <span className="font-mono text-ink">{s.enrollment_code}</span>
                  </span>
                </span>
                <span aria-hidden className="text-xl text-muted">
                  ›
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <CreateSubjectForm onCreated={reload} />
    </>
  )
}

// --- Detalle de materia ---

function TeachersEditor({ subject, onSaved }: { subject: AdminSubjectDetail; onSaved: () => void }) {
  const teachers = useApi<User[]>('/admin/users?role=teacher')
  const [selected, setSelected] = useState(subject.teachers.map((t) => t.id))
  const [message, setMessage] = useState<{ kind: 'error' | 'success'; text: string } | null>(null)

  const save = async () => {
    setMessage(null)
    try {
      await api(`/admin/subjects/${subject.id}/teachers`, { method: 'PUT', body: { teacher_ids: selected } })
      setMessage({ kind: 'success', text: 'Docentes actualizados.' })
      onSaved()
    } catch (err) {
      setMessage({ kind: 'error', text: errorText(err) })
    }
  }

  return (
    <section className="mb-10 flex flex-col gap-3">
      {teachers.data && <TeacherChecklist teachers={teachers.data} selected={selected} onChange={setSelected} legend={false} />}
      {message && <Alert kind={message.kind}>{message.text}</Alert>}
      <Button variant="secondary" onClick={save}>
        Guardar docentes
      </Button>
    </section>
  )
}

function ScheduleGenerator({ subjectId, onGenerated }: { subjectId: number; onGenerated: () => void }) {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [rules, setRules] = useState<ScheduleRule[]>([{ weekday: 0, start_time: '08:00' }])
  const [message, setMessage] = useState<{ kind: 'error' | 'success'; text: string } | null>(null)
  const [sending, setSending] = useState(false)

  const updateRule = (index: number, change: Partial<ScheduleRule>) =>
    setRules(rules.map((rule, i) => (i === index ? { ...rule, ...change } : rule)))

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSending(true)
    setMessage(null)
    try {
      const result = await api<{ created: number; skipped: number }>(`/admin/subjects/${subjectId}/classes/generate`, {
        method: 'POST',
        body: { start_date: startDate, end_date: endDate, rules },
      })
      const skipped = result.skipped > 0 ? ` (${result.skipped} ya existían)` : ''
      setMessage({ kind: 'success', text: `Se crearon ${result.created} clases${skipped}.` })
      onGenerated()
    } catch (err) {
      setMessage({ kind: 'error', text: errorText(err) })
    } finally {
      setSending(false)
    }
  }

  return (
    <form onSubmit={submit} className="mb-10 flex flex-col gap-4">
      <p className="text-muted">Elegí el período y los días y horarios en que se dicta. Las fechas que ya tienen clase no se duplican.</p>
      <div className="grid grid-cols-2 gap-3">
        <TextField id="start" label="Desde" type="date" required value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        <TextField id="end" label="Hasta" type="date" required value={endDate} onChange={(e) => setEndDate(e.target.value)} />
      </div>
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-medium">Días y horarios</legend>
        {rules.map((rule, i) => (
          <div key={i} className="flex items-center gap-2">
            <select
              aria-label={`Día del horario ${i + 1}`}
              className="min-h-11 flex-1 rounded-lg border border-line bg-surface px-3 text-base"
              value={rule.weekday}
              onChange={(e) => updateRule(i, { weekday: Number(e.target.value) })}
            >
              {WEEKDAYS.map((day, value) => (
                <option key={day} value={value}>
                  {day}
                </option>
              ))}
            </select>
            <input
              type="time"
              aria-label={`Hora del horario ${i + 1}`}
              required
              className="min-h-11 rounded-lg border border-line bg-surface px-3 text-base"
              value={rule.start_time}
              onChange={(e) => updateRule(i, { start_time: e.target.value })}
            />
            <button
              type="button"
              aria-label={`Quitar horario ${i + 1}`}
              disabled={rules.length === 1}
              onClick={() => setRules(rules.filter((_, j) => j !== i))}
              className="grid size-11 place-items-center rounded-lg text-xl text-muted hover:bg-subtle disabled:opacity-30"
            >
              ×
            </button>
          </div>
        ))}
        <Button type="button" variant="quiet" className="self-start px-0" onClick={() => setRules([...rules, { weekday: 0, start_time: '08:00' }])}>
          + Agregar horario
        </Button>
      </fieldset>
      {message && <Alert kind={message.kind}>{message.text}</Alert>}
      <Button type="submit" disabled={sending}>
        {sending ? 'Generando…' : 'Generar clases'}
      </Button>
    </form>
  )
}

export function AdminSubjectPage() {
  const subjectId = Number(useParams().subjectId)
  const { data, error, loading, reload } = useApi<AdminSubjectDetail>(`/admin/subjects/${subjectId}`)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const back = { to: '/admin', label: 'Materias' }

  if (error) {
    return (
      <>
        <PageHeader title="Materia" back={back} />
        <Alert>{error.message}</Alert>
      </>
    )
  }
  if (loading && !data) return <Loading />
  if (!data) return null

  const remove = async (classId: number, label: string) => {
    if (!window.confirm(`¿Eliminar la clase del ${label}?`)) return
    setDeleteError(null)
    try {
      await api(`/admin/classes/${classId}`, { method: 'DELETE' })
      reload()
    } catch (err) {
      setDeleteError(errorText(err))
    }
  }

  return (
    <>
      <PageHeader title={data.name} back={back}>
        Código de inscripción <span className="font-mono font-medium text-ink">{data.enrollment_code}</span>, {data.student_count} alumnos
        inscriptos
      </PageHeader>

      <h2 className="mb-3 text-base font-semibold">Docentes</h2>
      <TeachersEditor key={data.teachers.map((t) => t.id).join(',')} subject={data} onSaved={reload} />

      <h2 className="mb-3 text-base font-semibold">Generar clases</h2>
      <ScheduleGenerator subjectId={data.id} onGenerated={reload} />

      <h2 className="mb-3 text-base font-semibold">Clases ({data.classes.length})</h2>
      {deleteError && (
        <div className="mb-3">
          <Alert>{deleteError}</Alert>
        </div>
      )}
      {data.classes.length === 0 && <EmptyState title="Sin clases todavía">Generalas con el formulario de arriba.</EmptyState>}
      {groupByMonth(data.classes).map((group) => (
        <section key={group.month} className="mb-5">
          <h3 className="mb-2 font-semibold text-muted">{group.month}</h3>
          <ul className={LIST_CLASS}>
            {group.items.map((c) => {
              const label = `${weekdayShort(c.date).toLowerCase()} ${dayNumber(c.date)}, ${timeShort(c.start_time)} h`
              return (
                <li key={c.id} className="flex min-h-14 items-center justify-between gap-3 px-4 py-1.5">
                  <span>
                    {weekdayShort(c.date)} {dayNumber(c.date)}, {timeShort(c.start_time)} h
                  </span>
                  {c.can_delete ? (
                    <button onClick={() => remove(c.id, label)} className="min-h-11 rounded-lg px-3 text-danger hover:bg-danger-soft">
                      Eliminar
                    </button>
                  ) : (
                    <span className="text-sm text-muted">Tiene feedback</span>
                  )}
                </li>
              )
            })}
          </ul>
        </section>
      ))}
    </>
  )
}

// --- Usuarios ---

function RoleChecks({ value, onChange, idPrefix }: { value: Role[]; onChange: (roles: Role[]) => void; idPrefix: string }) {
  return (
    <div className="flex flex-wrap gap-x-5">
      {ALL_ROLES.map((role) => (
        <label key={role} htmlFor={`${idPrefix}-${role}`} className="flex min-h-11 cursor-pointer items-center gap-2">
          <input
            id={`${idPrefix}-${role}`}
            type="checkbox"
            className="size-5 accent-[var(--brand)]"
            checked={value.includes(role)}
            onChange={(e) => onChange(e.target.checked ? [...value, role] : value.filter((r) => r !== role))}
          />
          {ROLE_LABELS[role]}
        </label>
      ))}
    </div>
  )
}

function UserRow({ user, onSaved }: { user: User; onSaved: () => void }) {
  const [editing, setEditing] = useState(false)
  const [roles, setRoles] = useState<Role[]>(user.roles)
  const [error, setError] = useState<string | null>(null)

  const save = async () => {
    setError(null)
    try {
      await api(`/admin/users/${user.id}/roles`, { method: 'PUT', body: { roles } })
      setEditing(false)
      onSaved()
    } catch (err) {
      setError(errorText(err))
    }
  }

  return (
    <li className="px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <span className="min-w-0">
          <span className="block font-semibold">{user.full_name}</span>
          <span className="block truncate text-sm text-muted">{user.email}</span>
          {!editing && <span className="text-sm">{user.roles.map((r) => ROLE_LABELS[r]).join(', ')}</span>}
        </span>
        {!editing && (
          <button onClick={() => setEditing(true)} className="min-h-11 shrink-0 rounded-lg px-3 text-brand hover:bg-subtle">
            Editar roles
          </button>
        )}
      </div>
      {editing && (
        <div className="mt-2 flex flex-col gap-2">
          <RoleChecks value={roles} onChange={setRoles} idPrefix={`user-${user.id}`} />
          {error && <Alert>{error}</Alert>}
          <div className="flex gap-2">
            <Button onClick={save} disabled={roles.length === 0}>
              Guardar
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setRoles(user.roles)
                setEditing(false)
                setError(null)
              }}
            >
              Cancelar
            </Button>
          </div>
        </div>
      )}
    </li>
  )
}

function CreateUserForm({ onCreated }: { onCreated: () => void }) {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [roles, setRoles] = useState<Role[]>(['teacher'])
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSending(true)
    setError(null)
    try {
      await api('/admin/users', { method: 'POST', body: { full_name: fullName, email, password, roles } })
      setFullName('')
      setEmail('')
      setPassword('')
      onCreated()
    } catch (err) {
      setError(errorText(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <form onSubmit={submit} className="mt-10 flex flex-col gap-4 border-t border-line pt-6">
      <h2 className="text-base font-semibold">Nuevo usuario</h2>
      <TextField id="new-name" label="Nombre y apellido" required minLength={2} value={fullName} onChange={(e) => setFullName(e.target.value)} />
      <TextField id="new-email" label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      <TextField
        id="new-password"
        label="Contraseña inicial"
        type="password"
        autoComplete="new-password"
        required
        minLength={8}
        hint="Mínimo 8 caracteres. Compartila con la persona por un canal privado."
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <fieldset>
        <legend className="font-semibold">Roles</legend>
        <RoleChecks value={roles} onChange={setRoles} idPrefix="new" />
      </fieldset>
      {error && <Alert>{error}</Alert>}
      <Button type="submit" disabled={sending || roles.length === 0}>
        {sending ? 'Creando…' : 'Crear usuario'}
      </Button>
    </form>
  )
}

export function AdminUsersPage() {
  const { data, error, loading, reload } = useApi<User[]>('/admin/users')

  return (
    <>
      <AdminTabs />
      <PageHeader title="Usuarios">Los alumnos se registran solos. Acá se crean docentes y administradores.</PageHeader>
      {error && <Alert>{error.message}</Alert>}
      {loading && !data && <Loading />}
      {data && (
        <ul className={LIST_CLASS}>
          {data.map((user) => (
            <UserRow key={`${user.id}-${user.roles.join()}`} user={user} onSaved={reload} />
          ))}
        </ul>
      )}
      <CreateUserForm onCreated={reload} />
    </>
  )
}
