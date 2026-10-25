import { describe, expect, it } from "vitest"
import { mapJobPhaseToStep } from "@/lib/generation"

describe("mapJobPhaseToStep", () => {
  it("maps each server phase onto its step", () => {
    expect(mapJobPhaseToStep("processing_sources")).toBe("processing-sources")
    expect(mapJobPhaseToStep("preparing_knowledge")).toBe("preparing-knowledge")
    expect(mapJobPhaseToStep("generating_brd")).toBe("generating-brd")
  })

  it("falls back to the first step while queued (null phase)", () => {
    expect(mapJobPhaseToStep(null)).toBe("processing-sources")
  })

  it("falls back to the first step for a phase it does not know", () => {
    expect(mapJobPhaseToStep("something_new")).toBe("processing-sources")
  })
})
