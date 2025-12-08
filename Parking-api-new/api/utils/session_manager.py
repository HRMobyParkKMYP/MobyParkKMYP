"""
Session management utility for handling user sessions
"""

sessions = {}


def add_session(token: str, user: dict) -> None:
    """
    Add a new session for a user
    
    Args:
        token: Session token (UUID)
        user: User data dictionary
    """
    sessions[token] = user


def remove_session(token: str) -> dict:
    """
    Remove a session and return the user data
    
    Args:
        token: Session token to remove
        
    Returns:
        User data if session existed, None otherwise
    """
    return sessions.pop(token, None)


def get_session(token: str) -> dict:
    """
    Get user data for a session token
    
    Args:
        token: Session token to lookup
        
    Returns:
        User data if session exists, None otherwise
    """
    return sessions.get(token)
