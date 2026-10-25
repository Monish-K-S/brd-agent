/**
 * Document measure follows the rails: comfortable at full chrome, roomier as
 * rails collapse. The transition itself is handled in CSS; this only picks
 * the class.
 */

export const DOCUMENT_MEASURE = {
  full: "max-w-[1024px]",
  oneRail: "max-w-[880px]",
  bothRails: "max-w-[720px]",
} as const

export function documentMeasure(sourcesOpen: boolean, qaOpen: boolean): string {
  if (!sourcesOpen && !qaOpen) {
    return DOCUMENT_MEASURE.full
  }

  if (!sourcesOpen || !qaOpen) {
    return DOCUMENT_MEASURE.oneRail
  }

  return DOCUMENT_MEASURE.bothRails
}
