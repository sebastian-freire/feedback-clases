// Escala de calificación de 1 a 5 con caritas (D-014).
export const RATING_LABELS = ['Muy mal', 'Mal', 'Regular', 'Bien', 'Muy bien'] as const

export function ratingLabel(rating: number): string {
  return RATING_LABELS[Math.round(rating) - 1] ?? ''
}
