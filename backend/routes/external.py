from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Optional, Dict
import os
import secrets
from backend.models import ExternalClientAuth, ExternalTokenResponse, ExternalChatRequest
from backend.auth.utils import verify_password, get_password_hash, create_access_token, decode_access_token
from backend.database import crud
from backend.data_loader import DataLoader
from backend.vector_store import VectorStoreManager
from backend.assistant_engine import AssistantEngine
import logging
from sse_starlette.sse import EventSourceResponse
import json
from datetime import datetime

router = APIRouter(prefix="/api/v1/external", tags=["External API"])
logger = logging.getLogger(__name__)


async def get_current_api_client(authorization: Optional[str] = Header(None)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate external API credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_exception
        
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    client_id = payload.get("sub")
    client_type = payload.get("type")
    
    if client_id is None or client_type != "external_api":
        raise credentials_exception
        
    # We could fetch the client from DB here if we need up-to-date permissions
    # client = await crud.get_api_client_by_key(client_id)
    # if not client: raise credentials_exception
    
    return {"api_key": client_id}


@router.post("/register", status_code=201)
async def register_api_client(request: ExternalClientAuth):
    """Register a new external API client. In production, this should be admin-only or restricted."""
    # Check if exists
    existing = await crud.get_api_client_by_key(request.api_key)
    if existing:
        raise HTTPException(status_code=400, detail="API Key already registered")
        
    hashed_password = get_password_hash(request.password)
    
    client_data = {
        "api_key": request.api_key,
        "password_hash": hashed_password
    }
    await crud.create_api_client(client_data)
    
    return {"message": "External API Client registered successfully"}


@router.post("/auth/token", response_model=ExternalTokenResponse)
async def login_for_access_token(request: ExternalClientAuth):
    """Exchange API Key and Password for a JWT Access Token"""
    client = await crud.get_api_client_by_key(request.api_key)
    if not client or not verify_password(request.password, client["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect API Key or password",
        )
        
    access_token = create_access_token(
        data={"sub": client["api_key"], "type": "external_api"}
    )
    logger.info(f"🔑 AUTH SUCCESS: Token generated for API Key: {request.api_key}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/chat/stream")
async def external_chat_stream(
    request: ExternalChatRequest,
    client: dict = Depends(get_current_api_client)
):
    """
    Stream a chat response using a dynamically loaded database context (MongoDB or PostgreSQL).
    Requires a valid Bearer token.
    """
    try:
        from backend.main import vector_store_manager, assistant_engine
        
        api_key = client["api_key"]
        db_name = request.database_name
        
        # Create a unique virtual assistant ID for this client + database combo
        virtual_assistant_id = f"ext_{api_key}_{db_name}"
        logger.info(f"Incoming external request from [{api_key}]. Action: Chat with [{db_name}]")
        
        # Load fresh data from the requested database every time for 100% accuracy
        documents = []
        db_url = request.database_url
        
        if db_url and db_url.startswith("postgres"):
            # PostgreSQL Data Loading
            documents = DataLoader.load_from_postgres(db_url, table_names=None)
        else:
            # Load all available data from the requested MongoDB database using the PROVIDED URL
            target_url = request.database_url or os.getenv("MONGODB_URL") or "mongodb://127.0.0.1:27017"
            logger.info(f"🚨 FRESH SCAN: TARGETING DATABASE: {db_name} AT URL: {target_url}")
            documents = DataLoader.load_from_mongodb(db_name=db_name, mongo_url=target_url)
            logger.info(f"Reloaded {len(documents)} updated docs from MongoDB: {db_name}")
            
        if documents:
            vector_store = vector_store_manager.create_vector_store(documents)
            # We skip saving to disk here to keep it in-memory for current data
            
            assistant_config = {
                "assistant_id": virtual_assistant_id,
                "name": f"External {db_name} Assistant",
                "vector_store": vector_store,
                "system_instructions": "You are a helpful AI assistant integrated securely into a client website. Analyze the provided database records and answer clearly.",
                "documents_count": len(documents),
                "created_at": str(datetime.now()),
                "enable_statistics": True,
                "enable_alerts": False,
                "enable_recommendations": True
            }
        else:
            raise HTTPException(400, "No data could be loaded from the specified database")
        
        async def external_generator():
            async for chunk in assistant_engine.chat_stream(
                assistant_config=assistant_config,
                user_message=request.message
            ):
                yield chunk
                
        return EventSourceResponse(external_generator())
        
    except Exception as e:
        import traceback
        logger.error(f"🚨 EXTERNAL API ERROR: {str(e)}")
        logger.error(traceback.format_exc())
        
        # If it's a data loading error, it's a 400 (Bad Request), not a server crash
        status_code = 400 if isinstance(e, ValueError) else 500
        
        error_detail = {
            "error": str(e),
            "type": type(e).__name__,
            "msg": "The AI core encountered a data sync error. Check your database configuration."
        }
        raise HTTPException(status_code=status_code, detail=error_detail)

