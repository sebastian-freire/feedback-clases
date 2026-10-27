import { useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { api, ApiError } from '../../api/client'
import type {
  StudentClass,
  StudentClassDetail,
  StudentFeedback,
  StudentSubject,
  StudentSubjectClasses,
} from '../../api/types'
import { RatingPicker } from '../../components/Face'
import {
  Alert,
  Button,
  EmptyState,
  LIST_CLASS,
  Loading,
  PageHeader,
  ROW_LINK_CLASS,
  TextArea,
  TextField,
} from '../../components/ui'
import { dateLong, dateShort, dayNumber, groupByMonth, plural, timeShort, weekdayShort } from '../../lib/format'
import { useApi } from '../../lib/useApi'

const TEXT_MAX = 500

// --- Mis materias ---

function EnrollForm({ onEnrolled }: { onEnrolled: (name: string) => void }) {
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setSending(true)
    try {
      const subject = await api<StudentSubject>('/student/enrollments', { method: 'POST', body: { code } })
      setCode('')
      onEnrolled(subject.name)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error inesperado.')
    } finally {
      setSending(false)
    }
  }

  return (
    <form onSubmit={submit} className="mt-10 flex flex-col gap-3 border-t border-line pt-6">
      <TextField
        id="code"
        label="Sumarme a una materia"
        hint="Pedile el código de 8 caracteres a tu docente."
        placeholder="Ejemplo: BASES226"
        autoCapitalize="characters"
        autoComplete="off"
        required
        value={code}
        onChange={(e) => setCode(e.target.value.toUpperCase())}
        className="font-medium tracking-[0.15em] placeholder:font-normal placeholder:tracking-normal"
      />
      {error && <Alert>{error}</Alert>}
      <Button type="submit" variant="secondary" disabled={sending || code.trim() === ''}>
        {sending ? 'Inscribiendo…' : 'Inscribirme'}
      </Button>
    </form>
  )
}

export function StudentSubjectsPage() {
  const { data, error, loading, reload } = useApi<StudentSubject[]>('/student/subjects')
  const [enrolled, setEnrolled] = useState<string | null>(null)

  return (
    <>
      <PageHeader title="Mis materias" />
      {enrolled && (
        <div className="mb-4">
          <Alert kind="success">Te inscribiste en {enrolled}.</Alert>
        </div>
      )}
      {error && <Alert>{error.message}</Alert>}
      {loading && !data && <Loading />}
      {data && data.length === 0 && (
        <EmptyState title="Todavía no estás en ninguna materia">
          Ingresá abajo el código que te dio tu docente.
        </EmptyState>
      )}
      {data && data.length > 0 && (
        <ul className={LIST_CLASS}>
          {data.map((subject) => (
            <li key={subject.id}>
              <Link
                to={`/alumno/materias/${subject.id}`}
                className={`${ROW_LINK_CLASS} justify-between`}
              >
                <span>
                  <span className="block font-medium">{subject.name}</span>
                  <span className="text-sm text-muted">{subject.teachers.join(', ')}</span>
                </span>
                <span aria-hidden className="text-xl text-muted">
                  ›
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <EnrollForm
        onEnrolled={(name) => {
          setEnrolled(name)
          reload()
        }}
      />
    </>
  )
}

// --- Clases de una materia ---

function classStatus(c: StudentClass): { text: string; tone: 'action' | 'done' | 'quiet' } {
  if (c.window_state === 'upcoming') return { text: 'Todavía no ocurrió', tone: 'quiet' }
  if (c.window_state === 'closed')
    return c.has_feedback ? { text: 'Enviada', tone: 'quiet' } : { text: 'Cerrada sin opinar', tone: 'quiet' }
  return c.has_feedback
    ? { text: `Enviada, podés editarla hasta el ${dateShort(c.closes_on)}`, tone: 'done' }
    : { text: `Opiná hasta el ${dateShort(c.closes_on)}`, tone: 'action' }
}

function ClassRow({ item }: { item: StudentClass }) {
  const status = classStatus(item)
  const clickable = item.window_state !== 'upcoming'
  const content = (
    <>
      <span className="w-10 shrink-0 text-center">
        <span className="block text-xs text-muted">{weekdayShort(item.date)}</span>
        <span className="block text-lg leading-tight font-semibold tabular-nums">{dayNumber(item.date)}</span>
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium">{timeShort(item.start_time)} h</span>
        <span
          className={`text-sm ${
            status.tone === 'action' ? 'font-medium text-brand' : status.tone === 'done' ? 'text-ink' : 'text-muted'
          }`}
        >
          {status.tone === 'done' && (
            <span aria-hidden className="text-success">
              ✓{' '}
            </span>
          )}
          {status.text}
        </span>
      </span>
      {clickable && (
        <span aria-hidden className="text-xl text-muted">
          ›
        </span>
      )}
    </>
  )
  const base = 'flex items-center gap-4 px-4 py-3'
  return (
    <li>
      {clickable ? (
        <Link to={`/alumno/clases/${item.id}`} className={`${base} hover:bg-subtle`}>
          {content}
        </Link>
      ) : (
        <div className={`${base} opacity-70`}>{content}</div>
      )}
    </li>
  )
}

export function StudentClassesPage() {
  const { subjectId } = useParams()
  const { data, error, loading } = useApi<StudentSubjectClasses>(`/student/subjects/${subjectId}/classes`)
  const pendingClasses = data?.classes.filter((c) => c.window_state === 'open' && !c.has_feedback) ?? []
  const pending = pendingClasses.length
  const upcoming = data?.classes.filter((c) => c.window_state === 'upcoming') ?? []
  const saved = (useLocation().state as { saved?: 'created' | 'updated' } | null)?.saved

  return (
    <>
      <PageHeader title={data?.subject.name ?? 'Materia'} back={{ to: '/alumno', label: 'Mis materias' }}>
        {data &&
          (pending > 0
            ? `Tenés ${pending} ${pending === 1 ? 'clase' : 'clases'} esperando tu opinión.`
            : 'Estás al día con tus opiniones.')}
      </PageHeader>
      {saved && (
        <div className="mb-5">
          <Alert kind="success">{saved === 'created' ? 'Opinión enviada. ¡Gracias!' : 'Cambios guardados.'}</Alert>
        </div>
      )}
      {error && <Alert>{error.message}</Alert>}
      {loading && !data && <Loading />}
      {data && data.classes.length === 0 && <EmptyState title="Esta materia todavía no tiene clases cargadas" />}
      {pending > 0 && (
        <section className="mb-8">
          <h2 className="mb-2 text-sm font-semibold">Para opinar</h2>
          <ul className={LIST_CLASS}>
            {pendingClasses.map((item) => (
              <ClassRow key={item.id} item={item} />
            ))}
          </ul>
        </section>
      )}
      {data &&
        groupByMonth(data.classes.filter((c) => c.window_state !== 'upcoming')).map((group) => (
          <section key={group.month} className="mb-6">
            <h2 className="mb-2 text-sm font-medium text-muted">{group.month}</h2>
            <ul className={LIST_CLASS}>
              {group.items.map((item) => (
                <ClassRow key={item.id} item={item} />
              ))}
            </ul>
          </section>
        ))}
      {upcoming.length > 0 && (
        <p className="text-sm text-muted">
          {plural(upcoming.length, 'clase próxima', 'clases próximas')}, la siguiente el {dateShort(upcoming[0].date)} a las{' '}
          {timeShort(upcoming[0].start_time)} h. Vas a poder opinar desde ese día.
        </p>
      )}
    </>
  )
}

// --- Formulario de feedback ---

type ClassContext = { subjectId: number; subjectName: string; item: StudentClass }

async function findClass(classId: number): Promise<ClassContext> {
  const detail = await api<StudentClassDetail>(`/student/classes/${classId}`)
  return { subjectId: detail.subject.id, subjectName: detail.subject.name, item: detail.class_session }
}

export function FeedbackPage() {
  const classId = Number(useParams().classId)
  const navigate = useNavigate()
  const [context, setContext] = useState<ClassContext | null>(null)
  const [existing, setExisting] = useState<StudentFeedback | null>(null)
  const [rating, setRating] = useState<number | null>(null)
  const [liked, setLiked] = useState('')
  const [disliked, setDisliked] = useState('')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const found = await findClass(classId)
        if (cancelled) return
        setContext(found)
        if (found.item.has_feedback) {
          const mine = await api<StudentFeedback>(`/student/classes/${classId}/feedback`)
          if (cancelled) return
          setExisting(mine)
          setRating(mine.rating)
          setLiked(mine.liked ?? '')
          setDisliked(mine.disliked ?? '')
        }
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof ApiError ? err.message : 'Error inesperado.')
      } finally {
        if (!cancelled) setLoaded(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [classId])

  const back = context
    ? { to: `/alumno/materias/${context.subjectId}`, label: context.subjectName }
    : { to: '/alumno', label: 'Mis materias' }

  if (!loaded) return <Loading />
  if (loadError || !context) {
    return (
      <>
        <PageHeader title="Clase" back={back} />
        <Alert>{loadError}</Alert>
      </>
    )
  }

  const editable = context.item.window_state === 'open'
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (rating === null) {
      setError('Elegí una carita para calificar la clase.')
      return
    }
    setError(null)
    setSending(true)
    try {
      await api<StudentFeedback>(`/student/classes/${classId}/feedback`, {
        method: existing ? 'PUT' : 'POST',
        body: { rating, liked, disliked },
      })
      navigate(back.to, { state: { saved: existing ? 'updated' : 'created' }, replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error inesperado.')
      setSending(false)
    }
  }

  return (
    <>
      <PageHeader title={dateLong(context.item.date)} back={back}>
        {context.subjectName}, {timeShort(context.item.start_time)} h
      </PageHeader>

      {!editable && (
        <div className="mb-5">
          <Alert kind="info">
            {existing
              ? `El plazo para editar cerró el ${dateShort(context.item.closes_on)}. Esto es lo que enviaste.`
              : `El plazo para opinar sobre esta clase cerró el ${dateShort(context.item.closes_on)}.`}
          </Alert>
        </div>
      )}

      {(editable || existing) && (
        <form onSubmit={submit} className="flex flex-col gap-6">
          <RatingPicker value={rating} onChange={setRating} disabled={!editable} />
          <TextArea
            id="liked"
            label="¿Qué te gustó?"
            placeholder="Opcional"
            maxLength={TEXT_MAX}
            value={liked}
            disabled={!editable}
            onChange={(e) => setLiked(e.target.value)}
          />
          <TextArea
            id="disliked"
            label="¿Qué no te gustó?"
            placeholder="Opcional"
            maxLength={TEXT_MAX}
            value={disliked}
            disabled={!editable}
            onChange={(e) => setDisliked(e.target.value)}
          />
          {error && <Alert>{error}</Alert>}
          {editable && (
            <>
              <Button type="submit" disabled={sending}>
                {sending ? 'Guardando…' : existing ? 'Guardar cambios' : 'Enviar opinión'}
              </Button>
              <p className="-mt-3 text-center text-sm text-muted">
                El docente ve tu opinión sin tu nombre. Podés editarla hasta el {dateShort(context.item.closes_on)}.
              </p>
            </>
          )}
        </form>
      )}
    </>
  )
}
