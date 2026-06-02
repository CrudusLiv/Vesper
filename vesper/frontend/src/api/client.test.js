import { beforeEach, afterEach, expect, test, vi } from 'vitest'
import { api, AuthError, LlmError, ApiError, getSecret, setSecret, clearSecret } from './client.js'

beforeEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
})
afterEach(() => { vi.restoreAllMocks() })

function mockFetch(status, body) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  })
}

test('secret helpers read/write/clear localStorage', () => {
  expect(getSecret()).toBeNull()
  setSecret('abc')
  expect(getSecret()).toBe('abc')
  clearSecret()
  expect(getSecret()).toBeNull()
})

test('status injects the bearer header from stored secret', async () => {
  setSecret('s3cr3t')
  const f = mockFetch(200, { memory: 'ok' })
  vi.stubGlobal('fetch', f)
  const out = await api.status()
  expect(out).toEqual({ memory: 'ok' })
  const [url, opts] = f.mock.calls[0]
  expect(url).toBe('/api/status')
  expect(opts.headers.Authorization).toBe('Bearer s3cr3t')
})

test('status can use an explicit secret (for the unlock probe)', async () => {
  const f = mockFetch(200, { memory: 'ok' })
  vi.stubGlobal('fetch', f)
  await api.status('probe-secret')
  expect(f.mock.calls[0][1].headers.Authorization).toBe('Bearer probe-secret')
})

test('401 throws AuthError', async () => {
  vi.stubGlobal('fetch', mockFetch(401, {}))
  await expect(api.status('x')).rejects.toBeInstanceOf(AuthError)
})

test('502 throws LlmError', async () => {
  vi.stubGlobal('fetch', mockFetch(502, {}))
  await expect(api.chat('hi', [])).rejects.toBeInstanceOf(LlmError)
})

test('other non-ok throws ApiError', async () => {
  vi.stubGlobal('fetch', mockFetch(500, {}))
  await expect(api.status('x')).rejects.toBeInstanceOf(ApiError)
})

test('search encodes the query and top_k', async () => {
  setSecret('s')
  const f = mockFetch(200, { results: [] })
  vi.stubGlobal('fetch', f)
  await api.search('a b', 3)
  expect(f.mock.calls[0][0]).toBe('/api/memory/search?q=a%20b&top_k=3')
})

test('chat posts message and history as JSON', async () => {
  setSecret('s')
  const f = mockFetch(200, { reply: 'yo', sources: [] })
  vi.stubGlobal('fetch', f)
  await api.chat('hi', [{ role: 'user', content: 'prev' }])
  const [, opts] = f.mock.calls[0]
  expect(opts.method).toBe('POST')
  expect(JSON.parse(opts.body)).toEqual({ message: 'hi', history: [{ role: 'user', content: 'prev' }] })
})
