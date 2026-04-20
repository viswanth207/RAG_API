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

# Ensure paths are absolute relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, "frontend", "dist")

# Mount Static Assets
if os.path.exists(os.path.join(DIST_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

@app.get("/")
async def serve_erp_ui():
    index_path = os.path.join(DIST_DIR, "index.html")
    if not os.path.exists(index_path):
        return {"message": "Admin ERP UI Not Built Yet. Run npm run build."}
    return FileResponse(index_path)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
