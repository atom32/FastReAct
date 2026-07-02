const DEFAULT_SERVICE_HTTP = "http://localhost:18741"
const SERVICE_TOKEN_STORAGE = "fastreact_service_token"
const SERVICE_URL_STORAGE = "fastreact_service_url"

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "")
}

function browserServiceBase(): string {
  if (typeof window === "undefined") return DEFAULT_SERVICE_HTTP
  return `${window.location.protocol}//${window.location.hostname}:18741`
}

export function serviceHttpBase(): string {
  if (process.env.NEXT_PUBLIC_FASTREACT_SERVICE_HTTP_URL) {
    return trimTrailingSlash(process.env.NEXT_PUBLIC_FASTREACT_SERVICE_HTTP_URL)
  }
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(SERVICE_URL_STORAGE)
    if (stored?.trim()) return trimTrailingSlash(stored.trim())
  }
  return trimTrailingSlash(browserServiceBase())
}

export function setServiceHttpBase(value: string): void {
  if (typeof window === "undefined") return
  const trimmed = trimTrailingSlash(value.trim())
  if (trimmed) localStorage.setItem(SERVICE_URL_STORAGE, trimmed)
  else localStorage.removeItem(SERVICE_URL_STORAGE)
}

export function getServiceToken(): string {
  if (process.env.NEXT_PUBLIC_FASTREACT_SERVICE_TOKEN) {
    return process.env.NEXT_PUBLIC_FASTREACT_SERVICE_TOKEN
  }
  if (typeof window === "undefined") return ""
  return localStorage.getItem(SERVICE_TOKEN_STORAGE) || ""
}

export function setServiceToken(value: string): void {
  if (typeof window === "undefined") return
  if (value.trim()) localStorage.setItem(SERVICE_TOKEN_STORAGE, value.trim())
  else localStorage.removeItem(SERVICE_TOKEN_STORAGE)
}

export function serviceApi(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`
  return `${serviceHttpBase()}${normalized}`
}

export async function serviceFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  const token = getServiceToken()
  if (token) {
    headers.set("Authorization", `Bearer ${token}`)
    headers.set("X-FastReAct-Service-Token", token)
  }
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  return fetch(serviceApi(path), { ...init, headers })
}

export async function serviceJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await serviceFetch(path, init)
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`${response.status} ${response.statusText}: ${text || path}`)
  }
  return response.json() as Promise<T>
}

export function truncateJson(value: unknown, maxLength = 900): string {
  const text = stringifyJson(value)
  if (!text) return ""
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
}

export function stringifyJson(value: unknown): string {
  if (typeof value === "string") return value
  return JSON.stringify(value, null, 2)
}
