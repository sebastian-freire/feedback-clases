import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { apiDownload, ApiError } from '../../api/client'
import type { SubjectSummary, TopWords, WordCount } from '../../api/types'
import { BarList } from '../../components/BarList'
import { TrendChart } from '../../components/TrendChart'
import { Alert, Button, EmptyState, Loading, PageHeader, SectionTitle } from '../../components/ui'
import { dateShort, formatAverage, plural, timeShort } from '../../lib/format'
import { useApi } from '../../lib/useApi'
import { AverageSummary, EnrollmentCode } from './TeacherPages'

function WordColumn({ title, words }: { title: string; words: WordCount[] }) {
  return (
    <div>
      <h3 className="mb-3 text-sm font-medium text-muted">{title}</h3>
      {words.length === 0 ? (
        <p className="text-sm text-muted">Sin comentarios todavía.</p>
      ) : (
        <BarList
          label={title}
          max={words[0].count}
          bars={words.map((w) => ({ label: w.word, value: w.count, display: String(w.count) }))}
        />
      )}
    </div>
  )
}

function TopWordsSection({ subjectId }: { subjectId: string }) {
  const { data, error } = useApi<TopWords>(`/teacher/subjects/${subjectId}/top-words?limit=8`)
  return (
    <section className="mb-10">
      <SectionTitle hint="En los comentarios de todo el semestre, sin contar palabras comunes.">
        Palabras más repetidas
      </SectionTitle>
      {error && <Alert>{error.message}</Alert>}
      {data && (
        <div className="grid gap-8 sm:grid-cols-2">
          <WordColumn title="En lo que gustó" words={data.liked} />
          <WordColumn title="En lo que no gustó" words={data.disliked} />
        </div>
      )}
    </section>
  )
}

function DownloadButton({ subjectId }: { subjectId: string }) {
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const download = async () => {
    setError(null)
    setBusy(true)
    try {
      await apiDownload(`/teacher/subjects/${subjectId}/export.csv`, 'feedback.csv')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo descargar la planilla.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <Button variant="secondary" onClick={download} disabled={busy} className="min-h-9 shrink-0 px-3 text-sm">
        {busy ? 'Preparando…' : 'Exportar CSV'}
      </Button>
      {error && (
        <div className="mt-3 w-full">
          <Alert>{error}</Alert>
        </div>
      )}
    </>
  )
}

// --- Una materia: promedio por clase y tendencia ---

export function TeacherSubjectPage() {
  const { subjectId } = useParams()
  const { data, error, loading } = useApi<SubjectSummary>(`/teacher/subjects/${subjectId}/summary`)
  const back = { to: '/docente', label: 'Mis materias' }

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

  const { subject, classes } = data
  const past = classes.filter((c) => c.window_state !== 'upcoming')
  const upcoming = classes.filter((c) => c.window_state === 'upcoming')

  return (
    <>
      <PageHeader title={subject.name} back={back}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <EnrollmentCode code={subject.enrollment_code} />
          <DownloadButton subjectId={String(subjectId)} />
        </div>
      </PageHeader>

      <AverageSummary average={subject.average}>
        Promedio del semestre: {plural(subject.response_count, 'respuesta', 'respuestas')} en{' '}
        {plural(past.length, 'clase dictada', 'clases dictadas')}
      </AverageSummary>

      <section className="mb-10">
        <SectionTitle>Promedio por clase</SectionTitle>
        <TrendChart classes={classes} />
      </section>

      <TopWordsSection subjectId={String(subjectId)} />

      <section>
        <SectionTitle>Clases dictadas</SectionTitle>
        {past.length === 0 ? (
          <EmptyState title="Todavía no se dictó ninguna clase" />
        ) : (
          <div className="-mx-4 overflow-hidden border-y border-line sm:mx-0 sm:rounded-lg sm:border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line bg-subtle text-xs text-muted">
                <tr>
                  <th scope="col" className="px-4 py-2.5 font-medium">
                    Clase
                  </th>
                  <th scope="col" className="px-2 py-2.5 text-right font-medium">
                    Respuestas
                  </th>
                  <th scope="col" className="px-4 py-2.5 text-right font-medium">
                    Promedio
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {past.map((c) => (
                  <tr key={c.id} className="hover:bg-subtle">
                    <td className="px-4 py-1.5">
                      <Link
                        to={`/docente/clases/${c.id}`}
                        className="flex min-h-10 flex-col justify-center font-medium text-brand hover:underline"
                      >
                        {dateShort(c.date)}, {timeShort(c.start_time)} h
                        {c.window_state === 'open' && (
                          <span className="text-xs font-normal text-muted">Todavía recibe respuestas</span>
                        )}
                      </Link>
                    </td>
                    <td className="px-2 py-1.5 text-right text-muted tabular-nums">{c.response_count}</td>
                    <td className="px-4 py-1.5 text-right font-medium tabular-nums">{formatAverage(c.average)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {upcoming.length > 0 && (
          <p className="mt-3 text-sm text-muted">
            {plural(upcoming.length, 'clase próxima', 'clases próximas')}, la siguiente el{' '}
            {dateShort(upcoming[0].date)} a las {timeShort(upcoming[0].start_time)} h.
          </p>
        )}
      </section>
    </>
  )
}
