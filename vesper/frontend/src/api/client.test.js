import { beforeEach, afterEach, expect, test, vi } from 'vitest'
import { api, AuthError, LlmError, ApiError, ConflictError, getSecret, setSecret, clearSecret } from './client.js'

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

test('finance posts amount/category/note as JSON', async () => {
  setSecret('s')
  const f = mockFetch(200, { month_total: 5, category_total: 5, currency: 'RM', date: 'x' })
  vi.stubGlobal('fetch', f)
  await api.finance(5, 'food', 'lunch')
  const [url, opts] = f.mock.calls[0]
  expect(url).toBe('/api/finance')
  expect(opts.method).toBe('POST')
  expect(JSON.parse(opts.body)).toEqual({ amount: 5, category: 'food', note: 'lunch' })
})

test('financeSummary GETs the summary', async () => {
  setSecret('s'); const f = mockFetch(200, { summary: 'x' }); vi.stubGlobal('fetch', f)
  await api.financeSummary()
  expect(f.mock.calls[0][0]).toBe('/api/finance/summary')
})

test('note posts text', async () => {
  setSecret('s'); const f = mockFetch(200, { ok: true }); vi.stubGlobal('fetch', f)
  await api.note('hello')
  const [url, opts] = f.mock.calls[0]
  expect(url).toBe('/api/note')
  expect(opts.method).toBe('POST')
  expect(JSON.parse(opts.body)).toEqual({ text: 'hello' })
})

test('getSchedule GETs the schedule', async () => {
  setSecret('s'); const f = mockFetch(200, { schedule: null }); vi.stubGlobal('fetch', f)
  await api.getSchedule()
  expect(f.mock.calls[0][0]).toBe('/api/schedule')
})

test('setSchedule posts text and confirm', async () => {
  setSecret('s'); const f = mockFetch(200, { summary: 'ok' }); vi.stubGlobal('fetch', f)
  await api.setSchedule('mon 9-10 maths', true)
  const [url, opts] = f.mock.calls[0]
  expect(url).toBe('/api/schedule')
  expect(opts.method).toBe('POST')
  expect(JSON.parse(opts.body)).toEqual({ text: 'mon 9-10 maths', confirm: true })
})

test('setSchedule 409 throws ConflictError carrying the body', async () => {
  setSecret('s'); vi.stubGlobal('fetch', mockFetch(409, { summary: 'preview', exists: true }))
  await expect(api.setSchedule('x', false)).rejects.toBeInstanceOf(ConflictError)
})

test('setSchedule 409 error exposes .data', async () => {
  setSecret('s'); vi.stubGlobal('fetch', mockFetch(409, { summary: 'preview', exists: true }))
  expect.assertions(1)
  await api.setSchedule('x', false).catch((err) => {
    expect(err.data).toEqual({ summary: 'preview', exists: true })
  })
})

test('vaultList encodes the dir query', async () => {
  setSecret('s'); const f = mockFetch(200, { directory: 'a/b', entries: [] }); vi.stubGlobal('fetch', f)
  await api.vaultList('a/b')
  expect(f.mock.calls[0][0]).toBe('/api/vault/list?dir=a%2Fb')
})

test('vaultDelete posts the path', async () => {
  setSecret('s'); const f = mockFetch(200, { path: 'notes/x.md', trash_path: '_trash/x.md' }); vi.stubGlobal('fetch', f)
  await api.vaultDelete('notes/x.md')
  expect(f.mock.calls[0][0]).toBe('/api/vault/delete')
  expect(JSON.parse(f.mock.calls[0][1].body)).toEqual({ path: 'notes/x.md' })
})

test('vaultUndo POSTs undo', async () => {
  setSecret('s'); const f = mockFetch(200, { message: 'nothing to undo' }); vi.stubGlobal('fetch', f)
  await api.vaultUndo()
  expect(f.mock.calls[0][0]).toBe('/api/vault/undo')
  expect(f.mock.calls[0][1].method).toBe('POST')
})

test('uploadInbox posts the file as multipart with the bearer header', async () => {
  setSecret('s')
  const f = mockFetch(202, { id: '1', filename: 'x.pptx', status: 'queued' })
  vi.stubGlobal('fetch', f)
  const file = new File(['data'], 'x.pptx')
  await api.uploadInbox(file)
  const [url, opts] = f.mock.calls[0]
  expect(url).toBe('/api/inbox/upload')
  expect(opts.method).toBe('POST')
  expect(opts.body).toBeInstanceOf(FormData)
  expect(opts.body.get('file')).toBe(file)
  expect(opts.headers.Authorization).toBe('Bearer s')
  // The browser must set the multipart boundary itself.
  expect(opts.headers['Content-Type']).toBeUndefined()
})

test('uploadInbox surfaces a 415 as ApiError', async () => {
  setSecret('s'); vi.stubGlobal('fetch', mockFetch(415, { detail: 'bad type' }))
  await expect(api.uploadInbox(new File(['d'], 'x.txt'))).rejects.toBeInstanceOf(ApiError)
})

test('inboxUploads GETs the uploads list', async () => {
  setSecret('s'); const f = mockFetch(200, [{ id: '1', status: 'done' }]); vi.stubGlobal('fetch', f)
  await api.inboxUploads()
  expect(f.mock.calls[0][0]).toBe('/api/inbox/uploads')
})

describe('getFeed', () => {
  it('GETs /api/feed with auth', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => [{ id: 'x', kind: 'error', read: false }],
    })
    localStorage.setItem('vesper_secret', 'tok')
    const result = await api.getFeed()
    expect(fetch).toHaveBeenCalledWith(
      '/api/feed?limit=50',
      expect.objectContaining({ method: 'GET' }),
    )
    expect(result[0].kind).toBe('error')
  })
})

describe('markFeedItemRead', () => {
  it('PATCHes /api/feed/{id}/read', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ id: 'x', read: true }),
    })
    localStorage.setItem('vesper_secret', 'tok')
    const result = await api.markFeedItemRead('x')
    expect(fetch).toHaveBeenCalledWith(
      '/api/feed/x/read',
      expect.objectContaining({ method: 'PATCH' }),
    )
    expect(result.read).toBe(true)
  })
})
