
import io
import os
import tempfile
import logging
from pathlib import Path
from typing import Optional
from io import BytesIO
from datetime import datetime
import pytz

import google.generativeai as genai
from fastapi import APIRouter, UploadFile, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..routers.voice import transcribe_audio
from ..routers.tts import generate_tts, TTSRequest as TTSRequestModel
from ..config import settings
from ..database import get_db
from ..services.user_service import get_or_create_default_user
from ..services.conversation_service import (
    get_or_create_active_conversation,
    add_message,
    get_conversation_context,
    generate_conversation_title
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversation")

# Constants
DEFAULT_TIMEZONE = "America/Toronto"
GEMINI_MODEL = "gemini-2.5-flash"  # Using stable version instead of -exp

# Initialize Gemini
if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here":
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Test the connection by listing models
        try:
            list(genai.list_models())
            GEMINI_ENABLED = True
            logger.info("✅ Gemini API initialized successfully")
            logger.info(f"Using model: {GEMINI_MODEL}")
        except Exception as e:
            GEMINI_ENABLED = False
            logger.error(f"❌ Failed to verify Gemini API connection: {e}", exc_info=True)
    except Exception as e:
        GEMINI_ENABLED = False
        logger.error(f"❌ Failed to initialize Gemini API: {e}", exc_info=True)
else:
    GEMINI_ENABLED = False
    api_key_preview = settings.GEMINI_API_KEY[:20] + "..." if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 20 else (settings.GEMINI_API_KEY or "None")
    logger.warning(f"⚠️  GEMINI_API_KEY not set or invalid. Current value: {api_key_preview}")

class VoiceLoopResponse(BaseModel):
    text: str
    audio_url: str = "/conversation/voice-loop"
    conversation_id: Optional[int] = None
    message_id: Optional[int] = None

def generate_default_response() -> str:
    return "I'm sorry, I can't think right now. Please check my AI connection."


def format_user_context(user_preferences: dict) -> str:
    if not user_preferences:
        return "None specified"
    
    context_parts = []
    field_mappings = {
        "interests": "Interests",
        "favourite foods": "Favorite Foods",
        "goals": "Goals",
        "daily routine": "Daily Routine"
    }
    
    for key, label in field_mappings.items():
        value = user_preferences.get(key)
        if value and isinstance(value, list):
            context_parts.append(f"- {label}: {', '.join(value)}")
    
    return "\n".join(context_parts) if context_parts else "None specified"


def generate_gemini_response(
    user_text: str,
    conversation_context: list[dict] = None,
    user_timezone: str = DEFAULT_TIMEZONE,
    user_preferences: dict = None
) -> str:
    if not GEMINI_ENABLED:
        logger.warning("Gemini client not initialized, using default response")
        return generate_default_response()

    try:
        # Get current date/time (global knowledge, not user-specific)
        timezone = pytz.timezone(user_timezone)
        now = datetime.now(timezone)
        current_date = now.strftime("%A, %B %d, %Y")
        current_time = now.strftime("%I:%M %p")
        day_of_week = now.strftime("%A")
        
        # Format user-specific context (interests, goals, routines)
        user_context = format_user_context(user_preferences)
        
        # Build system prompt with clear separation of global vs user context
        system_prompt = f"""You are Sonna, an intelligent and caring AI voice assistant.

Global Knowledge (Current Real-Time Information):
- Date: {current_date} ({day_of_week})
- Time: {current_time}
- Location: Toronto, Ontario, Canada
- Year: 2025

User-Specific Context:
{user_context}

Instructions:
- Use the EXACT date and time from Global Knowledge when answering date/time questions
- Use the user's interests, goals, and routines to personalize responses
- Reference their preferences naturally when relevant
- Be concise and natural for voice conversation (under 2 sentences when possible)
- Be warm, helpful, and conversational"""

        # Create model
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Use conversation context if available
        limited_context = conversation_context[-5:] if conversation_context and len(conversation_context) > 5 else (conversation_context or [])
        
        # Build conversation history for Gemini
        if limited_context:
            chat_history = []
            for msg in limited_context:
                role = "user" if msg["role"] == "user" else "model"
                chat_history.append({
                    "role": role,
                    "parts": [msg["content"]]
                })
            
            # Start chat with history
            chat = model.start_chat(history=chat_history)
            logger.info(f"📚 Using conversation history with {len(limited_context)} previous messages")
        else:
            # Start chat without history
            chat = model.start_chat()
            logger.info("🆕 Starting new conversation (no history)")
        
        # Send current message with system context
        response = chat.send_message(f"{system_prompt}\n\nUser: {user_text}")
        
        # Get text response
        try:
            response_text = response.text.strip()
            if not response_text:
                logger.warning("Empty response from Gemini, using default")
                return generate_default_response()
        except (ValueError, AttributeError) as e:
            logger.error(f"Error extracting text from Gemini response: {e}", exc_info=True)
            return generate_default_response()
        
        logger.info(f"✅ Generated response for: {user_text[:50]}...")
        return response_text
        
    except Exception as e:
        logger.error(f"Gemini API error: {e}", exc_info=True)
        logger.error(f"Error type: {type(e).__name__}", exc_info=True)
        return generate_default_response()


@router.post("/voice-loop", response_model=VoiceLoopResponse)
async def voice_reasoning_loop(audio: UploadFile, db: Session = Depends(get_db)):
    
    temp_audio_path = None
    conversation_id = None
    message_id = None

    try:
        # Get or create user
        user = get_or_create_default_user(db)
        logger.info(f"👤 Using user: {user.name} (ID: {user.id})")
        
        # Get or create active conversation
        conversation = get_or_create_active_conversation(db, user.id)
        conversation_id = conversation.id
        logger.info(f"💬 Using conversation ID: {conversation_id}")
        
        # Get conversation context (last 10 messages)
        context = get_conversation_context(db, conversation_id, limit=10)
        logger.info(f"📚 Loaded {len(context)} previous messages for context")
        
        # Step 1: Save uploaded audio temporarily
        suffix = Path(audio.filename or "audio.m4a").suffix or ".m4a"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            contents = await audio.read()
            tmp.write(contents)
            temp_audio_path = tmp.name

        logger.info(f"💾 Temporary audio saved to {temp_audio_path}")

        # Build UploadFile for transcription
        audio_data = open(temp_audio_path, "rb").read()
        mock_upload = UploadFile(filename=Path(temp_audio_path).name, file=BytesIO(audio_data))
        mock_upload.__dict__["content_type"] = "audio/m4a"
        
        # Step 2: Transcribe audio to text
        transcription = await transcribe_audio(mock_upload)
        user_text = transcription.get("text", "").strip()

        if not user_text:
            user_text = "I couldn't catch that. Could you please repeat?"
            logger.warning("⚠️  No speech detected in audio")
            response_text = user_text
        else:
            logger.info(f"📝 Transcribed: {user_text[:100]}...")
            
            # Save user message to database
            user_message = add_message(
                db=db,
                conversation_id=conversation_id,
                role="user",
                content=user_text,
                audio_file_path=None,
                metadata={"source": "voice"}
            )
            logger.info(f"💾 Saved user message ID: {user_message.id}")
            
            # Generate title from first message
            if len(context) == 0:
                generate_conversation_title(db, conversation_id, user_text)
            
            # Step 3: Generate response via Gemini with conversation context and user preferences
            user_timezone = user.preferences.get("timezone", DEFAULT_TIMEZONE)
            response_text = generate_gemini_response(
                user_text=user_text,
                conversation_context=context,
                user_timezone=user_timezone,
                user_preferences=user.preferences
            )
            
            # Save assistant response to database
            assistant_message = add_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=response_text,
                metadata={"model": GEMINI_MODEL}
            )
            message_id = assistant_message.id
            logger.info(f"💾 Saved assistant message ID: {message_id}")

        # Step 4: Generate TTS audio from response
        logger.info("🔊 Generating TTS audio from response...")
        tts_request = TTSRequestModel(text=response_text)
        tts_response = await generate_tts(tts_request)

        # Step 5: Prepare response headers
        response_headers = {
            "X-Conversation-ID": str(conversation_id) if conversation_id else "",
            "X-Message-ID": str(message_id) if message_id else "",
            "X-Transcribed-Text": user_text[:500],
            "X-Response-Text": response_text[:500],
        }

        # Return audio response
        if isinstance(tts_response, StreamingResponse):
            tts_response.headers.update(response_headers)
            return tts_response

        # Fallback to gTTS
        from gtts import gTTS
        tts = gTTS(text=response_text, lang="en")
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        
        response_headers["Content-Disposition"] = "attachment; filename=sonna_response.mp3"

        return StreamingResponse(
            buffer,
            media_type="audio/mpeg",
            headers=response_headers,
        )

    except Exception as e:
        logger.error(f"❌ Voice reasoning loop failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice processing failed: {e}",
        )

    finally:
        # Clean up temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
                logger.debug(f"🧹 Cleaned up temp file: {temp_audio_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {temp_audio_path}: {e}")
