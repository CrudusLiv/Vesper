import { useCallback, useRef } from 'react'

// Tuning + voice preference. Change these to adjust how Vesper sounds.
// Tuned for a younger, snappier tsundere read: pitch up, a touch quick. Drop
// PITCH toward 1.0 and RATE toward 0.95 for a calmer/older delivery.
const RATE = 1.05
const PITCH = 1.25
// Tried in order; first English voice matching the earliest tier wins. The old
// Microsoft SAPI voices (Zira/David) are robotic, so they sit last — only used
// when nothing better is installed. "Google US English" reads younger/brighter
// (best for the tsundere tone); Natural/Online (Edge) are neural; other Google
// voices beat SAPI.
// Each tier is matched against "<name> <lang>" across ALL voices, so the
// Japanese tier can match by lang and read English with a Japanese accent.
const VOICE_PREFERENCE = [
  /ja[-_]?jp|日本語|japanese/i,            // Japanese voice → accented English (anime tone)
  /google uk english female/i,            // smoothest English; holds the pitch-up cleanly
  /natural|online/i,                      // Edge neural voices
  /google.*female/i,                      // any Google female
  /google/i,                              // any Google (still better than SAPI)
  /female|aria|jenny|hazel|susan|samantha|zira/i, // legacy SAPI fallback
]

function recognitionCtor() {
  return globalThis.SpeechRecognition || globalThis.webkitSpeechRecognition || null
}

function pickVoice() {
  const synth = globalThis.speechSynthesis
  if (!synth || typeof synth.getVoices !== 'function') return null
  const voices = synth.getVoices() || []
  if (!voices.length) return null
  for (const re of VOICE_PREFERENCE) {
    const match = voices.find((v) => re.test(`${v.name} ${v.lang}`))
    if (match) return match
  }
  return voices.find((v) => /^en/i.test(v.lang)) || voices[0] || null
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
    if (voice) {
      u.voice = voice
      u.lang = voice.lang // match the voice's locale (e.g. ja-JP) so it engages correctly
    }
    u.rate = RATE
    u.pitch = PITCH
    if (onStart) u.onstart = onStart
    if (onEnd) u.onend = onEnd
    synth.speak(u)
  }, [])

  return { sttSupported, ttsSupported, startListening, stopListening, speak, cancelSpeech }
}
