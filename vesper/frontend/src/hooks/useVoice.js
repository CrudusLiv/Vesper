import { useCallback, useState } from 'react'
import { useSpeech } from './useSpeech.js'

export function useVoice({ onTranscript, onSpeak } = {}) {
  const [listening, setListening] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const speech = useSpeech()

  const startListening = useCallback(() => {
    if (!speech.sttSupported) return
    speech.cancelSpeech()
    setSpeaking(false)
    setListening(true)
    speech.startListening(
      (text) => {
        setListening(false)
        if (onTranscript) onTranscript(text)
      },
      {
        onEnd: () => setListening(false),
        onError: () => setListening(false),
      },
    )
  }, [speech, onTranscript])

  const stopListening = useCallback(() => {
    speech.stopListening()
    setListening(false)
  }, [speech])

  const speak = useCallback((text) => {
    if (!speech.ttsSupported) return
    speech.speak(text, {
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false),
    })
    if (onSpeak) onSpeak(text)
  }, [speech, onSpeak])

  const cancelSpeech = useCallback(() => {
    speech.cancelSpeech()
    setSpeaking(false)
  }, [speech])

  return {
    listening,
    speaking,
    sttSupported: speech.sttSupported,
    ttsSupported: speech.ttsSupported,
    startListening,
    stopListening,
    speak,
    cancelSpeech,
  }
}
