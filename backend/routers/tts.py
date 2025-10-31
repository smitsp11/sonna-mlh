
import io
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from gtts import gTTS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tts", tags=["tts"])


class TTSRequest(BaseModel):
    text: str


@router.post("/speak")
async def generate_tts(req: TTSRequest):
    """
    Convert text into audio speech using gTTS (Google Text-to-Speech).
    
    Args:
        req: TTSRequest containing the text to convert
        
    Returns:
        StreamingResponse with MP3 audio file
    """
    try:
        logger.info(f"Generating TTS audio for text: {req.text[:50]}...")
        
        # Generate speech using gTTS
        tts = gTTS(text=req.text, lang="en")
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        audio_bytes = buffer.read()

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=sonna_output.mp3",
                "Accept-Ranges": "bytes"
            }
        )

    except Exception as e:
        logger.exception("TTS generation failed")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {e}")

