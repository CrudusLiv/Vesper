// The single seam between the UI and the Vesper API. Components/hooks call
// `api.*`; nothing else touches fetch or the stored secret.

const SECRET_KEY = 'vesper_secret'

export class AuthError extends Error {}
export class LlmError extends Error {}
export class ApiError extends Error {}

export function getSecret() {
  return localStorage.getItem(SECRET_KEY)
}
export function setSecret(s) {
  localStorage.setItem(SECRET_KEY, s)
}
export function clearSecret() {
  localStorage.removeItem(SECRET_KEY)
}

async function request(path, { method = 'GET', body, secret } = {}) {
  const token = secret ?? getSecret()
  const res = await fetch(`/api${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401) throw new AuthError('unauthorized')
  if (res.status === 502 || res.status === 504) throw new LlmError('llm unavailable')
  if (!res.ok) throw new ApiError(`HTTP ${res.status}`)
  return res.json()
}

export const api = {
  status: (secret) => request('/status', { secret }),
  search: (q, topK = 5) =>
    request(`/memory/search?q=${encodeURIComponent(q)}&top_k=${topK}`),
  chat: (message, history) =>
    request('/chat', { method: 'POST', body: { message, history } }),
}
