import type { Role } from '../api/types'

export const ROLE_LABELS: Record<Role, string> = { student: 'Alumno', teacher: 'Docente', admin: 'Admin' }
export const ROLE_HOME: Record<Role, string> = { student: '/alumno', teacher: '/docente', admin: '/admin' }
