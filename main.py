from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import List

from models import (
    ExtractionRequest, ExtractionResponse, AdminReviewRequest,
    StoredMemory, BufferedMemory, HealthResponse
)
from decider_service import DeciderService
from config import Config

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Global service instance
decider_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle"""
    global decider_service
    
    # Startup
    try:
        Config.validate()
        decider_service = DeciderService()
        logging.info("Decider service started successfully")
    except Exception as e:
        logging.error(f"Failed to start Decider service: {e}")
        raise
    
    yield
    
    # Shutdown
    if decider_service:
        decider_service.close()
        logging.info("Decider service stopped")

# Create FastAPI app
app = FastAPI(
    title="Decider v1 - Memory Management Service",
    description="Extractor-Scorer-Deduper service for conversational memories",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_service() -> DeciderService:
    """Dependency to get the decider service"""
    if not decider_service:
        raise HTTPException(status_code=503, detail="Service not available")
    return decider_service

@app.post("/extract_and_store", response_model=ExtractionResponse)
async def extract_and_store_memories(
    request: ExtractionRequest,
    service: DeciderService = Depends(get_service)
):
    """Extract memories from conversation turns and process them"""
    try:
        response = service.extract_and_store(request)
        return response
    except Exception as e:
        logging.error(f"Error in extract_and_store: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memories", response_model=List[StoredMemory])
async def get_memories(
    limit: int = 100,
    offset: int = 0,
    service: DeciderService = Depends(get_service)
):
    """Retrieve stored memories with pagination"""
    try:
        memories = service.get_memories(limit=limit, offset=offset)
        return memories
    except Exception as e:
        logging.error(f"Error retrieving memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/buffer", response_model=List[BufferedMemory])
async def get_buffered_memories(
    limit: int = 100,
    offset: int = 0,
    service: DeciderService = Depends(get_service)
):
    """Retrieve buffered memories for admin review"""
    try:
        memories = service.get_buffered_memories(limit=limit, offset=offset)
        return memories
    except Exception as e:
        logging.error(f"Error retrieving buffered memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/buffer/{memory_id}/approve")
async def approve_buffered_memory(
    memory_id: str,
    request: AdminReviewRequest,
    service: DeciderService = Depends(get_service)
):
    """Approve a buffered memory"""
    try:
        success = service.approve_buffered_memory(
            memory_id, 
            request.notes
        )
        if success:
            return {"message": "Memory approved successfully", "memory_id": memory_id}
        else:
            raise HTTPException(status_code=404, detail="Memory not found or already processed")
    except Exception as e:
        logging.error(f"Error approving memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/buffer/{memory_id}/reject")
async def reject_buffered_memory(
    memory_id: str,
    request: AdminReviewRequest,
    service: DeciderService = Depends(get_service)
):
    """Reject a buffered memory"""
    try:
        success = service.reject_buffered_memory(
            memory_id, 
            request.notes
        )
        if success:
            return {"message": "Memory rejected successfully", "memory_id": memory_id}
        else:
            raise HTTPException(status_code=404, detail="Memory not found or already processed")
    except Exception as e:
        logging.error(f"Error rejecting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health/db", response_model=HealthResponse)
async def health_check(service: DeciderService = Depends(get_service)):
    """Check database and service health"""
    try:
        health = service.health_check()
        return HealthResponse(
            status=health["service"],
            database=health["database"]["status"],
            timestamp=health["timestamp"],
            collections=health["database"].get("collections", {})
        )
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        from datetime import datetime, timezone
        return HealthResponse(
            status="unhealthy",
            database="error",
            timestamp=datetime.now(timezone.utc),
            collections={}
        )

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Decider v1",
        "description": "Memory Management Service for Edy",
        "version": "1.0.0",
        "endpoints": {
            "extract_and_store": "/extract_and_store",
            "memories": "/memories",
            "buffer": "/buffer",
            "health": "/health/db"
        }
    }





