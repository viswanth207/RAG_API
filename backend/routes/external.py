from fastapi import APIRouter, Depends, HTTPException, status, Header, BackgroundTasks
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

# Managers are lazily imported from backend.main to ensure API keys are loaded

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
        
    return {"api_key": client_id}


@router.post("/register", status_code=201)
async def register_api_client(request: ExternalClientAuth):
    """Register a new external API client. In production, this should be admin-only or restricted."""
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


def background_indexing_job(db_url: str, db_name: str, index_path: str, virtual_assistant_id: str):
    """Synchronous background job to load data and build Pinecone index without blocking the event loop."""
    indexing_flag = f"{index_path}.indexing"
    try:
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        open(indexing_flag, 'w').close()
        
        logger.info(f"⏳ BACKGROUND JOB: Starting indexing for {db_name} at {index_path}")
        
        if db_url and db_url.startswith("postgres"):
            documents = DataLoader.load_from_postgres(db_url, table_names=None)
        else:
            # Limit 0 means NO LIMIT - Process the entire massive database!
            documents = DataLoader.load_from_mongodb(db_name=db_name, mongo_url=db_url, limit_per_collection=0)
            
        if documents:
            from backend.main import vector_store_manager
            vector_store_manager.create_vector_store(documents, namespace=virtual_assistant_id)
            
            # Calculate EXACT counts per collection for the AI to use later
            counts = {}
            for doc in documents:
                source = doc.metadata.get('source', '')
                if source:
                    coll = source.split('/')[-1]
                    counts[coll] = counts.get(coll, 0) + 1
            
            with open(f"{index_path}.stats.json", 'w') as f:
                json.dump(counts, f)
                
            open(f"{index_path}.pinecone_indexed", 'w').close()
            logger.info(f"✅ BACKGROUND JOB: Successfully saved index and stats ({counts}) to Pinecone")
        else:
            logger.warning(f"⚠️ BACKGROUND JOB: No documents found for {db_name}")
            
    except Exception as e:
        import traceback
        logger.error(f"🚨 BACKGROUND JOB FAILED: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        if os.path.exists(indexing_flag):
            os.remove(indexing_flag)


@router.post("/chat/stream")
async def external_chat_stream(
    request: ExternalChatRequest,
    background_tasks: BackgroundTasks,
    client: dict = Depends(get_current_api_client)
):
    """
    Stream a chat response using a dynamically loaded database context (MongoDB or PostgreSQL).
    Requires a valid Bearer token.
    """
    try:
        api_key = client["api_key"]
        db_name = request.database_name or "vtfinal"
        
        # Verify target database
        if not db_name:
            raise HTTPException(400, "Target database name is required")
            
        target_url = request.database_url or os.getenv("MONGODB_URL") or "mongodb://127.0.0.1:27017"
            
        # Check usage limits
        client_data = await crud.get_api_client_by_key(api_key)
        if client_data:
            usage_count = client_data.get("usage_count", 0)
            usage_limit = client_data.get("usage_limit", 100)
            
            if usage_count >= usage_limit:
                raise HTTPException(
                    status_code=429, 
                    detail={"error": "API Limit Reached", "msg": f"You have reached your limit of {usage_limit} queries."}
                )
            
        # Increment usage count
        await crud.increment_api_client_usage(api_key, db_name, target_url)
        
        virtual_assistant_id = f"ext_{api_key}_{db_name}"
        
        # Use an absolute path inside the project folder for persistence
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        index_dir = os.path.join(base_dir, "vector_stores", virtual_assistant_id)
        indexing_flag = f"{index_dir}.indexing"
        
        if os.path.exists(indexing_flag):
            async def indexing_generator():
                yield json.dumps({"type": "content", "data": "⏳ **System Status:** I am currently analyzing and indexing your massive database in the background! This process takes a few minutes depending on the size of your data. Please check back shortly!"}) + "\n"
            return EventSourceResponse(indexing_generator())
            
        elif os.path.exists(f"{index_dir}.pinecone_indexed"):
            from backend.main import vector_store_manager, assistant_engine
            logger.info(f"⚡ INSTANT LOAD: Found pre-computed Pinecone Vector DB for namespace {virtual_assistant_id}")
            vector_store = vector_store_manager.load_vector_store(namespace=virtual_assistant_id)
            
            # Load the pre-calculated Ground Truth statistics
            db_stats = {}
            stats_path = f"{index_dir}.stats.json"
            if os.path.exists(stats_path):
                with open(stats_path, 'r') as f:
                    db_stats = json.load(f)
            
            stats_summary = ", ".join([f"{k}: {v} records" for k, v in db_stats.items()])
            
            assistant_config = {
                "assistant_id": virtual_assistant_id,
                "name": f"External {db_name} Assistant",
                "vector_store": vector_store,
                "system_instructions": f"You are a helpful AI assistant. IMPORTANT DATABASE STATS: The database contains the following totals: {stats_summary}. If the user asks for total counts, ALWAYS use these numbers. Do NOT rely on the search results for counting.",
                "documents_count": sum(db_stats.values()) if db_stats else "Unknown",
                "created_at": str(datetime.now()),
                "enable_statistics": True,
                "enable_alerts": False,
                "enable_recommendations": True
            }
            
            async def external_generator():
                async for chunk in assistant_engine.chat_stream(
                    assistant_config=assistant_config,
                    user_message=request.message
                ):
                    yield chunk
            return EventSourceResponse(external_generator())
            
        else:
            logger.info(f"🚀 KICKOFF: Starting background job for new DB: {db_name}")
            background_tasks.add_task(background_indexing_job, target_url, db_name, index_dir, virtual_assistant_id)
            
            async def kicking_off_generator():
                yield json.dumps({"type": "content", "data": "🚀 **System Status:** I have successfully connected to your database! Because your data is large, I have started building your AI knowledge base in the background. Please try asking your question again in 2-3 minutes."}) + "\n"
            return EventSourceResponse(kicking_off_generator())
        
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

