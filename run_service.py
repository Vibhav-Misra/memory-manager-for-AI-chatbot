#!/usr/bin/env python3
"""
Unified startup script for Decider Service
Handles environment setup, dependency checks, and service startup
"""

import os
import sys
import logging
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def setup_environment():
    """Setup environment variables and configuration"""
    print("🔧 Setting up Decider v1 environment...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  No .env file found. Creating from template...")
        
        # Create .env file with default values
        env_content = """# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/edy_decider
MONGODB_DB=edy_decider

# Scoring Configuration
RELEVANCE_WEIGHT=0.4
SPECIFICITY_WEIGHT=0.3
CONFIDENCE_WEIGHT=0.3

# Thresholds
PREFERENCE_THRESHOLD=0.5
GOAL_THRESHOLD=0.6
COMMITMENT_THRESHOLD=0.7
SKILL_THRESHOLD=0.6
FEEDBACK_THRESHOLD=0.5

# Service Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Deduplication Configuration
SIMILARITY_THRESHOLD=0.85
BUFFER_THRESHOLD=0.6
"""
        
        with open(env_file, "w") as f:
            f.write(env_content)
        
        print("✅ Created .env file. Please update with your actual values:")
        print("   - Set your OpenAI API key")
        print("   - Configure MongoDB connection if different from default")
        print("   - Adjust scoring weights and thresholds as needed")
        print()
        print("⚠️  IMPORTANT: Update OPENAI_API_KEY before starting the service!")
        return False
    
    # Load environment variables
    load_dotenv()
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here":
        print("❌ OPENAI_API_KEY not set or still has default value!")
        print("Please update your .env file with a valid OpenAI API key.")
        return False
    
    print("✅ Environment configuration looks good!")
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    print("Checking dependencies...")

    # pip/dist name -> importable module name
    required = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pymongo": "pymongo",
        "streamlit": "streamlit",
        "openai": "openai",
        "numpy": "numpy",
        "scikit-learn": "sklearn",   # <-- important
        "python-dotenv": "dotenv",   # <-- important
        "pydantic": "pydantic",
    }

    missing = []
    for dist_name, import_name in required.items():
        try:
            __import__(import_name)
            print(f"   ✅ {dist_name}")
        except ImportError:
            print(f"   ❌ {dist_name}")
            missing.append(dist_name)

    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("Please install them with: python -m pip install -r requirements.txt")
        return False

    print("✅ All dependencies are available!")
    return True

def check_mongodb():
    """Check MongoDB connection"""
    print("Checking MongoDB connection...")
    
    try:
        from pymongo import MongoClient
        from config import Config
        
        client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        client.close()
        
        print("✅ MongoDB connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("Please ensure MongoDB is running and accessible.")
        print("You can start MongoDB with: mongod")
        return False

def start_service():
    """Start the Decider service"""
    print("Starting Decider v1 service...")
    
    try:
        from config import Config
        
        print(f"Service will be available at: http://{Config.HOST}:{Config.PORT}")
        print(f"API documentation: http://{Config.HOST}:{Config.PORT}/docs")
        print(f"Admin UI: streamlit run admin_ui.py")
        print()
        print("Press Ctrl+C to stop the service")
        print("-" * 50)
        
        uvicorn.run(
            "main:app",
            host=Config.HOST,
            port=Config.PORT,
            reload=False,
            log_level=Config.LOG_LEVEL.lower()
        )
        
    except Exception as e:
        print(f"❌ Failed to start service: {e}")
        return False

def main():
    """Main startup function"""
    print("Decider v1 - Memory Management Service")
    print("=" * 50)
    
    # Setup checks
    if not setup_environment():
        print("\n❌ Environment setup failed. Please fix the issues above.")
        return 1
    
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install missing packages.")
        return 1
    
    if not check_mongodb():
        print("\n❌ MongoDB check failed. Please ensure MongoDB is running.")
        return 1
    
    print("\n✅ All checks passed! Starting service...")
    print()
    
    # Start the service
    try:
        start_service()
    except KeyboardInterrupt:
        print("\n\nService stopped by user")
    except Exception as e:
        print(f"\n❌ Service failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())






