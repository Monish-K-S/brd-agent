import { isAxiosError } from "axios"

/** Server `detail` from an axios error, when it is a plain string. */
export function errorDetail(error: unknown): string | null {
  if (!isAxiosError(error)) {
    return null
  }

  const detail = (error.response?.data as { detail?: unknown } | undefined)
    ?.detail

  return typeof detail === "string" ? detail : null
}
