import { describe, expect, it, vi } from "vitest"
import type { StandardDocumentSummary } from "@/api/documents"
import {
  MAX_UPLOAD_BYTES,
  findDuplicateUpload,
  replaceStoredSource,
  validateUploadSelection,
} from "@/lib/uploadDedup"

function makeFile(name: string, size = 10): File {
  const file = new File(["x"], name, { type: "text/plain" })

  Object.defineProperty(file, "size", { value: size })

  return file
}

function makeDocument(
  id: string,
  fileName: string,
  extension: string,
  sizeBytes: number,
): StandardDocumentSummary {
  return {
    id,
    workspace_id: "ws",
    source_type: "file",
    title: fileName,
    author: null,
    source_created_at: null,
    participants: [],
    metadata: {
      file_name: fileName,
      extension,
      size_bytes: sizeBytes,
    },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  }
}

describe("validateUploadSelection", () => {
  it("accepts a supported file", () => {
    expect(validateUploadSelection([makeFile("notes.txt")])).toBeNull()
  })

  it("accepts an empty selection without complaining", () => {
    expect(validateUploadSelection([])).toBeNull()
  })

  it("rejects more than ten files before checking any individual file", () => {
    const files = Array.from({ length: 11 }, (_, index) =>
      makeFile(`f${index}.txt`),
    )

    expect(validateUploadSelection(files)).toContain("Too many files: 11")
  })

  it("rejects an unsupported extension", () => {
    expect(validateUploadSelection([makeFile("notes.md")])).toBe(
      "Unsupported file type: notes.md. Supported types: .txt, .pdf, .docx",
    )
  })

  it("treats the extension case-insensitively", () => {
    expect(validateUploadSelection([makeFile("SCAN.PDF")])).toBeNull()
  })

  it("rejects a file over the 10MB cap and allows exactly 10MB", () => {
    expect(
      validateUploadSelection([makeFile("big.pdf", MAX_UPLOAD_BYTES + 1)]),
    ).toBe("File too large: big.pdf (max 10MB)")

    expect(
      validateUploadSelection([makeFile("edge.pdf", MAX_UPLOAD_BYTES)]),
    ).toBeNull()
  })
})

describe("findDuplicateUpload", () => {
  const stored = [
    makeDocument("doc-1", "brief.txt", ".txt", 10),
    makeDocument("doc-2", "spec.pdf", ".pdf", 2048),
  ]

  it("returns null when nothing matches", () => {
    expect(findDuplicateUpload([makeFile("new.txt")], stored)).toBeNull()
  })

  it("treats a repeat inside one selection as a hard error", () => {
    const match = findDuplicateUpload(
      [makeFile("a.txt"), makeFile("a.txt")],
      stored,
    )

    expect(match).toEqual({ kind: "batch", fileName: "a.txt" })
  })

  it("returns the stored document id for a name+extension+size match", () => {
    expect(findDuplicateUpload([makeFile("brief.txt", 10)], stored)).toEqual({
      kind: "stored",
      fileName: "brief.txt",
      documentId: "doc-1",
    })
  })

  it("does not match a stored source with a different size", () => {
    expect(findDuplicateUpload([makeFile("brief.txt", 11)], stored)).toBeNull()
  })

  it("does not match a stored source with a different extension", () => {
    expect(findDuplicateUpload([makeFile("brief.pdf", 10)], stored)).toBeNull()
  })

  it("works before any documents have loaded", () => {
    expect(findDuplicateUpload([makeFile("a.txt")], undefined)).toBeNull()
  })
})

describe("replaceStoredSource", () => {
  it("uploads only after the delete resolves", async () => {
    const files = [makeFile("brief.txt")]
    const order: string[] = []
    let release!: () => void

    const remove = vi.fn(() => {
      order.push("remove")

      return new Promise<void>((resolve) => {
        release = resolve
      })
    })
    const upload = vi.fn(() => {
      order.push("upload")
    })

    const pending = replaceStoredSource(
      { documentId: "doc-1", files },
      { remove, upload },
    )

    await Promise.resolve()

    // The server re-checks the dedup triple against committed rows, so an
    // upload that races the delete comes back 409.
    expect(upload).not.toHaveBeenCalled()
    expect(order).toEqual(["remove"])

    release()
    await pending

    expect(remove).toHaveBeenCalledWith("doc-1")
    expect(upload).toHaveBeenCalledWith(files)
    expect(order).toEqual(["remove", "upload"])
  })

  it("never uploads when the delete fails, and surfaces the error", async () => {
    const upload = vi.fn()

    await expect(
      replaceStoredSource(
        { documentId: "doc-1", files: [makeFile("brief.txt")] },
        { remove: () => Promise.reject(new Error("delete failed")), upload },
      ),
    ).rejects.toThrow("delete failed")

    expect(upload).not.toHaveBeenCalled()
  })
})
