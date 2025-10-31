# Sonna

A voice-first personal assistant backend that processes speech input, generates contextual AI responses using conversation history and user preferences, and returns synthesized speech output.

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

## Environment / API Keys

This project requires:
- `GEMINI_API_KEY` - Google Gemini API for LLM responses
- `DATABASE_URL` - PostgreSQL connection string (Supabase)

See `.env.example` for template. Keys are loaded via `pydantic-settings` with `python-dotenv` fallback.
