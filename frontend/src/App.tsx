import { lazy, Suspense, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import type { Role } from './api/types'
import { AuthProvider } from './auth/AuthContext'
import { useAuth } from './auth/useAuth'
import { Layout } from './components/Layout'
import { Loading, PageHeader } from './components/ui'
import { AdminSubjectPage, AdminSubjectsPage, AdminUsersPage } from './pages/admin/AdminPages'
import { ROLE_HOME } from './lib/roles'
import { LoginPage, RegisterPage } from './pages/AuthPages'
import { FeedbackPage, StudentClassesPage, StudentSubjectsPage } from './pages/student/StudentPages'
import { TeacherComparisonPage } from './pages/teacher/TeacherComparisonPage'
import { TeacherClassPage, TeacherSubjectsPage } from './pages/teacher/TeacherPages'

// El gráfico (Recharts) es pesado: se descarga solo cuando el docente abre una materia.
const TeacherSubjectPage = lazy(() =>
  import('./pages/teacher/TeacherSubjectPage').then((m) => ({ default: m.TeacherSubjectPage })),
)

/** Solo deja pasar si hay sesión y el usuario tiene el rol. El backend vuelve a verificarlo todo. */
function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (!user.roles.includes(role)) return <Navigate to="/" replace />
  return <Suspense fallback={<Loading />}>{children}</Suspense>
}

function Home() {
  const { activeRole } = useAuth()
  if (!activeRole) return <PageHeader title="Tu cuenta no tiene roles asignados">Pedile a la administración que te asigne uno.</PageHeader>
  return <Navigate to={ROLE_HOME[activeRole]} replace />
}

function AppRoutes() {
  const { user, loading } = useAuth()
  if (loading) return <Loading />

  if (!user) {
    return (
      <Routes>
        <Route path="/registro" element={<RegisterPage />} />
        <Route path="*" element={<LoginPage />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="alumno" element={<RequireRole role="student"><StudentSubjectsPage /></RequireRole>} />
        <Route path="alumno/materias/:subjectId" element={<RequireRole role="student"><StudentClassesPage /></RequireRole>} />
        <Route path="alumno/clases/:classId" element={<RequireRole role="student"><FeedbackPage /></RequireRole>} />
        <Route path="docente" element={<RequireRole role="teacher"><TeacherSubjectsPage /></RequireRole>} />
        <Route path="docente/materias/:subjectId" element={<RequireRole role="teacher"><TeacherSubjectPage /></RequireRole>} />
        <Route path="docente/comparar" element={<RequireRole role="teacher"><TeacherComparisonPage /></RequireRole>} />
        <Route path="docente/clases/:classId" element={<RequireRole role="teacher"><TeacherClassPage /></RequireRole>} />
        <Route path="admin" element={<RequireRole role="admin"><AdminSubjectsPage /></RequireRole>} />
        <Route path="admin/materias/:subjectId" element={<RequireRole role="admin"><AdminSubjectPage /></RequireRole>} />
        <Route path="admin/usuarios" element={<RequireRole role="admin"><AdminUsersPage /></RequireRole>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
