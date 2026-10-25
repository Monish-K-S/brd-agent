import { describe, expect, it } from "vitest"
import { errorDetail } from "@/lib/errors"

function axiosError(status: number, data: unknown) {
  return {
    isAxiosError: true,
    response: { status, data },
  }
}

describe("errorDetail", () => {
  it("returns a string detail from the server", () => {
    expect(errorDetail(axiosError(409, { detail: "Duplicate file" }))).toBe(
      "Duplicate file",
    )
  })

  it("returns null when detail is not a string", () => {
    expect(errorDetail(axiosError(422, { detail: { code: 1 } }))).toBeNull()
  })

  it("returns null when the response carries no detail", () => {
    expect(errorDetail(axiosError(500, undefined))).toBeNull()
    expect(errorDetail(axiosError(500, {}))).toBeNull()
  })

  it("returns null for a plain Error", () => {
    expect(errorDetail(new Error("boom"))).toBeNull()
  })

  it("returns null for non-error values", () => {
    expect(errorDetail(null)).toBeNull()
    expect(errorDetail("detail")).toBeNull()
    expect(errorDetail(undefined)).toBeNull()
  })
})
