import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router'
import type { ClassComments, TeacherSubject } from '../../api/types'
import { Face } from '../../components/Face'
import { Alert, EmptyState, LIST_CLASS, Loading, PageHeader, ROW_LINK_CLASS } from '../../components/ui'
import { dateLong, formatAverage, plural, timeShort } from '../../lib/format'
import { ratingLabel } from '../../lib/rating'
import { useApi } from '../../lib/useApi'

export function EnrollmentCode({ code }: { code: string }) {
  return (
    <span className="mt-2 inline-flex items-center gap-2">
      Código de inscripción
      <span className="rounded-md bg-subtle px-2 py-0.5 font-mono text-sm font-medium tracking-wider text-ink">{code}</span>
    </span>
  )
}

/** Resumen numérico: valor grande, cara de referencia y una línea de contexto. */
export function AverageSummary({ average, children }: { average: number | null; children: ReactNode }) {
  return (
    <section className="mb-8 flex items-center gap-4 border-y border-line py-5">
      {average !== null && <Face rating={average} size={44} />}
      <div>
        <p className="text-3xl leading-none font-semibold tracking-tight">{formatAverage(average)}</p>
        <p className="mt-1.5 text-sm text-muted">{children}</p>
      </div>
    </section>
  )
}

// --- Mis materias ---

export function TeacherSubjectsPage() {
  const { data, error, loading } = useApi<TeacherSubject[]>('/teacher/subjects')

  return (
    <>
      <PageHeader title="Mis materias" />
      {error && <Alert>{error.message}</Alert>}
      {loading && !data && <Loading />}
      {data?.length === 0 && (
        <EmptyState title="No tenés materias asignadas">Pedile a la administración que te asigne una.</EmptyState>
      )}
      {data && data.length > 0 && (
        <ul className={LIST_CLASS}>
          {data.map((subject) => (
            <li key={subject.id}>
              <Link to={`/docente/materias/${subject.id}`} className={ROW_LINK_CLASS}>
                <span className="min-w-0 flex-1">
                  <span className="block font-medium">{subject.name}</span>
                  <span className="text-sm text-muted">
                    {subject.average !== null
                      ? plural(subject.response_count, 'respuesta', 'respuestas')
                      : 'Sin respuestas todavía'}
                  </span>
                </span>
                {subject.average !== null && (
                  <span className="flex items-center gap-2">
                    <span className="text-lg font-semibold tabular-nums">{formatAverage(subject.average)}</span>
                    <Face rating={subject.average} size={24} />
                  </span>
                )}
                <span aria-hidden className="text-xl text-muted">
                  ›
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {data && data.length >= 2 && (
        <Link
          to="/docente/comparar"
          className="mt-4 inline-flex min-h-10 items-center text-sm font-medium text-brand hover:underline"
        >
          Comparar mis materias ›
        </Link>
      )}
    </>
  )
}

// --- Una clase: comentarios anónimos ---

export function TeacherClassPage() {
  const { classId } = useParams()
  const { data, error, loading } = useApi<ClassComments>(`/teacher/classes/${classId}/comments`)

  if (error) {
    return (
      <>
        <PageHeader title="Clase" back={{ to: '/docente', label: 'Mis materias' }} />
        <Alert>{error.message}</Alert>
      </>
    )
  }
  if (loading && !data) return <Loading />
  if (!data) return null

  const withText = data.comments.filter((c) => c.liked || c.disliked)
  const onlyRating = data.comments.length - withText.length

  return (
    <>
      <PageHeader title={dateLong(data.date)} back={{ to: `/docente/materias/${data.subject_id}`, label: data.subject_name }}>
        {timeShort(data.start_time)} h
      </PageHeader>

      <AverageSummary average={data.average}>{plural(data.response_count, 'respuesta', 'respuestas')}</AverageSummary>

      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="text-base font-semibold">Comentarios</h2>
        <p className="text-xs text-muted">Anónimos, en orden aleatorio</p>
      </div>

      {data.comments.length === 0 && <EmptyState title="Nadie opinó sobre esta clase todavía" />}

      {withText.length > 0 && (
        <ul className={LIST_CLASS}>
          {withText.map((comment, i) => (
            <li key={i} className="px-4 py-4">
              <p className="flex items-center gap-2 text-sm font-medium">
                <Face rating={comment.rating} size={20} />
                {ratingLabel(comment.rating)}
              </p>
              {comment.liked && (
                <p className="mt-2.5 text-[0.9375rem]">
                  <span className="block text-xs font-medium text-muted">Le gustó</span>
                  {comment.liked}
                </p>
              )}
              {comment.disliked && (
                <p className="mt-2.5 text-[0.9375rem]">
                  <span className="block text-xs font-medium text-muted">No le gustó</span>
                  {comment.disliked}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
      {onlyRating > 0 && (
        <p className="mt-4 text-sm text-muted">
          {onlyRating === 1
            ? '1 persona calificó sin dejar comentarios.'
            : `${onlyRating} personas calificaron sin dejar comentarios.`}
        </p>
      )}
    </>
  )
}
