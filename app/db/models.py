from datetime import datetime

def user_model(user_id: int, is_premium: bool = False):
    """
    Schema for a user document.
    """
    return {
        "user_id": user_id,
        "is_premium": is_premium,
        "created_at": datetime.utcnow()
    }

def authorized_user_model(user_id: int, added_by: int):
    """
    Schema for an authorized user.
    """
    return {
        "user_id": user_id,
        "added_by": added_by,
        "created_at": datetime.utcnow()
    }

def blocked_content_model(user_id: int, file_id: str = None, text: str = None):
    """
    Schema for a blocked content document.
    """
    return {
        "user_id": user_id,
        "file_id": file_id,
        "text": text,
        "created_at": datetime.utcnow()
    }

def session_model(user_id: int, session_string: str):
    """
    Schema for a user's session string.
    """
    return {
        "user_id": user_id,
        "session_string": session_string,
        "updated_at": datetime.utcnow()
    }

def rule_model(user_id: int, source_chats: list, destination_chat: int, source_names: list, destination_name: str, forwarding_style: str = "forwarded", content_type: str = "both", enabled: bool = True):
    """
    Schema for a forwarding rule.
    """
    return {
        "user_id": user_id,
        "source_chats": source_chats,
        "destination_chat": destination_chat,
        "source_names": source_names,
        "destination_name": destination_name,
        "forwarding_style": forwarding_style, # 'new' or 'forwarded'
        "content_type": content_type, # 'media', 'text', or 'both'
        "enabled": enabled,
        "created_at": datetime.utcnow()
    }