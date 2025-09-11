#!/usr/bin/env python3
"""
Memory Extractor Module
Extracts candidate memories from conversation turns using NLP and pattern matching
"""

import re
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
from models import ConversationTurn, CandidateMemory, MemoryType

logger = logging.getLogger(__name__)

class MemoryExtractor:
    """Extracts candidate memories from conversation turns"""
    
    def __init__(self):
        # Pattern-based extraction rules
        self.patterns = {
            MemoryType.PREFERENCE: [
                r'\b(?:I|I\'m|I am)\s+(?:prefer|like|enjoy|love|hate|dislike)\s+(?:to\s+)?(.+?)(?:\.|!|\?|$)',
                r'\b(?:I|I\'m|I am)\s+(?:not\s+)?(?:a\s+)?(?:fan\s+of|fond\s+of)\s+(.+?)(?:\.|!|\?|$)',
                r'\b(?:I|I\'m|I am)\s+(?:would\s+)?(?:rather|prefer)\s+(?:to\s+)?(.+?)(?:\.|!|\?|$)',
            ],
            MemoryType.GOAL: [
                r'\b(?:I|I\'m|I am)\s+(?:want|wish|hope|plan|aim|intend)\s+(?:to\s+)?(.+?)(?:\.|!|\?|$)',
                r'\b(?:My|The)\s+(?:goal|objective|target|aim|plan)\s+(?:is|was)\s+(?:to\s+)?(.+?)(?:\.|!|\?|$)',
                r'\b(?:I|I\'m|I am)\s+(?:working\s+)?(?:towards|on)\s+(.+?)(?:\.|!|\?|$)',
            ],
            MemoryType.COMMITMENT: [
                r'\b(?:I|I\'m|I am)\s+(?:will|shall|promise|commit|guarantee)\s+(?:to\s+)?(.+?)(?:\.|!|\?|$)',
                r'\b(?:I|I\'m|I am)\s+(?:going\s+to|gonna)\s+(.+?)(?:\.|!|\?|$)',
                r'\b(?:I|I\'m|I am)\s+(?:dedicated|committed)\s+(?:to\s+)?(.+?)(?:\.|!|\?|$)',
            ],
            MemoryType.SKILL: [
                r'\b(?:I|I\'m|I am)\s+(?:know|can|able\s+to|experienced\s+with|familiar\s+with)\s+(.+?)(?:\.|!|\?|$)',
                r'\b(?:I|I\'m|I am)\s+(?:good|great|excellent|skilled|proficient)\s+(?:at|with|in)\s+(.+?)(?:\.|!|\?|$)',
                r'\b(?:I|I\'m|I am)\s+(?:learning|studying|practicing)\s+(.+?)(?:\.|!|\?|$)',
            ],
            MemoryType.FEEDBACK: [
                r'\b(?:I|I\'m|I am)\s+(?:think|feel|believe|find|consider)\s+(?:that\s+)?(.+?)(?:\.|!|\?|$)',
                r'\b(?:This|That|It)\s+(?:is|was|feels|seems)\s+(.+?)(?:\.|!|\?|$)',
                r'\b(?:I|I\'m|I am)\s+(?:satisfied|happy|unhappy|disappointed|pleased)\s+(?:with|about)\s+(.+?)(?:\.|!|\?|$)',
            ]
        }
        
        # Confidence scoring weights
        self.confidence_weights = {
            'pattern_match': 0.6,
            'sentence_structure': 0.2,
            'context_relevance': 0.2
        }
        
        logger.info("MemoryExtractor initialized with pattern-based extraction rules")
    
    def extract_memories(self, turns: List[ConversationTurn]) -> List[CandidateMemory]:
        """Extract candidate memories from conversation turns"""
        candidates = []
        
        for turn in turns:
            if turn.speaker.lower() == "user":  # Only extract from user statements
                turn_candidates = self._extract_from_turn(turn)
                candidates.extend(turn_candidates)
        
        logger.info(f"Extracted {len(candidates)} candidate memories from {len(turns)} turns")
        return candidates
    
    def _extract_from_turn(self, turn: ConversationTurn) -> List[CandidateMemory]:
        """Extract memories from a single conversation turn"""
        candidates = []
        text = turn.text.strip()
        
        # Skip very short or non-informative turns
        if len(text) < 10 or text.lower() in ['yes', 'no', 'ok', 'okay', 'thanks', 'thank you']:
            return candidates
        
        # Check each memory type pattern
        for memory_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    content = match.group(1).strip()
                    
                    # Skip if content is too short or generic
                    if len(content) < 5 or content.lower() in ['it', 'this', 'that', 'something', 'things']:
                        continue
                    
                    # Calculate confidence score
                    confidence = self._calculate_confidence(text, content, memory_type, pattern)
                    
                    # Calculate relevance score
                    relevance = self._calculate_relevance(content, memory_type)
                    
                    # Calculate specificity score
                    specificity = self._calculate_specificity(content)
                    
                    # Calculate overall salience score
                    salience_score = (confidence * 0.4 + relevance * 0.4 + specificity * 0.2)
                    
                    # Create candidate memory
                    candidate = CandidateMemory(
                        memory_type=memory_type,
                        content=content,
                        confidence=confidence,
                        relevance=relevance,
                        specificity=specificity,
                        salience_score=salience_score,
                        source_turn=turn,
                        extraction_evidence=f"Pattern match: {pattern}",
                        created_at=datetime.now(timezone.utc)
                    )
                    
                    candidates.append(candidate)
        
        return candidates
    
    def _calculate_confidence(self, text: str, content: str, memory_type: MemoryType, pattern: str) -> float:
        """Calculate confidence score for extracted memory"""
        confidence = 0.0
        
        # Pattern match quality
        if re.search(pattern, text, re.IGNORECASE):
            confidence += 0.6
        
        # Sentence structure quality
        if text.endswith('.') or text.endswith('!') or text.endswith('?'):
            confidence += 0.2
        
        # Content quality
        if len(content) > 10 and not content.startswith(('the', 'a', 'an', 'and', 'or', 'but')):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _calculate_relevance(self, content: str, memory_type: MemoryType) -> float:
        """Calculate relevance score for memory content"""
        relevance = 0.5  # Base relevance
        
        # Boost relevance for specific, actionable content
        if any(word in content.lower() for word in ['learn', 'study', 'work', 'practice', 'improve', 'develop']):
            relevance += 0.3
        
        # Boost for personal statements
        if content.lower().startswith(('i ', 'my ', 'me ')):
            relevance += 0.2
        
        return min(relevance, 1.0)
    
    def _calculate_specificity(self, content: str) -> float:
        """Calculate specificity score for memory content"""
        specificity = 0.5  # Base specificity
        
        # Boost for specific details
        if any(word in content.lower() for word in ['python', 'machine learning', 'data science', '2 hours', 'every evening']):
            specificity += 0.3
        
        # Boost for measurable commitments
        if re.search(r'\d+', content):
            specificity += 0.2
        
        return min(specificity, 1.0)


