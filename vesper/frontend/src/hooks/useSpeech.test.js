import { renderHook, act } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { useSpeech } from './useSpeech.js'

afterEach(() => { vi.unstubAllGlobals() })

test('sttSupported is false when no SpeechRecognition global exists', () => {
  vi.stubGlobal('SpeechRecognition', undefined)
  vi.stubGlobal('webkitSpeechRecognition', undefined)
  const { result } = renderHook(() => useSpeech())
  expect(result.current.sttSupported).toBe(false)
})

test('sttSupported is true when webkitSpeechRecognition exists', () => {
  vi.stubGlobal('webkitSpeechRecognition', class {})
  const { result } = renderHook(() => useSpeech())
  expect(result.current.sttSupported).toBe(true)
})

test('startListening wires a recognition and fires onTranscript on result', () => {
  let inst
  class FakeRec {
    constructor() { inst = this }
    start() { this.started = true }
    abort() { this.aborted = true }
  }
  vi.stubGlobal('SpeechRecognition', FakeRec)
  const { result } = renderHook(() => useSpeech())
  const onTranscript = vi.fn()
  act(() => result.current.startListening(onTranscript, {}))
  expect(inst.started).toBe(true)
  expect(inst.continuous).toBe(false)
  expect(inst.lang).toBe('en-US')
  act(() => inst.onresult({ results: [[{ transcript: 'hello there' }]] }))
  expect(onTranscript).toHaveBeenCalledWith('hello there')
})

test('stopListening aborts the active recognition', () => {
  let inst
  class FakeRec {
    constructor() { inst = this }
    start() {}
    abort() { this.aborted = true }
  }
  vi.stubGlobal('SpeechRecognition', FakeRec)
  const { result } = renderHook(() => useSpeech())
  act(() => result.current.startListening(() => {}, {}))
  act(() => result.current.stopListening())
  expect(inst.aborted).toBe(true)
})

test('ttsSupported false and speak no-ops when speechSynthesis absent', () => {
  vi.stubGlobal('speechSynthesis', undefined)
  const { result } = renderHook(() => useSpeech())
  expect(result.current.ttsSupported).toBe(false)
  act(() => result.current.speak('hi', {}))
})

test('speak picks a tuned female en voice and calls speechSynthesis.speak', () => {
  const spoken = []
  const synth = {
    cancel: vi.fn(),
    speak: (u) => spoken.push(u),
    getVoices: () => [
      { name: 'Microsoft David', lang: 'en-US' },
      { name: 'Microsoft Zira', lang: 'en-US' },
    ],
  }
  vi.stubGlobal('speechSynthesis', synth)
  vi.stubGlobal('SpeechSynthesisUtterance', class { constructor(t) { this.text = t } })
  const { result } = renderHook(() => useSpeech())
  act(() => result.current.speak('hi there', {}))
  expect(synth.cancel).toHaveBeenCalled()
  expect(spoken).toHaveLength(1)
  expect(spoken[0].voice.name).toBe('Microsoft Zira')
  expect(spoken[0].rate).toBe(1.05)
  expect(spoken[0].pitch).toBe(1.25)
})

test('speak prefers a Google neural voice over robotic Microsoft SAPI', () => {
  const spoken = []
  const synth = {
    cancel: vi.fn(),
    speak: (u) => spoken.push(u),
    getVoices: () => [
      { name: 'Microsoft David - English (United States)', lang: 'en-US' },
      { name: 'Microsoft Zira - English (United States)', lang: 'en-US' },
      { name: 'Google US English', lang: 'en-US' },
      { name: 'Google UK English Female', lang: 'en-GB' },
    ],
  }
  vi.stubGlobal('speechSynthesis', synth)
  vi.stubGlobal('SpeechSynthesisUtterance', class { constructor(t) { this.text = t } })
  const { result } = renderHook(() => useSpeech())
  act(() => result.current.speak('hi there', {}))
  expect(spoken[0].voice.name).toBe('Google UK English Female')
})

test('prefers a Japanese voice and sets the utterance lang to ja-JP', () => {
  const spoken = []
  const synth = {
    cancel: vi.fn(),
    speak: (u) => spoken.push(u),
    getVoices: () => [
      { name: 'Google UK English Female', lang: 'en-GB' },
      { name: 'Google 日本語', lang: 'ja-JP' },
    ],
  }
  vi.stubGlobal('speechSynthesis', synth)
  vi.stubGlobal('SpeechSynthesisUtterance', class { constructor(t) { this.text = t } })
  const { result } = renderHook(() => useSpeech())
  act(() => result.current.speak('hi there', {}))
  expect(spoken[0].voice.name).toBe('Google 日本語')
  expect(spoken[0].lang).toBe('ja-JP')
})

test('cancelSpeech calls speechSynthesis.cancel', () => {
  const synth = { cancel: vi.fn(), speak: vi.fn(), getVoices: () => [] }
  vi.stubGlobal('speechSynthesis', synth)
  const { result } = renderHook(() => useSpeech())
  act(() => result.current.cancelSpeech())
  expect(synth.cancel).toHaveBeenCalled()
})
