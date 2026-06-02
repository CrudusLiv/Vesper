// STUB for the Phase 4 voice cycle. Exposes the interface ChatPanel/VoiceOrb
// will use so wiring doesn't change later. No-ops today.
export function useSpeech() {
  return {
    supported: false,
    listening: false,
    startListening: () => {},
    stopListening: () => {},
    speak: () => {},
  }
}
