import type { StandardDocumentSummary } from "@/api/documents"

export const MAX_UPLOAD_FILES = 10
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024
export const ALLOWED_EXTENSIONS: readonly string[] = [".txt", ".pdf", ".docx"]

export type DuplicateMatch =
  | { kind: "batch"; fileName: string }
  | { kind: "stored"; fileName: string; documentId: string }

export function extensionOf(fileName: string): string {
  return `.${fileName.split(".").pop()?.toLowerCase() ?? ""}`
}

/**
 * Client-side pre-check, mirroring the server's limits. Returns the message
 * to show, or null when the selection may be uploaded.
 *
 * Order matters and is user-visible: too many files is reported before an
 * individual file's type or size.
 */
export function validateUploadSelection(files: File[]): string | null {
  if (files.length > MAX_UPLOAD_FILES) {
    return `Too many files: ${files.length}. Maximum ${MAX_UPLOAD_FILES} files per upload.`
  }

  for (const file of files) {
    const suffix = extensionOf(file.name)

    if (!ALLOWED_EXTENSIONS.includes(suffix)) {
      return `Unsupported file type: ${file.name}. Supported types: .txt, .pdf, .docx`
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      return `File too large: ${file.name} (max 10MB)`
    }
  }

  return null
}

/**
 * Client-side mirror of the server triple check (file name + extension +
 * byte size) — the server re-validates.
 *
 * An in-batch repeat is a hard error (there is nothing to replace); a match
 * against a stored source returns its id so the caller can offer to replace
 * it (L-7).
 */
export function findDuplicateUpload(
  files: File[],
  documents: StandardDocumentSummary[] | undefined,
): DuplicateMatch | null {
  const seen = new Set<string>()

  for (const file of files) {
    const suffix = extensionOf(file.name)
    const key = `${file.name}|${suffix}|${file.size}`

    if (seen.has(key)) {
      return { kind: "batch", fileName: file.name }
    }

    seen.add(key)

    const match = (documents ?? []).find((document) => {
      const metadata = document.metadata ?? {}

      return (
        metadata.file_name === file.name &&
        metadata.extension === suffix &&
        metadata.size_bytes === file.size
      )
    })

    if (match) {
      return {
        kind: "stored",
        fileName: file.name,
        documentId: match.id,
      }
    }
  }

  return null
}

/**
 * Replace a stored source: remove it, and only then upload its replacement.
 *
 * Sequential on purpose. The server re-checks the dedup triple against
 * committed rows, so a parallel upload would race the delete and come back
 * 409. Extracted so that ordering is asserted by a test instead of being a
 * comment in a 2,000-line component.
 */
export async function replaceStoredSource(
  { documentId, files }: { documentId: string; files: File[] },
  operations: {
    remove: (documentId: string) => Promise<unknown>
    upload: (files: File[]) => void
  },
): Promise<void> {
  await operations.remove(documentId)
  operations.upload(files)
}
