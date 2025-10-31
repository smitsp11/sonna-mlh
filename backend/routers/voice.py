
import os
import logging
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, HTTPException, status
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])

# Initialize local Whisper model
# "small" balances speed and accuracy for most use cases
try:
    model = WhisperModel("small", compute_type="int8")
    logger.info("✅ Faster-Whisper model initialized successfully")
except Exception as e:
    logger.exception("Failed to initialize Whisper model")
    raise RuntimeError(f"Failed to load Faster-Whisper model: {e}")


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile):
    """
    Transcribe audio file (m4a) to text using local Faster-Whisper model.
    
    Args:
        audio: Audio file upload (expected format: m4a)
        
    Returns:
        dict: {"text": "<transcribed text>"}
    """
    tmp_path = None
    try:
        # Validate that it's an audio file
        content_type = audio.content_type or ""
        if content_type and not content_type.startswith("audio/"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Audio file not allowed. Please upload a valid audio file."
            )
        
        # Save uploaded audio to temporary file
        suffix = Path(audio.filename or "audio.m4a").suffix or ".m4a"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            data = await audio.read()
            tmp.write(data)
            tmp_path = tmp.name
        
        logger.info(f"Transcribing audio file: {audio.filename}")
        
        # Perform transcription (English only)
        segments, info = model.transcribe(tmp_path, language="en", vad_filter=True)
        text = " ".join(seg.text.strip() for seg in segments)
        
        logger.info(f"Transcription complete: {len(text)} characters")
        
        return {"text": text}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Transcription failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {e}"
        )
    finally:
        # Clean up temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                logger.warning(f"Failed to clean up temp file: {tmp_path}")
