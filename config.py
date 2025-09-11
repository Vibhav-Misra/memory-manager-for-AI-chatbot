import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration management for Decider service"""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # MongoDB Configuration
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/edy_decider")
    MONGODB_DB = os.getenv("MONGODB_DB", "edy_decider")
    
    # Scoring Configuration
    SCORING_WEIGHTS = {
        "relevance": float(os.getenv("RELEVANCE_WEIGHT", "0.4")),
        "specificity": float(os.getenv("SPECIFICITY_WEIGHT", "0.3")),
        "confidence": float(os.getenv("CONFIDENCE_WEIGHT", "0.3"))
    }
    
    THRESHOLDS = {
        "preference": float(os.getenv("PREFERENCE_THRESHOLD", "0.5")),
        "goal": float(os.getenv("GOAL_THRESHOLD", "0.6")),
        "commitment": float(os.getenv("COMMITMENT_THRESHOLD", "0.7")),
        "skill": float(os.getenv("SKILL_THRESHOLD", "0.6")),
        "feedback": float(os.getenv("FEEDBACK_THRESHOLD", "0.5"))
    }
    
    # Service Configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Deduplication Configuration
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
    BUFFER_THRESHOLD = float(os.getenv("BUFFER_THRESHOLD", "0.5"))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        if not cls.OPENAI_API_KEY.startswith("sk-"):
            raise ValueError("OPENAI_API_KEY appears to be invalid (should start with 'sk-')")
        return True
    
    @classmethod
    def get_mongodb_connection_string(cls) -> str:
        """Get MongoDB connection string with validation"""
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI is required")
        return cls.MONGODB_URI


