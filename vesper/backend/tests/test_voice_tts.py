import pytest
from unittest.mock import patch, MagicMock
from app.voice.tts import TextToSpeechClient


def test_tts_client_creation():
    """Test that TTS client initializes with TTS URL"""
    client = TextToSpeechClient(tts_url="http://localhost:5500")
    assert client.tts_url == "http://localhost:5500"


def test_synthesize_text():
    """Test synthesizing text to speech"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.content = b'audio data'
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = TextToSpeechClient(tts_url="http://localhost:5500")
        result = client.synthesize("Hello world", output_file="output.wav")

        assert result == "output.wav"
        mock_post.assert_called_once()


def test_synthesize_with_voice():
    """Test synthesizing with specific voice"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.content = b'audio data'
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = TextToSpeechClient(tts_url="http://localhost:5500")
        result = client.synthesize("Bonjour", output_file="output.wav", voice="fr-male")

        assert result == "output.wav"


def test_synthesize_with_speed():
    """Test synthesizing with custom speed"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.content = b'audio data'
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = TextToSpeechClient(tts_url="http://localhost:5500")
        result = client.synthesize("Hello", output_file="output.wav", speed=1.5)

        assert result == "output.wav"


def test_synthesize_handles_api_error():
    """Test that synthesize handles API errors gracefully"""
    with patch('requests.post') as mock_post:
        mock_post.side_effect = Exception("TTS service unavailable")

        client = TextToSpeechClient(tts_url="http://localhost:5500")

        with pytest.raises(Exception) as exc_info:
            client.synthesize("Hello", output_file="output.wav")

        assert "TTS service unavailable" in str(exc_info.value)


def test_synthesize_returns_audio_bytes():
    """Test getting audio bytes without writing file"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.content = b'audio data bytes'
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = TextToSpeechClient(tts_url="http://localhost:5500")
        result = client.synthesize("Hello", return_bytes=True)

        assert result == b'audio data bytes'
