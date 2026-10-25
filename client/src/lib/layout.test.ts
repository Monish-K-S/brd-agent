import { describe, expect, it } from "vitest"
import { DOCUMENT_MEASURE, documentMeasure } from "@/lib/layout"

describe("documentMeasure", () => {
  it("uses the widest measure when both rails are collapsed", () => {
    expect(documentMeasure(false, false)).toBe(DOCUMENT_MEASURE.full)
    expect(documentMeasure(false, false)).toBe("max-w-[1024px]")
  })

  it("uses the middle measure with exactly one rail open", () => {
    expect(documentMeasure(true, false)).toBe("max-w-[880px]")
    expect(documentMeasure(false, true)).toBe("max-w-[880px]")
  })

  it("uses the narrowest measure when both rails are open", () => {
    expect(documentMeasure(true, true)).toBe("max-w-[720px]")
  })
})
