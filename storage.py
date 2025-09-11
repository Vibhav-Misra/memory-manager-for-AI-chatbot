from pymongo import MongoClient
from typing import List, Optional, Dict, Any
from models import StoredMemory, BufferedMemory, CandidateMemory, MemoryDecision
from config import Config
import logging
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)

class MemoryStorage:
    """MongoDB storage for memories and audit logs"""
    
    def __init__(self):
        self.client = MongoClient(Config.MONGODB_URI)
        self.db = self.client[Config.MONGODB_DB]
        
        # Collections
        self.stored_memories = self.db.stored_memories
        self.buffered_memories = self.db.buffered_memories
        self.audit_logs = self.db.audit_logs
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            # Index on memory type and content for deduplication
            self.stored_memories.create_index([("candidate.memory_type", 1)])
            self.stored_memories.create_index([("final_content", 1)])
            
            # Index on buffer score for admin review
            self.buffered_memories.create_index([("buffer_score", -1)])
            self.buffered_memories.create_index([("buffered_at", -1)])
            
            # Index on audit logs for traceability
            self.audit_logs.create_index([("timestamp", -1)])
            self.audit_logs.create_index([("memory_id", 1)])
            
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    def store_memory(self, candidate: CandidateMemory, decision: MemoryDecision, final_content: str) -> str:
        """Store an accepted memory"""
        try:
            # Generate embedding (placeholder for now)
            embedding = self._generate_embedding(final_content)
            
            stored_memory = StoredMemory(
                candidate=candidate,
                decision=decision,
                final_content=final_content,
                embedding=embedding
            )
            
            # Convert to dict for MongoDB
            memory_dict = stored_memory.dict()
            memory_dict["_id"] = None  # Let MongoDB generate ID
            
            result = self.stored_memories.insert_one(memory_dict)
            memory_id = str(result.inserted_id)
            
            # Update the stored memory with the ID
            stored_memory.id = memory_id
            
            # Log the storage action
            self._log_audit("store", memory_id, decision, candidate)
            
            # Stub call to Tavus
            self._upsert_tavus_memory(stored_memory)
            
            logger.info(f"Stored memory with ID: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise
    
    def buffer_memory(self, candidate: CandidateMemory, buffer_reason: str, buffer_score: float) -> str:
        """Buffer a memory for admin review"""
        try:
            logger.info(f"Buffering memory: {candidate.content[:50]}...")
            
            # Create BufferedMemory object
            buffered_memory = BufferedMemory(
                candidate=candidate,
                buffer_reason=buffer_reason,
                buffer_score=buffer_score,
                buffered_at=datetime.now(timezone.utc)
            )
            
            # Convert to dict for MongoDB
            memory_dict = buffered_memory.dict()
            
            # Insert into MongoDB
            result = self.buffered_memories.insert_one(memory_dict)
            memory_id = str(result.inserted_id)
            
            # Log the buffer action
            self._log_audit("buffer", memory_id, None, candidate)
            
            logger.info(f"Successfully buffered memory: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to buffer memory: {e}")
            raise
    
    def get_stored_memories(self, limit: int = 100, offset: int = 0) -> List[StoredMemory]:
        """Retrieve stored memories with pagination"""
        try:
            cursor = self.stored_memories.find().skip(offset).limit(limit).sort("stored_at", -1)
            memories = []
            
            for doc in cursor:
                doc["id"] = str(doc["_id"])
                del doc["_id"]
                memories.append(StoredMemory(**doc))
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to retrieve stored memories: {e}")
            return []
    
    def get_buffered_memories(self, limit: int = 100, offset: int = 0) -> List[BufferedMemory]:
        """Retrieve buffered memories for admin review"""
        try:
            cursor = self.buffered_memories.find().skip(offset).limit(limit).sort("buffered_at", -1)
            memories = []
            
            for doc in cursor:
                doc["id"] = str(doc["_id"])
                del doc["_id"]
                memories.append(BufferedMemory(**doc))
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to retrieve buffered memories: {e}")
            return []
    
    def approve_buffered_memory(self, memory_id: str, admin_notes: str = None) -> bool:
        """Approve a buffered memory and move it to storage"""
        try:
            # Convert string ID to ObjectId for MongoDB query
            from bson import ObjectId
            try:
                object_id = ObjectId(memory_id)
            except Exception as e:
                logger.error(f"Invalid memory ID format: {memory_id}, error: {e}")
                return False
            
            # Get the buffered memory
            buffered_doc = self.buffered_memories.find_one({"_id": object_id})
            if not buffered_doc:
                logger.warning(f"Buffered memory {memory_id} not found")
                return False
            
            # Extract the candidate memory
            candidate_data = buffered_doc["candidate"]
            candidate = CandidateMemory(**candidate_data)
            
            # Create a decision for storage
            decision = MemoryDecision(
                action="keep",
                reason="Approved by admin",
                admin_notes=admin_notes
            )
            
            # Store the memory
            try:
                memory_id = self.store_memory(candidate, decision, candidate.content)
                logger.info(f"Successfully stored approved memory: {memory_id}")
                
                # Remove from buffered collection
                self.buffered_memories.delete_one({"_id": object_id})
                logger.info(f"Removed buffered memory: {memory_id}")
                
                # Log the approval action
                self._log_audit("approve", memory_id, decision, candidate)
                
                return True
                
            except Exception as store_error:
                logger.error(f"Failed to store approved memory: {store_error}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to approve buffered memory: {e}")
            return False
    
    def reject_buffered_memory(self, memory_id: str, admin_notes: str = None) -> bool:
        """Reject a buffered memory"""
        try:
            # Convert string ID to ObjectId for MongoDB query
            from bson import ObjectId
            try:
                object_id = ObjectId(memory_id)
            except Exception as e:
                logger.error(f"Invalid memory ID format: {memory_id}, error: {e}")
                return False
            
            # Get the buffered memory
            buffered_doc = self.buffered_memories.find_one({"_id": object_id})
            if not buffered_doc:
                logger.warning(f"Buffered memory {memory_id} not found")
                return False
            
            # Convert to BufferedMemory object
            buffered_doc["id"] = str(buffered_doc["_id"])
            del buffered_doc["_id"]
            buffered_memory = BufferedMemory(**buffered_doc)
            
            # Create decision for rejection
            decision = MemoryDecision(
                action="reject",
                reason="Rejected by admin review",
                admin_notes=admin_notes
            )
            
            # Log the rejection
            self._log_audit("reject", memory_id, decision, buffered_memory.candidate)
            
            # Remove from buffer
            self.buffered_memories.delete_one({"_id": object_id})
            
            logger.info(f"Rejected buffered memory {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reject buffered memory: {e}")
            return False
    
    def _log_audit(self, action: str, memory_id: str, decision: Optional[MemoryDecision], candidate: CandidateMemory):
        """Log an audit event"""
        try:
            audit_log = {
                "timestamp": datetime.now(timezone.utc),
                "action": action,
                "memory_id": memory_id,
                "memory_type": candidate.memory_type.value,
                "content": candidate.content,
                "salience_score": candidate.salience_score,
                "decision": decision.dict() if decision else None,
                "evidence": candidate.extraction_evidence
            }
            
            self.audit_logs.insert_one(audit_log)
            
        except Exception as e:
            logger.warning(f"Failed to log audit event: {e}")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (placeholder)"""
        # In production, this would call OpenAI's embedding API
        # For now, return a placeholder
        import hashlib
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        import numpy as np
        np.random.seed(seed)
        return np.random.rand(1536).tolist()
    
    def _upsert_tavus_memory(self, stored_memory: StoredMemory):
        """Stub for Tavus memory integration"""
        # This is a placeholder for future Tavus integration
        logger.info(f"Tavus stub: would upsert memory {stored_memory.id}")
        # In production, this would call Tavus API:
        # tavus_client.upsert_memory(
        #     memory_id=stored_memory.id,
        #     content=stored_memory.final_content,
        #     memory_type=stored_memory.candidate.memory_type.value,
        #     metadata=stored_memory.candidate.metadata
        # )
    
    def health_check(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            # Test database connection
            self.db.command("ping")
            
            # Get collection counts
            stored_count = self.stored_memories.count_documents({})
            buffered_count = self.buffered_memories.count_documents({})
            audit_count = self.audit_logs.count_documents({})
            
            return {
                "status": "healthy",
                "database": "connected",
                "collections": {
                    "stored_memories": stored_count,
                    "buffered_memories": buffered_count,
                    "audit_logs": audit_count
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "database": f"error: {str(e)}",
                "collections": {}
            }
    
    def close(self):
        """Close database connection"""
        self.client.close()







