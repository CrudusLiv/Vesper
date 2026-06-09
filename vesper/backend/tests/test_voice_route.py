import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app import deps

client = TestClient(app)


@pytest.fixture(autouse=True)
def _override_auth():
    app.dependency_overrides[deps.require_auth] = lambda: None
    yield
    app.dependency_overrides.pop(deps.require_auth, None)


def test_voice_chat_endpoint_exists():
    """Test that voice chat endpoint exists"""
    response = client.post("/api/chat/voice", json={})
    # Should return something (404 if endpoint doesn't exist)
    assert response.status_code != 404


@patch('app.voice.stt.SpeechToTextClient.transcribe')
@patch('app.agent.loop.AgentLoop.process')
@patch('app.voice.tts.TextToSpeechClient.synthesize')
def test_voice_chat_with_audio(mock_tts, mock_agent, mock_transcribe):
    """Test sending audio, receiving response with audio"""
    # Setup mocks
    mock_transcribe.return_value = "Remember to call mom"
    mock_agent.return_value = MagicMock(
        response="I'll remind you to call your mom",
        tool_calls=[],
        tool_results=[]
    )
    mock_tts.return_value = b'audio bytes'

    with patch('builtins.open', create=True):
        response = client.post(
            "/api/chat/voice",
            json={"audio_file": "test.wav"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "response_text" in data
    assert "audio" in data


@patch('app.voice.tts.TextToSpeechClient.synthesize')
@patch('app.agent.loop.AgentLoop.process')
def test_voice_chat_transcribe_text(mock_agent, mock_tts):
    """Test that voice chat endpoint handles text input"""
    mock_agent.return_value = MagicMock(
        response="Got it",
        tool_calls=[],
        tool_results=[]
    )
    mock_tts.return_value = b'audio bytes'

    response = client.post(
        "/api/chat/voice",
        json={"text": "What's the weather?"},
    )

    assert response.status_code == 200


@patch('app.voice.stt.SpeechToTextClient.transcribe')
def test_voice_chat_transcription_error(mock_transcribe):
    """Test handling transcription errors"""
    mock_transcribe.side_effect = Exception("Whisper error")

    with patch('builtins.open', create=True):
        response = client.post(
            "/api/chat/voice",
            json={"audio_file": "test.wav"},
        )

    assert response.status_code == 500
