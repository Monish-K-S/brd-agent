import { describe, expect, it, vi } from "vitest"
import { downloadBlob, safeExportFilename } from "@/lib/files"

describe("safeExportFilename", () => {
  it("builds '<name> - BRD.<ext>'", () => {
    expect(safeExportFilename("Sourcify", "pdf")).toBe("Sourcify - BRD.pdf")
    expect(safeExportFilename("Sourcify", "docx")).toBe("Sourcify - BRD.docx")
  })

  it("trims surrounding whitespace", () => {
    expect(safeExportFilename("  Q4 rollout  ", "pdf")).toBe(
      "Q4 rollout - BRD.pdf",
    )
  })

  it("falls back to BRD when the name is empty or whitespace", () => {
    expect(safeExportFilename("", "pdf")).toBe("BRD - BRD.pdf")
    expect(safeExportFilename("   ", "pdf")).toBe("BRD - BRD.pdf")
  })

  it("strips path separators, quotes and control characters", () => {
    expect(safeExportFilename('a/b\\c"d', "pdf")).toBe("abcd - BRD.pdf")
    expect(safeExportFilename("line\u0000break", "pdf")).toBe(
      "linebreak - BRD.pdf",
    )
  })

  it("collapses runs of whitespace into single spaces", () => {
    expect(safeExportFilename("a \n\t b", "pdf")).toBe("a b - BRD.pdf")
  })

  it("drops a leading dot or slash so the name is not hidden", () => {
    expect(safeExportFilename("..secret", "pdf")).toBe("secret - BRD.pdf")
  })

  it("caps the stem at 80 characters", () => {
    const filename = safeExportFilename("x".repeat(200), "pdf")

    expect(filename).toBe(`${"x".repeat(80)} - BRD.pdf`)
  })

  it("keeps unicode and emoji, which the PDF/DOCX builders accept", () => {
    expect(safeExportFilename("Café ☕", "pdf")).toBe("Café ☕ - BRD.pdf")
  })
})

describe("downloadBlob", () => {
  it("clicks a link with the filename and revokes the object URL", () => {
    const blob = new Blob(["x"])
    const createUrl = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:test")
    const revokeUrl = vi
      .spyOn(URL, "revokeObjectURL")
      .mockImplementation(() => {})
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {})

    downloadBlob(blob, "Report - BRD.pdf")

    expect(createUrl).toHaveBeenCalledWith(blob)
    expect(click).toHaveBeenCalledTimes(1)
    expect(revokeUrl).toHaveBeenCalledWith("blob:test")
    expect(document.querySelector("a")).toBeNull()

    createUrl.mockRestore()
    revokeUrl.mockRestore()
    click.mockRestore()
  })
})
