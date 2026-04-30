from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

import os
import sys

# Ensure the local directory is in the path for imports
sys.path.append(os.path.dirname(__file__))

from auth_utils import get_password_hash, verify_password, create_access_token

from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI(title="Data Mind.os Admin ERP")

@app.on_event("startup")
async def startup_event():
    print("\n" + "="*50)
    print("🚀 DATA MIND ADMIN ERP BACKEND ONLINE")
    print(f"🔗 Access the Dashboard at: http://localhost:9000")
    print(f"📁 Serving frontend from: {DIST_DIR}")
    if not os.path.exists(DIST_DIR):
        print("❌ WARNING: Frontend builds not found! Run 'npm run build' in admin_panel/frontend")
    print("="*50 + "\n")

# Security Protocol
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URL = os.getenv("MONGODB_URL")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.dynamic_assistant_db

# Models
class AdminAuth(BaseModel):
    username: str
    password: str

# Ensure paths are absolute relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, "frontend", "dist")

# Robust Static File Protocol
if os.path.exists(DIST_DIR):
    # Mount assets folder explicitly
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

# (Static files catch-all route moved to bottom)
# (Existing API routes follow)

@app.post("/api/admin/setup")
async def setup_initial_admin(auth: AdminAuth):
    # Check if any admin exists
    exists = await db.admins.find_one({})
    if exists:
        raise HTTPException(400, "Admin already initialized")
    
    admin_doc = {
        "username": auth.username,
        "password_hash": get_password_hash(auth.password),
        "created_at": datetime.utcnow()
    }
    await db.admins.insert_one(admin_doc)
    return {"message": "Master Admin created successfully"}

@app.post("/api/admin/login")
async def admin_login(auth: AdminAuth):
    admin = await db.admins.find_one({"username": auth.username})
    if not admin or not verify_password(auth.password, admin["password_hash"]):
        raise HTTPException(401, "Invalid administrative credentials")
    
    token = create_access_token({"sub": auth.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/admin/dashboard/summary")
async def get_dashboard_summary():
    total_hits = await db.api_audit_logs.count_documents({})
    success_count = await db.api_audit_logs.count_documents({"status_code": {"$lt": 400}})
    unique_clients = len(await db.api_audit_logs.distinct("api_key"))
    
    # Latency Average (Last 100)
    cursor = db.api_audit_logs.find().sort("timestamp", -1).limit(100)
    latencies = []
    async for log in cursor:
        latencies.append(log.get("latency_ms", 0))
    
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    return {
        "total_hits": total_hits,
        "success_rate": round((success_count/total_hits*100), 1) if total_hits > 0 else 100,
        "active_clients": unique_clients,
        "avg_latency_ms": round(avg_latency, 1)
    }

@app.get("/api/admin/logs")
async def get_audit_logs(limit: int = 100):
    cursor = db.api_audit_logs.find().sort("timestamp", -1).limit(limit)
    logs = []
    async for log in cursor:
        log["_id"] = str(log["_id"])
        if isinstance(log.get("timestamp"), datetime):
            log["timestamp"] = log["timestamp"].isoformat()
        logs.append(log)
    return logs

@app.get("/api/admin/clients")
async def get_api_clients():
    cursor = db.api_clients.find().sort("created_at", -1)
    clients = []
    async for client in cursor:
        client["_id"] = str(client["_id"])
        
        # Mask the API key (e.g. sk_***123)
        api_key = client.get("api_key", "")
        masked_key = f"{api_key[:4]}***{api_key[-4:]}" if len(api_key) > 8 else "***"
        
        # Default limits if not set
        usage_count = client.get("usage_count", 0)
        usage_limit = client.get("usage_limit", 100)
        
        # Fetch the most recent target DB from audit logs for this client
        latest_log = await db.api_audit_logs.find_one(
            {"api_key": api_key, "metadata.target_db": {"$exists": True}},
            sort=[("timestamp", -1)]
        )
        
        target_db = latest_log.get("metadata", {}).get("target_db", "N/A") if latest_log else "N/A"
        target_url = latest_log.get("metadata", {}).get("target_url", "N/A") if latest_log else "N/A"
        
        # Mask target URL password if present (e.g. mongodb+srv://user:pass@...)
        if "@" in target_url and "://" in target_url:
            parts = target_url.split("@")
            prefix = parts[0].split("://")[0] + "://***:***@"
            target_url = prefix + parts[1]
            
        clients.append({
            "id": client["_id"],
            "api_key": masked_key,
            "raw_api_key": api_key, # needed for put requests, frontend shouldn't show it
            "created_at": client.get("created_at", datetime.utcnow()).isoformat(),
            "usage_count": usage_count,
            "usage_limit": usage_limit,
            "target_db": target_db,
            "target_url": target_url
        })
    return clients

class UpdateLimitRequest(BaseModel):
    limit: int

@app.put("/api/admin/clients/{api_key}/limit")
async def update_client_limit(api_key: str, request: UpdateLimitRequest):
    result = await db.api_clients.update_one(
        {"api_key": api_key},
        {"$set": {"usage_limit": request.limit}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="API Client not found")
    return {"message": "Limit updated successfully", "new_limit": request.limit}

@app.delete("/api/admin/clients/{api_key}")
async def delete_client(api_key: str):
    result = await db.api_clients.delete_one({"api_key": api_key})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="API Client not found")
    return {"message": "Identity completely revoked"}

# Catch-all route for SPA must be defined LAST so it doesn't intercept valid API calls
@app.get("/{full_path:path}")
async def serve_admin_panel(full_path: str):
    # 1. Try to serve exact file from DIST_DIR (e.g., vite.svg, favicon.ico)
    file_path = os.path.join(DIST_DIR, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
        
    # 2. Fallback to index.html for SPA behavior or root access
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return {"message": "Admin ERP UI Not Built Yet. Please run 'npm run build' in the frontend directory."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
