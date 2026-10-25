/**
 * Export filename and download helpers.
 *
 * Extracted from WorkspacePage so they can be tested: these run on every
 * PDF/DOCX download and a bad filename is invisible until a user opens
 * their downloads folder.
 */

export const MAX_EXPORT_NAME_CHARS = 80

export function safeExportFilename(
  workspaceName: string,
  extension: string,
): string {
  let stem = workspaceName.trim() || "BRD"

  // eslint-disable-next-line no-control-regex
  stem = stem.replace(/[\x00-\x1f\x7f"\\/]/g, "")

  stem = stem.replace(/\s+/g, " ").replace(/^[./]+/, "") || "BRD"

  if (stem.length > MAX_EXPORT_NAME_CHARS) {
    stem = stem.slice(0, MAX_EXPORT_NAME_CHARS).trimEnd() || "BRD"
  }

  return `${stem} - BRD.${extension}`
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)

  const link = document.createElement("a")
  link.href = url
  link.download = filename

  document.body.appendChild(link)
  link.click()
  link.remove()

  window.URL.revokeObjectURL(url)
}
