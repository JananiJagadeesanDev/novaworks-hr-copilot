/**
 * api.js — fetch wrappers and SSE streaming helpers for NovaWorks HR Copilot
 */

const BASE = '/api/v1'

function authHeaders(token) {
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function handleResponse(res) {
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(body.detail || body.message || `HTTP ${res.status}`)
  }
  return body
}

/* ---- Auth ------------------------------------------------ */

export async function apiLogin(email, password) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  return handleResponse(res)
}

export async function apiGetMe(token) {
  const res = await fetch(`${BASE}/auth/me`, {
    headers: authHeaders(token),
  })
  return handleResponse(res)
}

/* ---- Chat — streaming SSE -------------------------------- */

/**
 * Opens an SSE stream to /chat/stream, calling handlers as events arrive.
 *
 * @param {string}   message
 * @param {string}   token
 * @param {object}   handlers  { onStatus, onDelta, onDone, onError }
 * @returns {() => void}  cleanup / abort function
 */
export function streamChat(message, token, { onStatus, onDelta, onDone, onError }) {
  const controller = new AbortController()

  fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ message }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `HTTP ${res.status}`)
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() // keep incomplete chunk

        for (const part of parts) {
          if (!part.trim()) continue
          const lines = part.split('\n')
          let eventType = 'message'
          let dataStr = ''

          for (const line of lines) {
            if (line.startsWith('event:')) eventType = line.slice(6).trim()
            if (line.startsWith('data:'))  dataStr   = line.slice(5).trim()
          }

          if (!dataStr) continue
          let payload
          try { payload = JSON.parse(dataStr) } catch { continue }

          if (eventType === 'status' && onStatus) onStatus(payload)
          if (eventType === 'delta'  && onDelta)  onDelta(payload)
          if (eventType === 'done'   && onDone)   onDone(payload)
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError' && onError) onError(err)
    })

  return () => controller.abort()
}

/* ---- Recent AI Actions ----------------------------------- */

export async function apiGetAuditLogs(token, limit = 20) {
  const res = await fetch(`${BASE}/audit-logs?limit=${limit}`, {
    headers: authHeaders(token),
  })
  // Endpoint may not exist in all deployments — return empty array gracefully
  if (!res.ok) return []
  return res.json().catch(() => [])
}
