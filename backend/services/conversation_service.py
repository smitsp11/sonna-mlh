
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models import Conversation, Message, User


def get_or_create_active_conversation(db: Session, user_id: int) -> Conversation:
    """
    Get the user's most recent active conversation or create a new one.
    
    A conversation is considered "active" if it was updated in the last 2 hours.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Conversation object
    """
    # Check for recent conversation (within last 2 hours)
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)
    
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.user_id == user_id,
            Conversation.updated_at >= two_hours_ago
        )
        .order_by(desc(Conversation.updated_at))
        .first()
    )
    
    if not conversation:
        # Create new conversation
        conversation = Conversation(
            user_id=user_id,
            title=f"Conversation at {datetime.utcnow().strftime('%I:%M %p')}",
            extra_data={"source": "voice"}
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    return conversation


def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
    audio_file_path: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Message:
    """
    Add a message to a conversation.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        role: Message role ('user', 'assistant', 'system')
        content: Message content
        audio_file_path: Optional path to audio file
        metadata: Optional metadata dictionary
        
    Returns:
        Created Message object
    """
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        audio_file_path=audio_file_path,
        extra_data=metadata or {}
    )
    
    db.add(message)
    
    # Update conversation's updated_at timestamp
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    
    return message


def get_conversation_context(
    db: Session,
    conversation_id: int,
    limit: int = 10
) -> List[Dict[str, str]]:
    """
    Get recent messages from a conversation for context.
    
    Returns messages in format suitable for Gemini API:
    [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        limit: Maximum number of messages to retrieve
        
    Returns:
        List of message dictionaries
    """
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(desc(Message.created_at))
        .limit(limit)
        .all()
    )
    
    # Reverse to get chronological order
    messages = list(reversed(messages))
    
    # Format for Gemini
    context = []
    for msg in messages:
        context.append({
            "role": msg.role,
            "content": msg.content
        })
    
    return context


def generate_conversation_title(db: Session, conversation_id: int, first_message: str) -> None:
    """
    Generate a title for the conversation based on the first user message.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        first_message: First user message content
    """
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    if conversation and conversation.title.startswith("Conversation at"):
        # Generate title from first message (first 50 chars)
        title = first_message[:50]
        if len(first_message) > 50:
            title += "..."
        
        conversation.title = title
        db.commit()

