import os


class Config:
    # Ollama settings
    # Use localhost for local dev, ollama for Docker
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

    # Whisper settings (Phase 4)
    WHISPER_URL = os.getenv("WHISPER_URL", "http://whisper:9000")

    # TTS settings (Phase 4)
    TTS_URL = os.getenv("TTS_URL", "http://tts:5500")

    # Vault
    VAULT_PATH = os.getenv("VAULT_PATH", "/workspace/Dynamous/Memory")


config = Config()
