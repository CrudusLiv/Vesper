import pytest
from unittest.mock import Mock, patch, MagicMock
from app.voice.stt import SpeechToTextClient


@pytest.fixture
def mock_whisper_response():
    """Mock Whisper API response"""
    return {
        "text": "Remember to call mom tomorrow",
    }


def test_stt_client_creation():
    """Test that STT client initializes with Whisper URL"""
    client = SpeechToTextClient(whisper_url="http://localhost:9000")
    assert client.whisper_url == "http://localhost:9000"


def test_transcribe_audio_file():
    """Test transcribing an audio file"""
    with patch('builtins.open', create=True):
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "text": "Remember to call mom"
            }
            mock_post.return_value.status_code = 200

            client = SpeechToTextClient(whisper_url="http://localhost:9000")
            result = client.transcribe("test_audio.wav")

            assert result == "Remember to call mom"
            mock_post.assert_called_once()


def test_transcribe_with_language():
    """Test transcribing with specific language parameter"""
    with patch('builtins.open', create=True):
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "text": "Bonjour le monde"
            }
            mock_post.return_value.status_code = 200

            client = SpeechToTextClient(whisper_url="http://localhost:9000")
            result = client.transcribe("test_audio.wav", language="fr")

            assert result == "Bonjour le monde"


def test_transcribe_handles_api_error():
    """Test that transcribe handles API errors gracefully"""
    with patch('builtins.open', create=True):
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Connection failed")

            client = SpeechToTextClient(whisper_url="http://localhost:9000")

            with pytest.raises(Exception) as exc_info:
                client.transcribe("test_audio.wav")

            assert "Connection failed" in str(exc_info.value)


def test_transcribe_empty_audio():
    """Test that empty audio returns empty string"""
    with patch('builtins.open', create=True):
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "text": ""
            }
            mock_post.return_value.status_code = 200

            client = SpeechToTextClient(whisper_url="http://localhost:9000")
            result = client.transcribe("empty_audio.wav")

            assert result == ""
