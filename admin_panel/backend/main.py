from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

app = FastAPI(title="Brain.OS Admin Control Center")

@app.get("/")
async def serve_admin_ui():
    # Adjusted path for remote server structure
    path = "admin_panel/frontend/index.html"
    if not os.path.exists(path):
        # Fallback if running directly from backend folder
        path = "../frontend/index.html"
    return FileResponse(path)

# Universal Collaboration Protocol
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URL = os.getenv("MONGODB_URL")
if not MONGODB_URL:
    raise ValueError("MONGODB_URL not found in environment")

client = AsyncIOMotorClient(MONGODB_URL)
db = client.dynamic_assistant_db

@app.get("/api/admin/health")
async def health():
    return {"status": "online", "system": "Admin Control Center"}

@app.get("/api/admin/stats")
async def get_global_stats():
    try:
        # 1. Total lifetime hits
        total_hits = await db.api_audit_logs.count_documents({})
        
        # 2. Success Rate
        success_count = await db.api_audit_logs.count_documents({"status_code": {"$lt": 400}})
        success_rate = (success_count / total_hits * 100) if total_hits > 0 else 100
        
        # 3. Recent Live Feed (Last 50)
        cursor = db.api_audit_logs.find().sort("timestamp", -1).limit(50)
        logs = []
        async for log in cursor:
            log["_id"] = str(log["_id"])
            # Format timestamp for frontend
            if isinstance(log.get("timestamp"), datetime):
                log["timestamp"] = log["timestamp"].isoformat()
            logs.append(log)
            
        # 4. Usage by Endpoint
        pipeline = [
            {"$group": {"_id": "$endpoint", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        endpoint_stats = []
        async for res in db.api_audit_logs.aggregate(pipeline):
            endpoint_stats.append(res)

        return {
            "total_hits": total_hits,
            "success_rate": round(success_rate, 1),
            "recent_logs": logs,
            "endpoint_distribution": endpoint_stats,
            "server_timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Admin runs on port 9000 to keep it separate from the main app
    uvicorn.run(app, host="0.0.0.0", port=9000)
