from typing import List, Dict, Any
from models import (
    ConversationTurn, CandidateMemory, MemoryDecision, 
    StoredMemory, BufferedMemory, ExtractionRequest, ExtractionResponse
)
from extractor import MemoryExtractor
from scorer import MemoryScorer
from deduper import MemoryDeduper
from storage import MemoryStorage
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class DeciderService:
    """Main orchestrator for the memory extraction and management pipeline"""
    
    def __init__(self):
        self.extractor = MemoryExtractor()
        self.scorer = MemoryScorer()
        self.deduper = MemoryDeduper()
        self.storage = MemoryStorage()
        
        logger.info("Decider service initialized")
    
    def extract_and_store(self, request: ExtractionRequest) -> ExtractionResponse:
        """Main pipeline: extract, score, deduplicate, and store memories"""
        try:
            logger.info(f"Processing extraction request with {len(request.turns)} conversation turns")
            
            # Step 1: Extract candidate memories
            candidates = self.extractor.extract_memories(request.turns)
            logger.info(f"Extracted {len(candidates)} candidate memories")
            
            if not candidates:
                return ExtractionResponse(
                    candidates=[],
                    decisions=[],
                    stored_count=0,
                    buffered_count=0,
                    rejected_count=0
                )
            
            # Step 2: Score candidates
            scored_candidates = self.scorer.score_memories(candidates)
            logger.info(f"Scored {len(scored_candidates)} candidates")
            
            # Step 3: Make initial decisions based on scores
            initial_decisions = self.scorer.make_decisions(scored_candidates)
            
            # Step 4: Deduplicate against stored memories and other candidates
            dedup_decisions, remaining_candidates = self.deduper.deduplicate_memories(
                [c for c, _ in scored_candidates], 
                self.storage.get_stored_memories(limit=1000)  # Get recent memories for dedup
            )
            
            # Combine all decisions
            all_decisions = initial_decisions + dedup_decisions
            
            # Step 5: Process decisions and store/buffer memories
            stored_count = 0
            buffered_count = 0
            rejected_count = 0
            
            for i, (candidate, score) in enumerate(scored_candidates):
                decision = all_decisions[i] if i < len(all_decisions) else initial_decisions[i]
                
                if decision.action == "keep":
                    # Store the memory
                    try:
                        memory_id = self.storage.store_memory(
                            candidate, decision, candidate.content
                        )
                        stored_count += 1
                        logger.info(f"Stored memory: {memory_id}")
                    except Exception as e:
                        logger.error(f"Failed to store memory: {e}")
                        # Fall back to buffering
                        decision.action = "buffer"
                        decision.reason = f"Storage failed, buffering instead: {e}"
                
                if decision.action == "buffer":
                    # Buffer for admin review
                    try:
                        logger.info(f"Buffering memory: {candidate.content[:50]}...")
                        buffer_id = self.storage.buffer_memory(
                            candidate, decision.reason, score
                        )
                        buffered_count += 1
                        logger.info(f"Successfully buffered memory: {buffer_id}")
                    except Exception as e:
                        logger.error(f"Failed to buffer memory: {e}")
                        rejected_count += 1
                
                elif decision.action == "reject":
                    rejected_count += 1
                    logger.info(f"Rejected memory: {candidate.content[:50]}...")
                
                elif decision.action == "merge":
                    # Memory was merged, count as processed
                    logger.info(f"Merged memory: {candidate.content[:50]}...")
            
            # Create response
            response = ExtractionResponse(
                candidates=[c for c, _ in scored_candidates],
                decisions=all_decisions,
                stored_count=stored_count,
                buffered_count=buffered_count,
                rejected_count=rejected_count
            )
            
            logger.info(f"Pipeline completed: {stored_count} stored, {buffered_count} buffered, {rejected_count} rejected")
            return response
            
        except Exception as e:
            logger.error(f"Error in extract_and_store pipeline: {e}")
            raise
    
    def get_memories(self, limit: int = 100, offset: int = 0) -> List[StoredMemory]:
        """Retrieve stored memories"""
        try:
            return self.storage.get_stored_memories(limit=limit, offset=offset)
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []
    
    def get_buffered_memories(self, limit: int = 100, offset: int = 0) -> List[BufferedMemory]:
        """Retrieve buffered memories for admin review"""
        try:
            return self.storage.get_buffered_memories(limit=limit, offset=offset)
        except Exception as e:
            logger.error(f"Failed to retrieve buffered memories: {e}")
            return []
    
    def approve_buffered_memory(self, memory_id: str, admin_notes: str = None) -> bool:
        """Approve a buffered memory"""
        try:
            return self.storage.approve_buffered_memory(memory_id, admin_notes)
        except Exception as e:
            logger.error(f"Failed to approve buffered memory: {e}")
            return False
    
    def reject_buffered_memory(self, memory_id: str, admin_notes: str = None) -> bool:
        """Reject a buffered memory"""
        try:
            return self.storage.reject_buffered_memory(memory_id, admin_notes)
        except Exception as e:
            logger.error(f"Failed to reject buffered memory: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            db_health = self.storage.health_check()
            
            return {
                "service": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "database": {
                    "status": db_health.get("database", "unknown"),
                    "collections": db_health.get("collections", {})
                }
            }
        except Exception as e:
            return {
                "service": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "database": {
                    "status": "error",
                    "collections": {}
                },
                "error": str(e)
            }
    
    def close(self):
        """Cleanup resources"""
        try:
            self.storage.close()
            logger.info("Decider service closed")
        except Exception as e:
            logger.error(f"Error closing service: {e}")







