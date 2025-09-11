import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Tuple, Dict, Set
from models import CandidateMemory, MemoryDecision, StoredMemory
from config import Config
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class MemoryDeduper:
    """Deduplicates memories using embedding cosine similarity"""
    
    def __init__(self):
        self.similarity_threshold = Config.SIMILARITY_THRESHOLD
        
    def deduplicate_memories(
        self, 
        candidates: List[CandidateMemory], 
        stored_memories: List[StoredMemory]
    ) -> Tuple[List[MemoryDecision], List[CandidateMemory]]:
        """Deduplicate candidates against stored memories and other candidates"""
        
        # First, deduplicate against stored memories
        decisions, remaining_candidates = self._deduplicate_against_stored(
            candidates, stored_memories
        )
        
        # Then, deduplicate remaining candidates against each other
        if len(remaining_candidates) > 1:
            decisions.extend(self._deduplicate_candidates(remaining_candidates))
        
        return decisions, remaining_candidates
    
    def _deduplicate_against_stored(
        self, 
        candidates: List[CandidateMemory], 
        stored_memories: List[StoredMemory]
    ) -> Tuple[List[MemoryDecision], List[CandidateMemory]]:
        """Deduplicate candidates against already stored memories"""
        decisions = []
        remaining_candidates = []
        
        for candidate in candidates:
            best_match = None
            best_similarity = 0.0
            
            for stored in stored_memories:
                if stored.embedding is None:
                    continue
                    
                # For now, use simple text similarity (could be enhanced with embeddings)
                similarity = self._calculate_text_similarity(
                    candidate.content, stored.final_content
                )
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = stored
            
            if best_similarity >= self.similarity_threshold:
                # Merge with existing memory
                decision = MemoryDecision(
                    action="merge",
                    reason=f"Similarity {best_similarity:.3f} with stored memory '{best_match.final_content[:50]}...'",
                    merged_with=best_match.id
                )
                decisions.append(decision)
                logger.info(f"Merging candidate with stored memory (similarity: {best_similarity:.3f})")
            else:
                remaining_candidates.append(candidate)
        
        return decisions, remaining_candidates
    
    def _deduplicate_candidates(self, candidates: List[CandidateMemory]) -> List[MemoryDecision]:
        """Deduplicate candidates against each other"""
        decisions = []
        processed = set()
        
        for i, candidate1 in enumerate(candidates):
            if i in processed:
                continue
                
            for j, candidate2 in enumerate(candidates[i+1:], i+1):
                if j in processed:
                    continue
                    
                similarity = self._calculate_text_similarity(
                    candidate1.content, candidate2.content
                )
                
                if similarity >= self.similarity_threshold:
                    # Keep the higher-scoring candidate
                    if candidate1.salience_score >= candidate2.salience_score:
                        keep_candidate = candidate1
                        merge_candidate = candidate2
                        keep_idx, merge_idx = i, j
                    else:
                        keep_candidate = candidate2
                        merge_candidate = candidate1
                        keep_idx, merge_idx = j, i
                    
                    decision = MemoryDecision(
                        action="merge",
                        reason=f"Similarity {similarity:.3f} with candidate '{merge_candidate.content[:50]}...'",
                        merged_with=keep_candidate.id
                    )
                    decisions.append(decision)
                    
                    processed.add(merge_idx)
                    logger.info(f"Merging candidate {merge_idx} into candidate {keep_idx} (similarity: {similarity:.3f})")
        
        return decisions
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using simple word overlap (placeholder for embeddings)"""
        # This is a simplified similarity measure
        # In production, you'd use proper embeddings from OpenAI or similar
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    








