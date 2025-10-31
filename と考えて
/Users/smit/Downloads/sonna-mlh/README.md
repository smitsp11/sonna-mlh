# Sonna

A voice-first personal assistant backend that processes speech input, generates contextual AI responses using conversation history and user preferences, and returns synthesized speech output.

## What This Project Does

- Transcribes audio input (m4a) to text using local Faster-Whisper model
- Generates personalized responses via Google Gemini API with conversation context and user preferences
- Stores conversation history and user profiles in Supabase (PostgreSQL)
- Returns text-to-speech audio output using gTTS

## Why This Project Matters

Enables natural voice conversations with an AI assistant that remembers past interactions and user-specific information (interests, goals, routines) across sessions.

## My Contribution

- Built FastAPI backend architecture with SQLAlchemy ORM models and service layer separation
- Designed `/conversation/voice-loop` endpoint orchestrating transcription → LLM reasoning → TTS pipeline
- Integrated Supabase for persistent storage of conversations, messages, and user preferences
- Implemented conversation context retrieval (last 10 messages) and user preference formatting for LLM prompts
- Engineered user preference migration logic to consolidate duplicate database entries

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI, Uvicorn |
| Database | PostgreSQL (Supabase), SQLAlchemy ORM |
| AI/ML | Google Gemini API, Faster-Whisper (local), gTTS |
| Config | pydantic-settings, python-dotenv |

## Key Files

```
backend/
├── app.py                    # FastAPI app entry, CORS, database init
├── routers/
│   ├── conversation.py       # Main voice-loop endpoint, Gemini integration
│   ├── voice.py             # Speech-to-text (Faster-Whisper)
│   └── tts.py               # Text-to-speech (gTTS)
├── services/
│   ├── conversation_service.py  # Conversation context, message storage
│   └── user_service.py          # User retrieval/preference management
├── models.py                # SQLAlchemy models (User, Conversation, Message)
└── database.py              # SQLAlchemy engine, session management
```

## How to Run

```bash
git clone <repo>
cd sonna-mlh
pip install -r backend/requirements.txt
cp .env.example .env  # Add GEMINI_API_KEY and DATABASE_URL
uvicorn backend.app:app --reload
```

## Example Usage

```bash
curl -X POST "http://localhost:8000/conversation/voice-loop" \
  -F "audio=@input.m4a" \
  --output response.mp3
```

**Output**: Returns MP3 audio of AI response with conversation context headers (`X-Conversation-ID`, `X-Response-Text`)

## What I Learned

- Separated global knowledge (date/time) from user-specific context in LLM prompts to reduce redundancy
- Implemented conversation context windowing (last 5-10 messages) to balance memory with API token limits
- Designed database schema with cascade deletes and JSON columns for flexible user preferences storage
- Handled race conditions in user creation with preference migration logic
- Optimized system prompts to include real-time context (timezone-aware date/time) while keeping user data scoped

## Environment / API Keys

This project requires:
- `GEMINI_API_KEY` - Google Gemini API for LLM responses
- `DATABASE_URL` - PostgreSQL connection string (Supabase)

See `.env.example` for template. Keys are loaded via `pydantic-settings` with `python-dotenv` fallback.

