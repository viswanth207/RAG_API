
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict, Optional
import uuid
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")
logging.getLogger("httpx").setLevel(logging.INFO)
logging.getLogger("backend").setLevel(logging.INFO)

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from dotenv import load_dotenv
import shutil
from sse_starlette.sse import EventSourceResponse

from backend.models import (
    AssistantCreateRequest,
    AssistantCreateResponse,
    ChatRequest,
    ChatResponse,
    AssistantInfo,
    ErrorResponse,
    HealthResponse,
    DataSourceType
)
from backend.assistant_engine import AssistantEngine
from backend.data_loader import DataLoader
from backend.vector_store import VectorStoreManager
from backend.database.mongodb import connect_to_mongo, close_mongo_connection
from backend.database import crud
from backend.auth.dependencies import get_current_user
from backend.routes import auth
from backend.database.models import UserInDB

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dynamic AI Assistant API",
    description="Create and chat with custom AI assistants dynamically",
    version="1.0.0"
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Neural Link Error: {str(exc)}", "type": "INTERNAL_NEURAL_ERROR"}
    )


# Universal Collaboration Protocol: Allow all local devices (Mac, Windows, Linux) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Neural Protocol Management: Handle security, logging, and errors in a single high-performance block
@app.middleware("http")
async def neural_protocol_middleware(request, call_next):
    try:
        # Pre-execution tracer
        if "external" in request.url.path:
            logger.info(f"🛰️ INCOMING EXTERNAL LINK: {request.method} {request.url.path} from {request.client.host if request.client else 'Unknown'}")
            
        response = await call_next(request)
        
        # Mandatory Security Headers
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response
        
    except Exception as e:
        import traceback
        logger.error(f"🚨 FATAL CORE ERROR: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"BrainCore Collision Error: {str(e)}",
                "type": type(e).__name__,
                "suggestion": "Check server console for full traceback."
            }
        )

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Neural Protocol Online", "host_ip": "10.178.40.76", "port": 8888}

# Add MongoDB lifecycle events
@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()


# Include auth router
app.include_router(auth.router)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY not found in environment variables")
    raise ValueError("GROQ_API_KEY must be set in .env file")

try:
    assistant_engine = AssistantEngine(
        groq_api_key=GROQ_API_KEY,
        model_name=GROQ_MODEL_NAME
    )
    data_loader = DataLoader()
    vector_store_manager = VectorStoreManager()
    logger.info("Assistant engine initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize assistant engine: {str(e)}")
    raise

assistants_store: Dict[str, Dict] = {}

from backend.routes import external
app.include_router(external.router)

# Serve React build in production, fallback to old frontend for development
FRONTEND_BUILD_DIR = "frontend/dist"
FRONTEND_DEV_DIR = "frontend"

if os.path.exists(FRONTEND_BUILD_DIR):
    # Production: Serve React build
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_BUILD_DIR, "static")), name="static")
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_BUILD_DIR, "index.html"))
else:
    # Development: Serve old HTML files
    app.mount("/static", StaticFiles(directory=FRONTEND_DEV_DIR), name="static")
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DEV_DIR, "index.html"))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/api/assistants/create", response_model=AssistantCreateResponse)
async def create_assistant(
    name: str = Form(...),
    data_source_type: str = Form(...),
    data_source_url: Optional[str] = Form(None),
    custom_instructions: str = Form(
        "You are a helpful AI assistant. Analyze the data, identify patterns, and answer questions. You can make predictions based on data patterns when asked about hypothetical scenarios."
    ),
    enable_statistics: bool = Form(False),
    enable_alerts: bool = Form(False),
    enable_recommendations: bool = Form(False),
    file: Optional[UploadFile] = File(None),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        logger.info(f"Creating assistant: {name} for user: {current_user.email}")
        
        if data_source_type not in ["csv", "json", "url", "mongodb"]:
            raise HTTPException(400, "Invalid data_source_type")
        
        assistant_id = str(uuid.uuid4())
        
        documents = []
        
        if data_source_type == "url":
            if not data_source_url:
                raise HTTPException(400, "data_source_url required for URL type")
            
            logger.info(f"Loading data from URL: {data_source_url}")
            documents = DataLoader.load_from_url(data_source_url)
            
        elif data_source_type == "mongodb":
            collection_name = data_source_url if data_source_url else None
            logger.info(f"Loading data from MongoDB all collections or {collection_name}")
            documents = DataLoader.load_from_mongodb(collection_name)
        
        else:
            if not file:
                raise HTTPException(400, "File required for CSV/JSON type")
            
            file_size = 0
            content = await file.read()
            file_size = len(content) / (1024 * 1024)
            
            if file_size > MAX_FILE_SIZE_MB:
                raise HTTPException(
                    400, 
                    f"File size exceeds {MAX_FILE_SIZE_MB}MB limit"
                )
            
            # Create user-specific upload directory
            user_upload_dir = os.path.join(UPLOAD_DIR, current_user.id)
            os.makedirs(user_upload_dir, exist_ok=True)
            
            file_path = os.path.join(user_upload_dir, f"{assistant_id}_{file.filename}")
            with open(file_path, "wb") as f:
                f.write(content)
            
            logger.info(f"File saved: {file_path}")
            
            if data_source_type == "csv":
                documents = DataLoader.load_from_csv(file_path)
            elif data_source_type == "json":
                documents = DataLoader.load_from_json(file_path)
        
        if not documents:
            raise HTTPException(400, "No data could be loaded from the source")
        
        logger.info(f"Loaded {len(documents)} documents")
        
        assistant_config = assistant_engine.create_assistant(
            assistant_id=assistant_id,
            name=name,
            documents=documents,
            custom_instructions=custom_instructions,
            enable_statistics=enable_statistics,
            enable_alerts=enable_alerts,
            enable_recommendations=enable_recommendations
        )
        
        # Save FAISS index
        vs_path = os.path.join(UPLOAD_DIR, "vector_stores", assistant_id)
        vector_store_manager.save_vector_store(assistant_config["vector_store"], vs_path)
        
        # Save to MongoDB
        assistant_data = {
            "user_id": current_user.id,
            "assistant_id": assistant_id,
            "name": name,
            "data_source_type": data_source_type,
            "data_source_url": data_source_url,
            "custom_instructions": custom_instructions,
            "enable_statistics": enable_statistics,
            "enable_alerts": enable_alerts,
            "enable_recommendations": enable_recommendations,
            "documents_count": len(documents),
            "vector_store_path": user_upload_dir if data_source_type not in ["url", "mongodb"] else ""
        }
        await crud.create_assistant(assistant_data)
        
        # Keep in memory for current session
        assistants_store[assistant_id] = assistant_config
        
        logger.info(f"Assistant created: {assistant_id}")
        
        return AssistantCreateResponse(
            assistant_id=assistant_id,
            name=name,
            data_source_type=data_source_type,
            documents_loaded=len(documents),
            created_at=assistant_config["created_at"],
            message="Assistant created successfully! You can now start chatting."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating assistant: {str(e)}")
        raise HTTPException(500, f"Failed to create assistant: {str(e)}")

@app.post("/api/assistants/auto-vtfinal")
async def auto_create_vtfinal_assistant(current_user: UserInDB = Depends(get_current_user)):
    try:
        # Check if user already has it
        assistants = await crud.get_user_assistants(current_user.id)
        for asst in assistants:
            if asst.name == "Global vtfinal Assistant" and asst.data_source_type == "mongodb":
                return {
                    "assistant_id": asst.assistant_id,
                    "name": asst.name,
                    "message": "Assistant ready"
                }
        
        # Determine unique assistant id
        assistant_id = str(uuid.uuid4())
        name = "Global vtfinal Assistant"
        data_source_type = "mongodb"
        
        logger.info(f"Auto-creating vtfinal assistant for {current_user.email}")
        
        # Load from ALL collections
        documents = DataLoader.load_from_mongodb(None)
        if not documents:
            raise HTTPException(400, "No data could be loaded from vtfinal")
            
        assistant_config = assistant_engine.create_assistant(
            assistant_id=assistant_id,
            name=name,
            documents=documents,
            custom_instructions="You are a helpful AI assistant connected to the vtfinal master database. Answer questions accurately based on all provided documents.",
            enable_statistics=True,
            enable_alerts=False,
            enable_recommendations=True
        )
        
        vs_path = os.path.join(UPLOAD_DIR, "vector_stores", assistant_id)
        vector_store_manager.save_vector_store(assistant_config["vector_store"], vs_path)
        
        assistant_data = {
            "user_id": current_user.id,
            "assistant_id": assistant_id,
            "name": name,
            "data_source_type": data_source_type,
            "data_source_url": "",
            "custom_instructions": assistant_config["custom_instructions"],
            "enable_statistics": True,
            "enable_alerts": False,
            "enable_recommendations": True,
            "documents_count": len(documents),
            "vector_store_path": ""
        }
        await crud.create_assistant(assistant_data)
        
        assistants_store[assistant_id] = assistant_config
        return {
            "assistant_id": assistant_id,
            "name": name,
            "message": "Assistant created and ready"
        }
    except Exception as e:
        logger.error(f"Error auto-creating vtfinal assistant: {str(e)}")
        raise HTTPException(500, f"Failed to auto-create vtfinal assistant: {str(e)}")



@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_assistant(
    request: ChatRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    import time
    start_time = time.time()
    
    try:
        logger.info(f"Chat request for assistant: {request.assistant_id} by user: {current_user.email}")
        
        # Verify user owns this assistant
        assistant_db = await crud.get_assistant_by_id(request.assistant_id, current_user.id)
        if not assistant_db:
            raise HTTPException(404, "Assistant not found or access denied")
        
        # Load assistant config if not in memory
        if request.assistant_id not in assistants_store:
            load_start = time.time()
            logger.info(f"Loading assistant {request.assistant_id} from database...")
            
            # Check cache
            vs_path = os.path.join(UPLOAD_DIR, "vector_stores", request.assistant_id)
            if os.path.exists(vs_path):
                logger.info("Loading vector store from cache")
                vector_store = vector_store_manager.load_vector_store(vs_path)
                documents_count = assistant_db.documents_count
            else:
                # Load documents based on data source type
                documents = []
                
                if assistant_db.data_source_type == "mongodb":
                    collection_name = assistant_db.data_source_url if assistant_db.data_source_url else None
                    logger.info(f"Loading data from MongoDB all collections or {collection_name}")
                    documents = DataLoader.load_from_mongodb(collection_name)
                    
                elif assistant_db.data_source_type == "url":
                    logger.info(f"Loading data from URL: {assistant_db.data_source_url}")
                    if assistant_db.data_source_url:
                        documents = DataLoader.load_from_url(assistant_db.data_source_url)
                        
                else:
                    # File based
                    user_upload_dir = os.path.join(UPLOAD_DIR, current_user.id)
                    assistant_files = []
                    if os.path.exists(user_upload_dir):
                        for file in os.listdir(user_upload_dir):
                            if file.startswith(f"{request.assistant_id}_"):
                                assistant_files.append(os.path.join(user_upload_dir, file))
                    
                    if not assistant_files:
                        raise HTTPException(400, "Assistant files not found. Please recreate the assistant.")
                    
                    for file_path in assistant_files:
                        file_ext = os.path.splitext(file_path)[1].lower()
                        try:
                            if file_ext == '.csv':
                                docs = DataLoader.load_from_csv(file_path)
                            elif file_ext == '.json':
                                docs = DataLoader.load_from_json(file_path)
                            else:
                                logger.warning(f"Unsupported file type: {file_ext}")
                                continue
                            documents.extend(docs)
                        except Exception as e:
                            logger.error(f"Error loading file {file_path}: {str(e)}")
                            
                if not documents:
                    raise HTTPException(400, "Failed to load assistant documents.")
                
                # Create vector store and cache
                vector_store = vector_store_manager.create_vector_store(documents)
                vector_store_manager.save_vector_store(vector_store, vs_path)
                documents_count = len(documents)
            
            # Build system instructions using assistant engine's method
            system_instructions = assistant_engine._build_system_instructions(
                custom_instructions=assistant_db.custom_instructions,
                enable_statistics=assistant_db.enable_statistics,
                enable_alerts=assistant_db.enable_alerts,
                enable_recommendations=assistant_db.enable_recommendations
            )
            
            # Restore assistant config
            assistant_config = {
                "assistant_id": request.assistant_id,
                "name": assistant_db.name,
                "custom_instructions": assistant_db.custom_instructions,
                "system_instructions": system_instructions,
                "vector_store": vector_store,
                "documents_count": documents_count,
                "enable_statistics": assistant_db.enable_statistics,
                "enable_alerts": assistant_db.enable_alerts,
                "enable_recommendations": assistant_db.enable_recommendations,
                "created_at": assistant_db.created_at
            }
            
            assistants_store[request.assistant_id] = assistant_config
            load_time = time.time() - load_start
            logger.info(f"Assistant {request.assistant_id} loaded in {load_time:.2f}s")
        else:
            logger.info(f"Using cached assistant {request.assistant_id}")
        
        assistant_config = assistants_store[request.assistant_id]
        
        # Call LLM
        llm_start = time.time()
        result = assistant_engine.chat(
            assistant_config=assistant_config,
            user_message=request.message
        )
        llm_time = time.time() - llm_start
        logger.info(f"LLM response received in {llm_time:.2f}s")
        
        # Save chat history
        await crud.save_chat_message(current_user.id, request.assistant_id, "user", request.message)
        await crud.save_chat_message(current_user.id, request.assistant_id, "assistant", result["response"])
        
        total_time = time.time() - start_time
        logger.info(f"Total chat request time: {total_time:.2f}s")
        
        return ChatResponse(
            assistant_id=request.assistant_id,
            user_message=request.message,
            assistant_response=result["response"],
            sources_used=result["sources_used"],
            timestamp=result["timestamp"]
        )
    
    except Exception as e:
        logger.error(f"Error during chat: {str(e)}")
        raise HTTPException(500, f"Chat failed: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        logger.info(f"Stream chat request for assistant: {request.assistant_id}")
        
        # Verify user owns this assistant
        assistant_db = await crud.get_assistant_by_id(request.assistant_id, current_user.id)
        if not assistant_db:
            raise HTTPException(404, "Assistant not found or access denied")
            
        # ---------------------------------------------------------
        # NEW: Load Assistant Config FIRST (needed for Actions too)
        # ---------------------------------------------------------
        
        # Check if already loaded in memory
        if request.assistant_id not in assistants_store:
            vs_path = os.path.join(UPLOAD_DIR, "vector_stores", request.assistant_id)
            if os.path.exists(vs_path):
                logger.info("Loading vector store from cache")
                vector_store = vector_store_manager.load_vector_store(vs_path)
                documents_count = assistant_db.documents_count
            else:
                # Load documents based on data source type
                documents = []
                
                if assistant_db.data_source_type == "mongodb":
                    collection_name = assistant_db.data_source_url if assistant_db.data_source_url else None
                    try:
                        documents = DataLoader.load_from_mongodb(collection_name)
                    except Exception as e:
                        logger.error(f"Error loading mongodb: {e}")
                        
                elif assistant_db.data_source_type == "url":
                    try:
                        if assistant_db.data_source_url:
                            documents = DataLoader.load_from_url(assistant_db.data_source_url)
                    except Exception as e:
                        logger.error(f"Error loading url: {e}")
                        
                else:
                    user_upload_dir = os.path.join(UPLOAD_DIR, current_user.id)
                    assistant_files = []
                    if os.path.exists(user_upload_dir):
                        for file_name in os.listdir(user_upload_dir):
                            if file_name.startswith(f"{request.assistant_id}_"):
                                assistant_files.append(os.path.join(user_upload_dir, file_name))
                    
                    for file_path in assistant_files:
                        file_ext = os.path.splitext(file_path)[1].lower()
                        try:
                            if file_ext == '.csv':
                                docs = DataLoader.load_from_csv(file_path)
                            elif file_ext == '.json':
                                docs = DataLoader.load_from_json(file_path)
                            elif file_ext == '.pdf':
                                docs = DataLoader.load_from_pdf(file_path)
                            elif file_ext == '.txt':
                                docs = DataLoader.load_from_txt(file_path)
                            documents.extend(docs)
                        except Exception as e:
                            logger.error(f"Error loading file {file_path}: {e}")
                            continue
                
                if documents:
                    vector_store = vector_store_manager.create_vector_store(documents)
                    vector_store_manager.save_vector_store(vector_store, vs_path)
                else:
                    vector_store = None
                documents_count = len(documents)

            system_instructions = assistant_engine._build_system_instructions(
                custom_instructions=assistant_db.custom_instructions,
                enable_statistics=assistant_db.enable_statistics,
                enable_alerts=assistant_db.enable_alerts,
                enable_recommendations=assistant_db.enable_recommendations
            )
            
            assistants_store[request.assistant_id] = {
                "assistant_id": request.assistant_id,
                "name": assistant_db.name,
                "custom_instructions": assistant_db.custom_instructions,
                "system_instructions": system_instructions,
                "vector_store": vector_store,
                "documents_count": documents_count,
                "enable_statistics": assistant_db.enable_statistics,
                "enable_alerts": assistant_db.enable_alerts,
                "enable_recommendations": assistant_db.enable_recommendations,
                "created_at": assistant_db.created_at
            }
        
        # Get Config
        assistant_config = assistants_store.get(request.assistant_id)
        
        # ---------------------------------------------------------
        # Intent Detection Layer (Action Commands)
        # ---------------------------------------------------------
        from backend.actions import detect_intent, execute_action
        import json
        
        intent, target = detect_intent(request.message)
        if intent:
            # Pass the CONFIG, not just ID
            result = await execute_action(intent, target, assistant_config)
            
            # Save User Message
            await crud.save_chat_message(current_user.id, request.assistant_id, "user", request.message)
            
            # Determine text for DB history
            response_text = ""
            if result.get("type") == "error":
                response_text = result.get("message", "Error executing action")
            elif result.get("type") == "success":
                response_text = result.get("message", "Action completed successfully")
            elif result.get("type") == "action":
                if result.get("action") == "open_whatsapp":
                    response_text = f"Opening WhatsApp for {result.get('phone')}..."
                else:
                    response_text = "Executing action..."
            
            # Save Assistant Message
            if response_text:
                await crud.save_chat_message(current_user.id, request.assistant_id, "assistant", response_text)
            
            async def action_generator():
                yield json.dumps(result) + "\n"
                
            return EventSourceResponse(action_generator())
        # ---------------------------------------------------------
        
        # assistant_config is already loaded and available here
        
        async def wrap_generator():
            full_response = ""
            # Save User Message immediately
            await crud.save_chat_message(current_user.id, request.assistant_id, "user", request.message)
            
            async for chunk in assistant_engine.chat_stream(
                assistant_config=assistant_config,
                user_message=request.message
            ):
                import json
                try:
                    data = json.loads(chunk.strip())
                    if data.get("type") == "content":
                        full_response += data.get("data", "")
                except:
                    pass
                yield chunk
            
            # Save Assistant Message once stream is complete
            if full_response:
                await crud.save_chat_message(current_user.id, request.assistant_id, "assistant", full_response)

        return EventSourceResponse(wrap_generator())
            
    except Exception as e:
        logger.error(f"Error during stream chat: {str(e)}")
        raise HTTPException(500, str(e))


@app.get("/api/assistants/{assistant_id}", response_model=AssistantInfo)
async def get_assistant_info(
    assistant_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        # Verify user owns this assistant
        assistant_db = await crud.get_assistant_by_id(assistant_id, current_user.id)
        if not assistant_db:
            raise HTTPException(404, "Assistant not found or access denied")
        
        return AssistantInfo(
            assistant_id=assistant_db.assistant_id,
            name=assistant_db.name,
            data_source_type=assistant_db.data_source_type,
            custom_instructions=assistant_db.custom_instructions,
            documents_count=assistant_db.documents_count,
            enable_statistics=assistant_db.enable_statistics,
            enable_alerts=assistant_db.enable_alerts,
            enable_recommendations=assistant_db.enable_recommendations,
            created_at=assistant_db.created_at.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting assistant info: {str(e)}")
        raise HTTPException(500, f"Failed to get assistant info: {str(e)}")


@app.get("/api/assistants")
async def list_assistants(current_user: UserInDB = Depends(get_current_user)):
    try:
        # Get assistants from MongoDB for this user
        assistants = await crud.get_user_assistants(current_user.id)
        
        assistants_list = [
            {
                "assistant_id": asst.assistant_id,
                "name": asst.name,
                "documents_count": asst.documents_count,
                "data_source_type": asst.data_source_type,
                "created_at": asst.created_at.isoformat()
            }
            for asst in assistants
        ]
        
        return {"assistants": assistants_list, "count": len(assistants_list)}
    
    except Exception as e:
        logger.error(f"Error listing assistants: {str(e)}")
        raise HTTPException(500, f"Failed to list assistants: {str(e)}")


@app.delete("/api/assistants/{assistant_id}")
async def delete_assistant(
    assistant_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        # Delete from MongoDB
        deleted = await crud.delete_assistant(assistant_id, current_user.id)
        if not deleted:
            raise HTTPException(404, "Assistant not found or access denied")
        
        # Remove from memory store
        if assistant_id in assistants_store:
            del assistants_store[assistant_id]
        
        # Clean up user files
        user_upload_dir = os.path.join(UPLOAD_DIR, current_user.id)
        if os.path.exists(user_upload_dir):
            for file in os.listdir(user_upload_dir):
                if file.startswith(assistant_id):
                    os.remove(os.path.join(user_upload_dir, file))
        
        logger.info(f"Assistant deleted: {assistant_id}")
        
        return {"message": "Assistant deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting assistant: {str(e)}")
        raise HTTPException(500, f"Failed to delete assistant: {str(e)}")


@app.get("/api/assistants/{assistant_id}/chat-history")
async def get_assistant_chat_history(
    assistant_id: str,
    limit: int = 50,
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        # Verify user owns this assistant
        assistant_db = await crud.get_assistant_by_id(assistant_id, current_user.id)
        if not assistant_db:
            raise HTTPException(404, "Assistant not found or access denied")
        
        # Get chat history
        messages = await crud.get_chat_history(current_user.id, assistant_id, limit)
        
        return {
            "assistant_id": assistant_id,
            "messages": messages,
            "total": len(messages)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        raise HTTPException(500, f"Failed to retrieve chat history: {str(e)}")





if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# Reload trigger
