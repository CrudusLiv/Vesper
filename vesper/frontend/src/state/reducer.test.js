import { expect, test } from 'vitest'
import { reducer, initialState } from './reducer.js'

test('UNLOCK sets secret and unlocked', () => {
  const s = reducer(initialState, { type: 'UNLOCK', secret: 'k' })
  expect(s.auth).toEqual({ secret: 'k', unlocked: true })
})

test('LOCK clears auth', () => {
  const s = reducer({ ...initialState, auth: { secret: 'k', unlocked: true } }, { type: 'LOCK' })
  expect(s.auth).toEqual({ secret: null, unlocked: false })
})

test('STATUS_OK replaces status and clears loading', () => {
  const s = reducer(initialState, { type: 'STATUS_OK', status: { integrations: { a: {} }, vault: {}, memory: 'ok' } })
  expect(s.status.integrations).toEqual({ a: {} })
  expect(s.status.loading).toBe(false)
})

test('CHAT_SEND appends user message, sets pending + thinking orb', () => {
  const s = reducer(initialState, { type: 'CHAT_SEND', content: 'hi', ts: 1 })
  expect(s.chat.messages).toEqual([{ role: 'user', content: 'hi', ts: 1 }])
  expect(s.chat.pending).toBe(true)
  expect(s.orb).toBe('thinking')
})

test('CHAT_REPLY appends assistant message with sources, speaking orb', () => {
  const mid = reducer(initialState, { type: 'CHAT_SEND', content: 'hi', ts: 1 })
  const s = reducer(mid, { type: 'CHAT_REPLY', reply: 'yo', sources: [{ path: 'p' }], ts: 2 })
  expect(s.chat.messages[1]).toEqual({ role: 'assistant', content: 'yo', sources: [{ path: 'p' }], ts: 2 })
  expect(s.chat.pending).toBe(false)
  expect(s.orb).toBe('speaking')
})

test('CHAT_ERROR appends an error message and idles orb', () => {
  const mid = reducer(initialState, { type: 'CHAT_SEND', content: 'hi', ts: 1 })
  const s = reducer(mid, { type: 'CHAT_ERROR', error: 'llm unavailable', ts: 2 })
  expect(s.chat.messages[1]).toEqual({ role: 'assistant', content: 'llm unavailable', error: true, ts: 2 })
  expect(s.chat.pending).toBe(false)
  expect(s.orb).toBe('idle')
})

test('MEMORY_RESULTS stores results and clears loading', () => {
  const s = reducer(initialState, { type: 'MEMORY_RESULTS', results: [{ path: 'p' }] })
  expect(s.memory.results).toEqual([{ path: 'p' }])
  expect(s.memory.loading).toBe(false)
})

test('SET_ORB sets orb state', () => {
  expect(reducer(initialState, { type: 'SET_ORB', orb: 'idle' }).orb).toBe('idle')
})

test('unknown action returns same state', () => {
  expect(reducer(initialState, { type: 'NOPE' })).toBe(initialState)
})
