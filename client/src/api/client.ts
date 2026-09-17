import axios from "axios"
import { supabase } from "@/lib/supabase"

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 30_000,
})

apiClient.interceptors.request.use(async (config) => {
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
  (error) => {
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
