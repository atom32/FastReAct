const DEFAULT_GATEWAY_HTTP = "http://localhost:9000"
const DEFAULT_GATEWAY_WS = "ws://localhost:9000"

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "")
}

function browserHttpBase(): string {
  if (typeof window === "undefined") return DEFAULT_GATEWAY_HTTP
  return `${window.location.protocol}//${window.location.hostname}:9000`
}

function browserWsBase(): string {
  if (typeof window === "undefined") return DEFAULT_GATEWAY_WS
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
  return `${protocol}//${window.location.hostname}:9000`
}

export function gatewayHttpBase(): string {
  return trimTrailingSlash(
    process.env.NEXT_PUBLIC_FASTREACT_GATEWAY_HTTP_URL || browserHttpBase(),
  )
}

export function gatewayWsBase(): string {
  return trimTrailingSlash(
    process.env.NEXT_PUBLIC_FASTREACT_GATEWAY_WS_URL || browserWsBase(),
  )
}

export function gatewayApi(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`
  return `${gatewayHttpBase()}${normalized}`
}

export function gatewayWsPath(path = "/ws", userKey?: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`
  const url = new URL(`${gatewayWsBase()}${normalized}`)
  if (userKey && userKey !== "web:default") {
    url.searchParams.set("user_key", userKey)
  }
  return url.toString()
}

export function summarizeSafe(value: unknown, maxLength = 240): string {
  const sensitive = /api[_-]?key|apikey|token|pat|password|secret|authorization/i
  const seen = new WeakSet<object>()

  const clean = (input: unknown): unknown => {
    if (input === null || input === undefined) return input
    if (typeof input === "string") {
      if (input.startsWith("sk-")) return "***"
      return input.length > maxLength ? `${input.slice(0, maxLength)}...` : input
    }
    if (typeof input !== "object") return input
    if (seen.has(input)) return "[Circular]"
    seen.add(input)
    if (Array.isArray(input)) return input.slice(0, 20).map(clean)
    return Object.fromEntries(
      Object.entries(input as Record<string, unknown>).map(([key, inner]) => [
        key,
        sensitive.test(key) ? "***" : clean(inner),
      ]),
    )
  }

  const text = JSON.stringify(clean(value), null, 2) || ""
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
}
