import axios, { type InternalAxiosRequestConfig } from "axios"
import { supabase } from "@/lib/supabase"

const apiBaseUrl = import.meta.env.VITE_API_URL as string | undefined

if (!apiBaseUrl && typeof console !== "undefined") {
  console.warn(
    "VITE_API_URL is not set. API requests will target the page origin. " +
      "See client/.env.example.",
  )
}

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30_000,
})

type RetriableRequest = InternalAxiosRequestConfig & {
  _retry?: boolean
}

let refreshPromise: Promise<string | null> | null = null

function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = supabase.auth
      .refreshSession()
      .then(({ data }) => data.session?.access_token ?? null)
      .catch(() => null)
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

apiClient.interceptors.request.use(async (config) => {
  if (!apiBaseUrl) {
    throw new Error(
      "API URL is not configured. Set VITE_API_URL (see client/.env.example).",
    )
  }

  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }

  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error?.config as RetriableRequest | undefined

    if (
      error?.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true

      const token = await refreshAccessToken()

      if (token) {
        originalRequest.headers.Authorization = `Bearer ${token}`

        return apiClient(originalRequest)
      }

      await supabase.auth.signOut().catch(() => {})

      if (
        typeof window !== "undefined" &&
        window.location.pathname !== "/auth"
      ) {
        window.location.replace("/auth")
      }

      return Promise.reject(error)
    }

    if (error?.response?.status === 429) {
      const retryAfter = error.response.headers?.["retry-after"]
      const seconds = retryAfter ? Number(retryAfter) : NaN

      const suffix =
        Number.isFinite(seconds) && seconds > 0
          ? ` Try again in ${seconds}s.`
          : " Please try again later."

      const serverDetail = error.response.data?.detail

      const message =
        typeof serverDetail === "string" && serverDetail.length > 0
          ? serverDetail
          : `Too many requests.${suffix}`

      return Promise.reject(new Error(message))
    }

    return Promise.reject(error)
  },
)
