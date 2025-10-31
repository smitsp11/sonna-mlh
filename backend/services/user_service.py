
from sqlalchemy.orm import Session
from ..models import User


def get_or_create_default_user(db: Session) -> User:
    """
    Get the default user or create one if it doesn't exist.
    
    For now, we use a single default user. In the future, this will
    be replaced with proper authentication and multi-user support.
    
    Args:
        db: Database session
        
    Returns:
        User object
    """
    DEFAULT_EMAIL = "smitpatel11@gmail.com"
    DEFAULT_NAME = "Smit Patel"
    OLD_USER_NAME = "Sonna User"
    
    # Get or create Smit Patel user
    user = db.query(User).filter(User.email == DEFAULT_EMAIL).first()
    
    if not user:
        # Check if "Sonna User" exists to migrate preferences
        old_user = db.query(User).filter(User.name == OLD_USER_NAME).first()
        initial_preferences = old_user.preferences.copy() if old_user and old_user.preferences else {}
        
        # Create Smit Patel user
        user = User(
            name=DEFAULT_NAME,
            email=DEFAULT_EMAIL,
            preferences=initial_preferences
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Delete old "Sonna User" after migration
        if old_user:
            db.delete(old_user)
            db.commit()
    else:
        # User exists, check if preferences need migration
        if not user.preferences or len(user.preferences) == 0:
            old_user = db.query(User).filter(User.name == OLD_USER_NAME).first()
            if old_user and old_user.preferences and len(old_user.preferences) > 0:
                # Migrate preferences from Sonna User
                user.preferences = old_user.preferences.copy()
                db.commit()
                db.refresh(user)
                
                # Delete old user after migration
                db.delete(old_user)
                db.commit()
    
    # Ensure name is correct
    if user.name != DEFAULT_NAME:
        user.name = DEFAULT_NAME
        db.commit()
        db.refresh(user)
    
    return user

