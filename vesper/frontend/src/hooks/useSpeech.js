import { useCallback, useRef } from 'react'

// Tuning + voice heuristic. Change these to adjust how Vesper sounds.
const RATE = 0.95
const PITCH = 0.9
const FEMALE_HINT = /female|zira|aria|jenny|hazel|susan|samantha/i

function recognitionCtor() {
  return globalThis.SpeechRecognition || globalThis.webkitSpeechRecognition || null
}

function pickVoice() {
  const synth = globalThis.speechSynthesis
  if (!synth || typeof synth.getVoices !== 'function') return null
  const voices = synth.getVoices() || []
  if (!voices.length) return null
  const en = voices.filter((v) => /^en/i.test(v.lang))
  return en.find((v) => FEMALE_HINT.test(v.name)) || en[0] || voices[0] || null
}

export function useSpeech() {
  const recognitionRef = useRef(null)

  const sttSupported = !!recognitionCtor()
  const ttsSupported = !!globalThis.speechSynthesis

  const startListening = useCallback((onTranscript, { onEnd, onError } = {}) => {
    const Ctor = recognitionCtor()
    if (!Ctor) return
    const rec = new Ctor()
    rec.continuous = false
    rec.interimResults = false
    rec.lang = 'en-US'
    rec.onresult = (e) => {
      const text = e?.results?.[0]?.[0]?.transcript ?? ''
      if (text) onTranscript(text)
    }
    rec.onend = () => { if (onEnd) onEnd() }
    rec.onerror = (e) => { if (onError) onError(e) }
    recognitionRef.current = rec
    rec.start()
  }, [])

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.abort()
      recognitionRef.current = null
    }
  }, [])

  const cancelSpeech = useCallback(() => {
    if (globalThis.speechSynthesis) globalThis.speechSynthesis.cancel()
  }, [])

  const speak = useCallback((text, { onStart, onEnd } = {}) => {
    const synth = globalThis.speechSynthesis
    const Utter = globalThis.SpeechSynthesisUtterance
    if (!synth || !Utter) return
    synth.cancel()
    const u = new Utter(text)
    const voice = pickVoice()
    if (voice) u.voice = voice
    u.rate = RATE
    u.pitch = PITCH
    if (onStart) u.onstart = onStart
    if (onEnd) u.onend = onEnd
    synth.speak(u)
  }, [])

  return { sttSupported, ttsSupported, startListening, stopListening, speak, cancelSpeech }
}
