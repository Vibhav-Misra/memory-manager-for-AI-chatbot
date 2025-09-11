from typing import List, Tuple
from models import CandidateMemory, MemoryType, MemoryDecision
from config import Config
import logging

logger = logging.getLogger(__name__)

class MemoryScorer:
    """Scores candidate memories using linear blend and type-specific thresholds"""
    
    def __init__(self):
        self.weights = Config.SCORING_WEIGHTS
        self.thresholds = Config.THRESHOLDS
        self.buffer_threshold = Config.BUFFER_THRESHOLD
    
    def score_memories(self, candidates: List[CandidateMemory]) -> List[Tuple[CandidateMemory, float]]:
        """Score all candidate memories"""
        scored = []
        for candidate in candidates:
            score = self._calculate_salience_score(candidate)
            candidate.salience_score = score
            scored.append((candidate, score))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    
    def _calculate_salience_score(self, candidate: CandidateMemory) -> float:
        """Calculate salience score using linear blend of factors"""
        score = (
            self.weights["relevance"] * candidate.relevance +
            self.weights["specificity"] * candidate.specificity +
            self.weights["confidence"] * candidate.confidence
        )
        return round(score, 3)
    
    def make_decisions(self, scored_candidates: List[Tuple[CandidateMemory, float]]) -> List[MemoryDecision]:
        """Make decisions about each candidate based on scores and thresholds"""
        decisions = []
        
        for candidate, score in scored_candidates:
            decision = self._evaluate_candidate(candidate, score)
            decisions.append(decision)
            
            logger.info(f"Memory '{candidate.content[:50]}...' scored {score:.3f}, decision: {decision.action}")
        
        return decisions
    
    def _evaluate_candidate(self, candidate: CandidateMemory, score: float) -> MemoryDecision:
        """Evaluate a single candidate and make a decision"""
        memory_type = candidate.memory_type.value
        threshold = self.thresholds.get(memory_type, 0.7)
        
        if score >= threshold:
            return MemoryDecision(
                action="keep",
                reason=f"Score {score:.3f} meets {memory_type} threshold {threshold}"
            )
        elif score >= self.buffer_threshold:
            return MemoryDecision(
                action="buffer",
                reason=f"Score {score:.3f} below {memory_type} threshold {threshold} but above buffer threshold {self.buffer_threshold}"
            )
        else:
            return MemoryDecision(
                action="reject",
                reason=f"Score {score:.3f} below buffer threshold {self.buffer_threshold}"
            )
    
    def get_statistics(self, decisions: List[MemoryDecision]) -> dict:
        """Get statistics about the decisions made"""
        stats = {
            "total": len(decisions),
            "kept": len([d for d in decisions if d.action == "keep"]),
            "buffered": len([d for d in decisions if d.action == "buffer"]),
            "rejected": len([d for d in decisions if d.action == "reject"]),
            "merged": len([d for d in decisions if d.action == "merge"])
        }
        return stats










