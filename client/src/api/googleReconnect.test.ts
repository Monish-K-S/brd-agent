import { describe, expect, it } from "vitest"
import {
  GoogleReconnectRequiredError,
  isGoogleReconnectRequiredError,
  throwIfGoogleReconnectRequired,
} from "@/api/googleReconnect"

function response(status: number, data: unknown) {
  return { isAxiosError: true, response: { status, data } }
}

describe("throwIfGoogleReconnectRequired", () => {
  it("throws a reconnect error for a 409 on the same connector", () => {
    expect(() =>
      throwIfGoogleReconnectRequired(
        response(409, { reconnect_required: true, connector: "gmail" }),
        "gmail",
      ),
    ).toThrow(GoogleReconnectRequiredError)
  })

  it("carries the connector on the thrown error", () => {
    try {
      throwIfGoogleReconnectRequired(
        response(409, { reconnect_required: true, connector: "drive" }),
        "drive",
      )
    } catch (error) {
      expect(isGoogleReconnectRequiredError(error, "drive")).toBe(true)
    }
  })

  it("ignores a 409 that belongs to the other connector", () => {
    // Connecting Drive must never tear down a healthy Gmail grant.
    expect(() =>
      throwIfGoogleReconnectRequired(
        response(409, { reconnect_required: true, connector: "drive" }),
        "gmail",
      ),
    ).not.toThrow()
  })

  it("ignores a 409 without the reconnect flag", () => {
    expect(() =>
      throwIfGoogleReconnectRequired(
        response(409, { detail: "Duplicate file" }),
        "gmail",
      ),
    ).not.toThrow()
  })

  it("ignores other statuses and non-axios errors", () => {
    expect(() =>
      throwIfGoogleReconnectRequired(
        response(401, { reconnect_required: true, connector: "gmail" }),
        "gmail",
      ),
    ).not.toThrow()

    expect(() =>
      throwIfGoogleReconnectRequired(new Error("boom"), "gmail"),
    ).not.toThrow()
  })
})

describe("isGoogleReconnectRequiredError", () => {
  it("matches the class, optionally filtered by connector", () => {
    const error = new GoogleReconnectRequiredError("gmail")

    expect(isGoogleReconnectRequiredError(error)).toBe(true)
    expect(isGoogleReconnectRequiredError(error, "gmail")).toBe(true)
    expect(isGoogleReconnectRequiredError(error, "drive")).toBe(false)
    expect(isGoogleReconnectRequiredError(new Error("other"))).toBe(false)
  })
})
