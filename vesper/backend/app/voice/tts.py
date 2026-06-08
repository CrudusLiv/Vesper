import requests
import logging
from typing import Union

logger = logging.getLogger(__name__)


class TextToSpeechClient:
    """Client for TTS service (Piper)"""

    def __init__(self, tts_url: str = "http://tts:5500"):
        self.tts_url = tts_url

    def synthesize(
        self,
        text: str,
        output_file: str = None,
        voice: str = None,
        speed: float = 1.0,
        return_bytes: bool = False
    ) -> Union[str, bytes]:
        """
        Synthesize text to speech.

        Args:
            text: Text to synthesize
            output_file: Path to save audio file (optional)
            voice: Voice model to use (e.g., 'en-us-default', 'fr-male')
            speed: Speech speed (1.0 = normal)
            return_bytes: If True, return audio bytes instead of saving file

        Returns:
            Path to output file, or audio bytes if return_bytes=True
        """
        try:
            data = {
                "text": text,
            }
            if voice:
                data["voice"] = voice
            if speed != 1.0:
                data["speed"] = speed

            response = requests.post(
                f"{self.tts_url}/synthesize",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            audio_bytes = response.content

            if return_bytes:
                return audio_bytes

            if output_file:
                with open(output_file, 'wb') as f:
                    f.write(audio_bytes)
                return output_file

            return audio_bytes

        except Exception as e:
            logger.error(f"Text-to-speech synthesis failed: {str(e)}", exc_info=True)
            raise
