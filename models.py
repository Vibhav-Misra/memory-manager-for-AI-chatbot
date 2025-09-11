from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum

class MemoryType(str, Enum):
    """Types of memories that can be extracted"""
    PREFERENCE = "preference"
    GOAL = "goal"
    COMMITMENT = "commitment"
    SKILL = "skill"
    FEEDBACK = "feedback"

class ConversationTurn(BaseModel):
    """A single turn in a conversation"""
    speaker: str
    text: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class CandidateMemory(BaseModel):
    """A candidate memory extracted from conversation"""
    id: Optional[str] = None
    memory_type: MemoryType
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    relevance: float = Field(ge=0.0, le=1.0)
    specificity: float = Field(ge=0.0, le=1.0)
    salience_score: float = Field(ge=0.0, le=1.0)
    source_turn: ConversationTurn
    extraction_evidence: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class MemoryDecision(BaseModel):
    """Decision made about a candidate memory"""
    action: str  # "keep", "merge", "buffer", "reject"
    reason: str
    merged_with: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    admin_notes: Optional[str] = None

class StoredMemory(BaseModel):
    """A memory that has been processed and stored"""
    id: Optional[str] = None
    candidate: CandidateMemory
    decision: MemoryDecision
    final_content: str
    embedding: Optional[List[float]] = None
    stored_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BufferedMemory(BaseModel):
    """A memory waiting for admin review"""
    id: Optional[str] = None
    candidate: CandidateMemory
    buffer_reason: str
    buffer_score: float
    buffered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ExtractionRequest(BaseModel):
    """Request to extract memories from conversation turns"""
    turns: List[ConversationTurn]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ExtractionResponse(BaseModel):
    """Response from memory extraction"""
    candidates: List[CandidateMemory]
    decisions: List[MemoryDecision]
    stored_count: int
    buffered_count: int
    rejected_count: int

class AdminReviewRequest(BaseModel):
    """Request to review a buffered memory"""
    memory_id: str
    action: str  # "approve", "reject", "modify"
    notes: Optional[str] = None
    modified_content: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    collections: Optional[Dict[str, int]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


