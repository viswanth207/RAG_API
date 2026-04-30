from backend.database.mongodb import get_database
from backend.database.models import UserCreate, UserInDB, AssistantInDB, ChatHistoryInDB
from datetime import datetime
from bson import ObjectId
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


# User CRUD
async def create_user(user: UserCreate, password_hash: str) -> UserInDB:
    """Create a new user in the database"""
    db = get_database()
    
    user_doc = {
        "email": user.email,
        "password_hash": password_hash,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = str(result.inserted_id)
    
    return UserInDB(**user_doc)


async def get_user_by_email(email: str) -> Optional[UserInDB]:
    """Get user by email"""
    db = get_database()
    user_doc = await db.users.find_one({"email": email})
    
    if user_doc:
        user_doc["_id"] = str(user_doc["_id"])
        return UserInDB(**user_doc)
    return None


async def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    """Get user by ID"""
    db = get_database()
    user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    
    if user_doc:
        user_doc["_id"] = str(user_doc["_id"])
        return UserInDB(**user_doc)
    return None


# Assistant CRUD
async def create_assistant(assistant_data: dict) -> AssistantInDB:
    """Create a new assistant in the database"""
    db = get_database()
    
    assistant_doc = {
        **assistant_data,
        "created_at": datetime.utcnow()
    }
    
    result = await db.assistants.insert_one(assistant_doc)
    assistant_doc["_id"] = str(result.inserted_id)
    
    return AssistantInDB(**assistant_doc)


async def get_assistant_by_id(assistant_id: str, user_id: str) -> Optional[AssistantInDB]:
    """Get assistant by ID and verify ownership"""
    db = get_database()
    assistant_doc = await db.assistants.find_one({
        "assistant_id": assistant_id,
        "user_id": user_id
    })
    
    if assistant_doc:
        assistant_doc["_id"] = str(assistant_doc["_id"])
        return AssistantInDB(**assistant_doc)
    return None


async def get_user_assistants(user_id: str) -> List[AssistantInDB]:
    """Get all assistants for a user"""
    db = get_database()
    cursor = db.assistants.find({"user_id": user_id}).sort("created_at", -1)
    
    assistants = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        assistants.append(AssistantInDB(**doc))
    
    return assistants


async def delete_assistant(assistant_id: str, user_id: str) -> bool:
    """Delete an assistant"""
    db = get_database()
    result = await db.assistants.delete_one({
        "assistant_id": assistant_id,
        "user_id": user_id
    })
    return result.deleted_count > 0


# Chat History CRUD
async def save_chat_message(user_id: str, assistant_id: str, role: str, content: str):
    """Save a chat message to history"""
    db = get_database()
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow()
    }
    
    # Update or insert chat history
    await db.chat_history.update_one(
        {"user_id": user_id, "assistant_id": assistant_id},
        {
            "$push": {"messages": message},
            "$set": {"updated_at": datetime.utcnow()},
            "$setOnInsert": {"created_at": datetime.utcnow()}
        },
        upsert=True
    )


async def get_chat_history(user_id: str, assistant_id: str, limit: int = 50) -> List[dict]:
    """Get chat history for an assistant"""
    db = get_database()
    
    chat_doc = await db.chat_history.find_one(
        {"user_id": user_id, "assistant_id": assistant_id}
    )
    
    if chat_doc and "messages" in chat_doc:
        # Return last N messages
        return chat_doc["messages"][-limit:]
    return []

# External API Client CRUD
async def create_api_client(client_data: dict) -> dict:
    """Create a new external API client identity in the database"""
    db = get_database()
    
    client_doc = {
        **client_data,
        "created_at": datetime.utcnow(),
        "usage_count": 0,
        "usage_limit": 100
    }
    
    result = await db.api_clients.insert_one(client_doc)
    client_doc["_id"] = str(result.inserted_id)
    return client_doc

async def get_api_client_by_key(api_key: str) -> Optional[dict]:
    """Get an API client config securely by its public api key"""
    db = get_database()
    client_doc = await db.api_clients.find_one({"api_key": api_key})
    
    if client_doc:
        client_doc["_id"] = str(client_doc["_id"])
        return client_doc
    return None

async def increment_api_client_usage(api_key: str, target_db: str, target_url: str):
    """Increment the client's usage count and log their latest target info."""
    db = get_database()
    await db.api_clients.update_one(
        {"api_key": api_key},
        {
            "$inc": {"usage_count": 1},
            "$set": {
                "last_target_db": target_db,
                "last_target_url": target_url,
                "updated_at": datetime.utcnow()
            }
        }
    )

async def save_api_audit_log(log_data: dict):
    """Save an API audit log entry to the database"""
    db = get_database()
    await db.api_audit_logs.insert_one(log_data)

