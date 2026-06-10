import os


class Config:
    # Anthropic settings
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
    ANTHROPIC_TIMEOUT = int(os.getenv("ANTHROPIC_TIMEOUT", "120"))

    # Whisper settings (Phase 4)
    WHISPER_URL = os.getenv("WHISPER_URL", "http://whisper:9000")

    # TTS settings (Phase 4)
    TTS_URL = os.getenv("TTS_URL", "http://tts:5500")

    # Vault
    VAULT_PATH = os.getenv("VAULT_PATH", "/workspace/Dynamous/Memory")


config = Config()
