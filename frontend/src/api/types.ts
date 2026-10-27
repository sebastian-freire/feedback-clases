// Tipos de la API (ver http://localhost:8000/docs).

export type Role = 'student' | 'teacher' | 'admin'
export type WindowState = 'upcoming' | 'open' | 'closed'

export type User = { id: number; email: string; full_name: string; roles: Role[] }
export type TokenResponse = { access_token: string; token_type: string; user: User }

export type StudentSubject = { id: number; name: string; teachers: string[] }
export type StudentClass = {
  id: number
  date: string
  start_time: string
  window_state: WindowState
  closes_on: string
  has_feedback: boolean
}
export type StudentClassDetail = { subject: StudentSubject; class_session: StudentClass }
export type StudentSubjectClasses = { subject: StudentSubject; classes: StudentClass[] }
export type FeedbackInput = { rating: number; liked: string | null; disliked: string | null }
export type StudentFeedback = FeedbackInput & {
  class_session_id: number
  editable: boolean
  closes_on: string
}

export type TeacherSubject = {
  id: number
  name: string
  enrollment_code: string
  class_count: number
  response_count: number
  average: number | null
}
export type ClassSummary = {
  id: number
  date: string
  start_time: string
  window_state: WindowState
  response_count: number
  average: number | null
}
export type SubjectSummary = { subject: TeacherSubject; classes: ClassSummary[] }
export type AnonymousFeedback = { rating: number; liked: string | null; disliked: string | null }
export type ClassComments = {
  id: number
  subject_id: number
  subject_name: string
  date: string
  start_time: string
  response_count: number
  average: number | null
  comments: AnonymousFeedback[]
}

export type UserBrief = { id: number; full_name: string; email: string }
export type AdminSubject = {
  id: number
  name: string
  enrollment_code: string
  teachers: UserBrief[]
  class_count: number
  student_count: number
}
export type AdminClass = { id: number; date: string; start_time: string; can_delete: boolean }
export type AdminSubjectDetail = AdminSubject & { classes: AdminClass[] }
export type ScheduleRule = { weekday: number; start_time: string }

export type WordCount = { word: string; count: number }
export type TopWords = { liked: WordCount[]; disliked: WordCount[] }
export type SubjectComparison = {
  id: number
  name: string
  average: number | null
  response_count: number
  past_class_count: number
  student_count: number
  participation: number | null
}
