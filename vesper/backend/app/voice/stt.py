import requests
import logging

logger = logging.getLogger(__name__)


class SpeechToTextClient:
    """Client for Whisper speech-to-text service"""

    def __init__(self, whisper_url: str = "http://whisper:9000"):
        self.whisper_url = whisper_url

    def transcribe(self, audio_file_path: str, language: str = None) -> str:
        """
        Transcribe audio file to text using Whisper.

        Args:
            audio_file_path: Path to audio file
            language: Optional language code (e.g., 'en', 'fr')

        Returns:
            Transcribed text
        """
        try:
            with open(audio_file_path, 'rb') as audio_file:
                files = {'audio': audio_file}
                data = {}
                if language:
                    data['language'] = language

                response = requests.post(
                    f"{self.whisper_url}/transcribe",
                    files=files,
                    data=data,
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
                return result.get('text', '')
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}", exc_info=True)
            raise
