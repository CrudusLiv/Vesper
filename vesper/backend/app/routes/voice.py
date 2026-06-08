from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import logging

from ..agent.loop import AgentLoop
from ..agent.models import AgentRequest
from ..voice.stt import SpeechToTextClient
from ..voice.tts import TextToSpeechClient
from ..config import config
from ..deps import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()


class VoiceChatRequest(BaseModel):
    text: Optional[str] = None
    audio_file: Optional[str] = None
    voice_output: bool = True


class VoiceChatResponse(BaseModel):
    response_text: str
    audio: Optional[bytes] = None
    tool_calls: list = []
    tool_results: list = []


@router.post("/voice")
def voice_chat(req: VoiceChatRequest, _: None = Depends(require_auth)):
    """
    Process voice or text input and return response with optional voice output.

    Supports:
    - Text input: send `text` in request
    - Audio input: send `audio_file` path in request
    - Voice output: set `voice_output=true` to get audio response
    """
    try:
        user_input = None

        if req.text:
            user_input = req.text
        elif req.audio_file:
            stt = SpeechToTextClient(whisper_url=config.WHISPER_URL)
            user_input = stt.transcribe(req.audio_file)

        if not user_input:
            raise HTTPException(status_code=400, detail="No input provided (text or audio_file required)")

        agent = AgentLoop()
        agent_req = AgentRequest(
            input=user_input,
            input_type="voice" if req.audio_file else "text"
        )
        agent_response = agent.process(agent_req)

        response_data = {
            "response_text": agent_response.response,
            "tool_calls": [tc.model_dump() for tc in agent_response.tool_calls],
            "tool_results": agent_response.tool_results
        }

        if req.voice_output:
            tts = TextToSpeechClient(tts_url=config.TTS_URL)
            audio_bytes = tts.synthesize(
                agent_response.response,
                return_bytes=True
            )
            response_data["audio"] = audio_bytes

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice chat failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
